"""Focused test suite for Phase 3 RAG Pipeline matching TEST_PLAN.md §4 (RAG-001 through RAG-009)."""

import os
from pathlib import Path
import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings
from app.graph.builder import build_graph
from app.llm.gateway import FakeLLMGateway
from app.llm.schemas import GroundedAnswer
from app.rag.chunking import chunk_pages, extract_pages_from_pdf
from app.rag.grounding import UNANSWERABLE_HANDBOOK_REPLY, validate_and_build_grounded_response
from app.rag.ingest import compute_file_sha256, ingest_handbook
from app.rag.retriever import HandbookRetriever, RetrievedChunk, get_retriever


@pytest.fixture
def pdf_path() -> Path:
    """Path to the official employee handbook PDF."""
    path = Path(settings.DATA_DIR) / "raw" / settings.HANDBOOK_FILENAME
    assert path.exists(), f"Employee handbook PDF missing at {path}"
    return path


def test_rag_001_pdf_extraction_and_chunking_metadata(pdf_path):
    """RAG-001: 10 pages parsed with text (page 1 skipped as <30 chars), exactly 26 chunks created,

    every chunk has source, page in 2..11, and chunk_index.
    """
    pages = extract_pages_from_pdf(pdf_path, min_chars_per_page=30)

    # Page 1 (title page with 22 chars) is skipped; remaining pages are 2 to 11
    assert len(pages) == 10
    extracted_page_nums = [p["page"] for p in pages]
    assert extracted_page_nums == list(range(2, 12))

    # Page-bounded chunking
    chunks = chunk_pages(
        pages,
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        source_filename="employee_handbook.pdf",
    )

    assert len(chunks) == 26

    # Verify chunk structure and metadata invariants
    for chunk in chunks:
        assert chunk["source"] == "employee_handbook.pdf"
        assert chunk["title"] == "Zava Employee Handbook"
        assert 2 <= chunk["page"] <= 11
        assert isinstance(chunk["chunk_index"], int)
        assert chunk["chunk_index"] >= 0
        expected_id = f"employee_handbook.pdf-p{chunk['page']}-c{chunk['chunk_index']}"
        assert chunk["chunk_id"] == expected_id
        assert len(chunk["text"]) > 0

    # Page 4 contains performance review text
    p4_chunks = [c for c in chunks if c["page"] == 4]
    assert len(p4_chunks) >= 1
    assert any("conducted annually" in c["text"].lower() for c in p4_chunks)


def test_rag_002_ingestion_repeatability_and_idempotency(tmp_path, pdf_path):
    """RAG-002: Ingestion is repeatable and strictly idempotent without duplicating indexed chunks."""
    temp_chroma_dir = tmp_path / "chroma_test"

    # First ingestion run
    res1 = ingest_handbook(pdf_path=pdf_path, chroma_dir=temp_chroma_dir)
    assert res1["status"] == "indexed"
    assert res1["chunks_indexed"] == 26
    assert res1["collection_count"] == 26
    expected_hash = compute_file_sha256(pdf_path)
    assert res1["file_sha256"] == expected_hash

    # Second ingestion run with same parameters -> must be a no-op
    res2 = ingest_handbook(pdf_path=pdf_path, chroma_dir=temp_chroma_dir)
    assert res2["status"] == "skipped"
    assert res2["reason"] == "already_indexed"
    assert res2["collection_count"] == 26
    assert res2["file_sha256"] == expected_hash

    # Force re-ingestion rebuilds the collection cleanly
    res3 = ingest_handbook(pdf_path=pdf_path, chroma_dir=temp_chroma_dir, force=True)
    assert res3["status"] == "indexed"
    assert res3["collection_count"] == 26


def test_rag_003_performance_review_retrieval():
    """RAG-003: Retrieve 'How often are performance reviews conducted?' -> top-k includes page 4 chunk with 'conducted annually'."""
    retriever = get_retriever()
    passages = retriever.retrieve_sync("How often are performance reviews conducted?", top_k=4)

    assert len(passages) > 0
    top_passage = passages[0]
    assert top_passage.page == 4
    assert top_passage.document == "employee_handbook.pdf"
    assert any("conducted annually" in p.text.lower() for p in passages)


def test_rag_004_answerable_question_set_hit_rate():
    """RAG-004: All 12 labelled answerable questions in TEST_PLAN §10.1 achieve >= 90% top-k expected page hit rate."""
    retriever = get_retriever()
    test_cases = [
        ("How often are performance reviews conducted?", [4], "conducted annually"),
        ("Will I get a written summary of my performance review?", [4], "written summary"),
        ("What should I do if I witness workplace violence?", [6], "supervisor"),
        ("What is the Compliance Hotline number?", [8, 9], "hotline"),
        ("Can I report a concern anonymously?", [9], "anonymously"),
        ("Who do I contact about my personal information?", [7, 8], "Privacy Officer"),
        ("Does Zava sell personal information?", [7], "will not sell"),
        ("How often must employees complete data security training?", [10], "annually thereafter"),
        ("What are the company values?", [3, 4], "Integrity"),
        ("What industry is Zava in?", [3], "aerospace"),
        ("Is retaliation against whistleblowers allowed?", [9], "Retaliation"),
        ("Which job roles exist at Zava, e.g. a Chief Technology Officer?", [10], "Chief Technology Officer"),
    ]

    hits = 0
    for q, exp_pages, key in test_cases:
        passages = retriever.retrieve_sync(q, top_k=4)
        retrieved_pages = [p.page for p in passages]
        has_page = any(p in exp_pages for p in retrieved_pages)
        if has_page:
            hits += 1

    hit_rate = hits / len(test_cases)
    assert hit_rate >= 0.90, f"Expected hit rate >= 0.90, got {hit_rate:.2f}"


def test_rag_005_unanswerable_pto_and_benefits_questions():
    """RAG-005: Unanswerable topics (PTO, vacation, health insurance) exceed calibrated distance gate."""
    retriever = get_retriever()
    unanswerable = [
        "What is the PTO policy?",
        "How many vacation days do I get?",
        "What health insurance plans are offered?",
        "What is the dress code?",
        "What is the remote-work policy?",
    ]

    for q in unanswerable:
        # With threshold gating at 0.55, unanswerable queries return no passages
        passages = retriever.retrieve_sync(q, top_k=4, max_distance=settings.RETRIEVAL_MAX_DISTANCE)
        assert len(passages) == 0, f"Expected 0 passages for unanswerable question '{q}', got {len(passages)}"


def test_rag_006_out_of_domain_capital_of_france():
    """RAG-006: Out-of-domain query 'What is the capital of France?' returns no passages under threshold."""
    retriever = get_retriever()
    passages = retriever.retrieve_sync("What is the capital of France?", top_k=4, max_distance=settings.RETRIEVAL_MAX_DISTANCE)
    assert len(passages) == 0


@pytest.mark.asyncio
async def test_rag_007_grounded_answer_and_citations():
    """RAG-007: FAQ answering produces factual answer with valid source citation mentioning annual review."""
    retriever = get_retriever()
    passages = await retriever.retrieve("How often are performance reviews conducted?")
    assert len(passages) > 0

    from app.llm.gateway import OfflineLLMGateway
    gateway = OfflineLLMGateway()
    grounded_ans = await gateway.answer_from_passages("How often are performance reviews conducted?", passages)

    assert grounded_ans.answerable is True
    assert "annual" in grounded_ans.answer.lower()
    assert "twice a year" not in grounded_ans.answer.lower()

    content, citations = validate_and_build_grounded_response(grounded_ans, passages)
    assert len(citations) >= 1
    assert citations[0]["document"] == "employee_handbook.pdf"
    assert citations[0]["page"] == 4
    assert "Source: employee_handbook.pdf, p. 4" in content


def test_rag_008_citation_metadata_schema_correctness():
    """RAG-008: Validates citation schema contains required fields and no invented page numbers."""
    dummy_passage = RetrievedChunk(
        chunk_id="employee_handbook.pdf-p4-c0",
        document="employee_handbook.pdf",
        title="Zava Employee Handbook",
        page=4,
        chunk_index=0,
        text="Performance reviews are conducted annually.",
        distance=0.42,
    )
    answer = GroundedAnswer(
        answerable=True,
        answer="Reviews are annual.",
        used_chunk_ids=["employee_handbook.pdf-p4-c0"],
    )

    content, citations = validate_and_build_grounded_response(answer, [dummy_passage])
    assert len(citations) == 1
    c = citations[0]
    assert c["document"] == "employee_handbook.pdf"
    assert c["title"] == "Zava Employee Handbook"
    assert c["page"] == 4
    assert c["chunk_id"] == "employee_handbook.pdf-p4-c0"
    assert "Performance reviews are conducted annually." in c["snippet"]


def test_rag_009_fabricated_chunk_id_rejection():
    """RAG-009: Hallucinated or non-retrieved chunk IDs are dropped; if none remain, unanswerable reply is returned."""
    real_passage = RetrievedChunk(
        chunk_id="employee_handbook.pdf-p4-c0",
        document="employee_handbook.pdf",
        title="Zava Employee Handbook",
        page=4,
        chunk_index=0,
        text="Real handbook text.",
        distance=0.35,
    )

    # Hallucinated chunk ID not present in retrieved passages
    fabricated_answer = GroundedAnswer(
        answerable=True,
        answer="This answer relies on a hallucinated chunk.",
        used_chunk_ids=["employee_handbook.pdf-p99-c99"],
    )

    content, citations = validate_and_build_grounded_response(fabricated_answer, [real_passage])
    # Must reject fabricated ID and fall back to unanswerable notice
    assert citations == []
    assert content == UNANSWERABLE_HANDBOOK_REPLY


@pytest.mark.asyncio
async def test_faq_integration_preserves_booking_state():
    """FAQ turn never mutates or clobbers active structured booking state (GR-006, SC-03)."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-booking-preservation"}}

    # Turn 1: User starts booking
    await graph.ainvoke(
        {"messages": [HumanMessage(content="Hi, I need to book a 1-on-1 Performance Review session.")]},
        config=config,
    )
    s1 = await graph.aget_state(config)
    assert s1.values["booking"]["status"] == "collecting"

    # Turn 2: User provides name and email -> transitions to awaiting_slot
    await graph.ainvoke(
        {"messages": [HumanMessage(content="Alex Chen (alex.chen@example.com)")]},
        config=config,
    )
    state_before = await graph.aget_state(config)
    booking_before = dict(state_before.values["booking"])
    assert booking_before["status"] == "awaiting_slot"
    assert booking_before["full_name"] == "Alex Chen"
    assert booking_before["email"] == "alex.chen@example.com"
    assert len(booking_before["offered_slots"]) > 0

    # Turn 3: User asks an FAQ question in the middle of active booking
    await graph.ainvoke(
        {"messages": [HumanMessage(content="How often are performance reviews conducted according to the handbook?")]},
        config=config,
    )

    state_after = await graph.aget_state(config)
    booking_after = dict(state_after.values["booking"])

    # Invariant: Structured booking state is 100% preserved and never overwritten
    assert booking_after["status"] == "awaiting_slot"
    assert booking_after["full_name"] == "Alex Chen"
    assert booking_after["email"] == "alex.chen@example.com"
    assert booking_after["offered_slots"] == booking_before["offered_slots"]

    # Verify FAQ citations were generated on Turn 3
    assert len(state_after.values.get("citations", [])) >= 1
    assert state_after.values["citations"][0]["page"] == 4
