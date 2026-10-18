"""Grounding context formatting and citation validation matching TECHNICAL_DESIGN.md §11.4."""

from typing import Any, Dict, List, Set, Tuple
from app.llm.schemas import GroundedAnswer
from app.rag.retriever import RetrievedChunk

UNANSWERABLE_HANDBOOK_REPLY = (
    "I couldn't find that in the Employee Handbook. I can help with topics it covers — "
    "such as performance reviews, workplace safety, privacy, whistleblower policy, data "
    "security and job roles — or book a performance review session."
)


def format_context_block(passages: List[RetrievedChunk]) -> str:
    """Format retrieved passages into a clearly delimited context block."""
    if not passages:
        return "No relevant handbook passages found."

    blocks = []
    for idx, passage in enumerate(passages, start=1):
        header = f"[C{idx}] (Document: {passage.document}, Page {passage.page}, ID: {passage.chunk_id})"
        blocks.append(f"{header}\n{passage.text}")

    return "\n\n---\n\n".join(blocks)


def validate_and_build_grounded_response(
    grounded_answer: GroundedAnswer,
    retrieved_passages: List[RetrievedChunk],
) -> Tuple[str, List[Dict[str, Any]]]:
    """Validate model output against retrieved passages and build authoritative citations.
    
    Security and validation rules (TECHNICAL_DESIGN §11.4):
    1. Filter used_chunk_ids: only IDs actually retrieved are allowed; fabricated IDs are discarded.
    2. If answerable is False OR no valid chunk IDs remain, return grounded 'not found' text with empty citations.
    3. Citations are built solely from chunk metadata, never from LLM hallucinations.
    4. Append deterministic source footer to answer text: 'Source: employee_handbook.pdf, p. 4'.
    """
    if not grounded_answer.answerable or not grounded_answer.answer.strip():
        return UNANSWERABLE_HANDBOOK_REPLY, []

    retrieved_by_id: Dict[str, RetrievedChunk] = {p.chunk_id: p for p in retrieved_passages}

    # 1. Enforce used_chunk_ids ⊆ retrieved_passages
    valid_chunk_ids = [cid for cid in grounded_answer.used_chunk_ids if cid in retrieved_by_id]

    # If the model declared answerable=True but cited no valid retrieved chunks, reject
    if not valid_chunk_ids:
        # Fallback: if retrieved_passages has exactly 1 relevant passage and answer is grounded, or treat as unanswerable
        return UNANSWERABLE_HANDBOOK_REPLY, []

    # 2. Build citations from validated chunk metadata
    citations: List[Dict[str, Any]] = []
    seen_chunk_ids: Set[str] = set()
    cited_pages: Set[int] = set()
    doc_name = "employee_handbook.pdf"

    for cid in valid_chunk_ids:
        if cid in seen_chunk_ids:
            continue
        seen_chunk_ids.add(cid)
        passage = retrieved_by_id[cid]
        doc_name = passage.document
        cited_pages.add(passage.page)
        citations.append({
            "document": passage.document,
            "title": passage.title,
            "page": passage.page,
            "snippet": passage.text[:200] if len(passage.text) > 200 else passage.text,
            "chunk_id": passage.chunk_id,
        })

    # 3. Format deterministic source footer
    sorted_pages = sorted(cited_pages)
    if len(sorted_pages) == 1:
        page_str = f"p. {sorted_pages[0]}"
    else:
        page_str = f"pp. {', '.join(str(p) for p in sorted_pages)}"

    source_footer = f"Source: {doc_name}, {page_str}"
    cleaned_answer = grounded_answer.answer.strip()
    final_content = f"{cleaned_answer}\n\n{source_footer}"

    return final_content, citations
