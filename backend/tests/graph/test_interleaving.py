"""Tests for multi-turn context interleaving and resumption matching docs/TECHNICAL_DESIGN.md §7 & GR-006..010."""

import uuid
import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.booking.service import get_booking_service
from app.graph.builder import build_graph


@pytest.fixture(autouse=True)
def reset_service():
    """Reset deterministic booking inventory before each test."""
    svc = get_booking_service()
    svc.reset()
    yield
    svc.reset()


@pytest.mark.asyncio
async def test_interleaving_full_journey_faq_then_booking(tmp_path):
    """AR-014, AR-025, AR-041: Complete 9-step user journey with handbook FAQ interrupting pending booking."""
    db_file = str(tmp_path / "checkpoints.sqlite")
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async with AsyncSqliteSaver.from_conn_string(db_file) as cp:
        await cp.setup()
        graph = build_graph(checkpointer=cp)

        # ---------------------------------------------------------------------
        # Turn 1: User initiates booking without attendee details
        # ---------------------------------------------------------------------
        s1 = await graph.ainvoke(
            {"messages": [HumanMessage(content="I want to schedule a performance review.")]},
            config=config,
        )
        assert s1["booking"]["status"] == "collecting"
        assert s1["booking"]["full_name"] is None
        assert s1["booking"]["email"] is None
        assert "full name and email" in s1["reply_parts"][-1].lower()

        # ---------------------------------------------------------------------
        # Turn 2: User provides valid name and email
        # ---------------------------------------------------------------------
        s2 = await graph.ainvoke(
            {"messages": [HumanMessage(content="Jordan Lee, jordan.lee@example.com")]},
            config=config,
        )
        assert s2["booking"]["status"] == "awaiting_slot"
        assert s2["booking"]["full_name"] == "Jordan Lee"
        assert s2["booking"]["email"] == "jordan.lee@example.com"
        assert len(s2["booking"]["offered_slots"]) == 3
        offered_labels = [s["label"] for s in s2["booking"]["offered_slots"]]
        assert any("available slots" in p.lower() for p in s2["reply_parts"])

        # ---------------------------------------------------------------------
        # Turn 3: User interrupts with an FAQ question answered by handbook RAG
        # ---------------------------------------------------------------------
        s3 = await graph.ainvoke(
            {"messages": [HumanMessage(content="How often are performance reviews conducted according to the handbook?")]},
            config=config,
        )

        # Grounded answer assertion
        reply_text = "\n\n".join(s3["reply_parts"])
        assert "annually" in reply_text.lower()
        # Citations assertion
        assert len(s3["citations"]) >= 1
        assert s3["citations"][0]["page"] == 4
        assert s3["citations"][0]["document"] == "employee_handbook.pdf"

        # Resumption assertion: Booking state is strictly preserved
        assert s3["booking"]["status"] == "awaiting_slot"
        assert s3["booking"]["full_name"] == "Jordan Lee"
        assert s3["booking"]["email"] == "jordan.lee@example.com"
        assert len(s3["booking"]["offered_slots"]) == 3
        assert [s["label"] for s in s3["booking"]["offered_slots"]] == offered_labels

        # Resumption text re-presents slot choices
        assert "returning to your booking, jordan" in reply_text.lower()
        assert "which one works best" in reply_text.lower()

        # ---------------------------------------------------------------------
        # Turn 4: User selects a valid offered slot
        # ---------------------------------------------------------------------
        s4 = await graph.ainvoke(
            {"messages": [HumanMessage(content="Option 1")]},
            config=config,
        )

        # Booking confirmation assertions
        assert s4["booking"]["status"] == "confirmed"
        assert s4["booking"]["booking_reference"] is not None
        assert s4["booking"]["booking_reference"].startswith("#REV-")
        assert s4["booking"]["full_name"] == "Jordan Lee"
        assert s4["booking"]["email"] == "jordan.lee@example.com"
        assert s4["booking"]["confirmed_slot"]["slot_id"] == s2["booking"]["offered_slots"][0]["slot_id"]
        assert "confirmed" in s4["reply_parts"][-1].lower()


@pytest.mark.asyncio
async def test_interleaving_multiple_faqs_preserve_booking_state(tmp_path):
    """GR-008: Multiple consecutive FAQ turns do not corrupt accumulated booking state."""
    db_file = str(tmp_path / "checkpoints.sqlite")
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async with AsyncSqliteSaver.from_conn_string(db_file) as cp:
        await cp.setup()
        graph = build_graph(checkpointer=cp)

        # Turn 1: Start booking with details
        await graph.ainvoke(
            {"messages": [HumanMessage(content="Schedule review for Alex Rivera (alex.rivera@example.com)")]},
            config=config,
        )

        # Turn 2: FAQ 1
        t2 = await graph.ainvoke(
            {"messages": [HumanMessage(content="What should I do if I witness workplace violence?")]},
            config=config,
        )
        assert t2["booking"]["status"] == "awaiting_slot"
        assert t2["booking"]["full_name"] == "Alex Rivera"
        assert t2["citations"][0]["page"] == 6

        # Turn 3: FAQ 2
        t3 = await graph.ainvoke(
            {"messages": [HumanMessage(content="Does Zava sell personal information?")]},
            config=config,
        )
        assert t3["booking"]["status"] == "awaiting_slot"
        assert t3["booking"]["full_name"] == "Alex Rivera"
        assert t3["citations"][0]["page"] == 7

        # Turn 4: User selects slot after two interruptions
        t4 = await graph.ainvoke(
            {"messages": [HumanMessage(content="Option 2")]},
            config=config,
        )
        assert t4["booking"]["status"] == "confirmed"
        assert t4["booking"]["booking_reference"].startswith("#REV-")
        assert t4["booking"]["full_name"] == "Alex Rivera"


@pytest.mark.asyncio
async def test_interleaving_unrelated_question_does_not_confirm(tmp_path):
    """NEG-015: Out-of-domain query during awaiting_slot returns refusal and never confirms booking."""
    db_file = str(tmp_path / "checkpoints.sqlite")
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async with AsyncSqliteSaver.from_conn_string(db_file) as cp:
        await cp.setup()
        graph = build_graph(checkpointer=cp)

        await graph.ainvoke(
            {"messages": [HumanMessage(content="Book appointment for Taylor Swift (taylor@example.com)")]},
            config=config,
        )

        # Unrelated query
        resp = await graph.ainvoke(
            {"messages": [HumanMessage(content="What is the capital of France?")]},
            config=config,
        )

        assert resp["booking"]["status"] == "awaiting_slot"
        assert resp["booking"]["booking_reference"] is None
        assert len(resp["citations"]) == 0
        assert "couldn't find that in the employee handbook" in resp["reply_parts"][0].lower()
        # Still offered slots to resume
        assert "returning to your booking" in resp["reply_parts"][-1].lower()


@pytest.mark.asyncio
async def test_interleaving_invalid_slot_selection_preserves_state(tmp_path):
    """GR-010: Out-of-range slot input during interleaved flow retains details and guides user."""
    db_file = str(tmp_path / "checkpoints.sqlite")
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async with AsyncSqliteSaver.from_conn_string(db_file) as cp:
        await cp.setup()
        graph = build_graph(checkpointer=cp)

        await graph.ainvoke(
            {"messages": [HumanMessage(content="Book appointment for Chris Pratt (chris@example.com)")]},
            config=config,
        )

        # Invalid slot option
        s_inv = await graph.ainvoke(
            {"messages": [HumanMessage(content="Option 99")]},
            config=config,
        )
        assert s_inv["booking"]["status"] == "awaiting_slot"
        assert s_inv["booking"]["selected_slot_id"] is None
        assert "outside the offered options" in s_inv["reply_parts"][0].lower()

        # Valid recovery
        s_ok = await graph.ainvoke(
            {"messages": [HumanMessage(content="Option 1")]},
            config=config,
        )
        assert s_ok["booking"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_interleaving_mid_collecting_faq(tmp_path):
    """GR-009: FAQ asked while collecting name/email answers FAQ and resumes missing-info prompt."""
    db_file = str(tmp_path / "checkpoints.sqlite")
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async with AsyncSqliteSaver.from_conn_string(db_file) as cp:
        await cp.setup()
        graph = build_graph(checkpointer=cp)

        # Turn 1: Name only provided
        await graph.ainvoke(
            {"messages": [HumanMessage(content="Book review for Morgan Freeman")]},
            config=config,
        )

        # Turn 2: FAQ mid-collecting
        s2 = await graph.ainvoke(
            {"messages": [HumanMessage(content="How often are performance reviews conducted according to the handbook?")]},
            config=config,
        )
        assert s2["booking"]["status"] == "collecting"
        assert s2["booking"]["full_name"] == "Morgan Freeman"
        assert s2["booking"]["email"] is None
        assert "annually" in s2["reply_parts"][0].lower()
        assert "what is your email address" in s2["reply_parts"][-1].lower()

        # Turn 3: User provides email and booking advances
        s3 = await graph.ainvoke(
            {"messages": [HumanMessage(content="morgan@example.com")]},
            config=config,
        )
        assert s3["booking"]["status"] == "awaiting_slot"
        assert s3["booking"]["full_name"] == "Morgan Freeman"
        assert s3["booking"]["email"] == "morgan@example.com"
        assert len(s3["booking"]["offered_slots"]) == 3


@pytest.mark.asyncio
async def test_interleaving_compound_turn_name_email_and_faq(tmp_path):
    """AR-040 & GR-007: Single compound message providing details AND asking an FAQ question."""
    db_file = str(tmp_path / "checkpoints.sqlite")
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async with AsyncSqliteSaver.from_conn_string(db_file) as cp:
        await cp.setup()
        graph = build_graph(checkpointer=cp)

        # Compound turn
        s1 = await graph.ainvoke(
            {"messages": [HumanMessage(content="Book a review. Jordan Smith (jordan.smith@example.com). Also how often are performance reviews conducted according to the handbook?")]},
            config=config,
        )

        assert s1["booking"]["status"] == "awaiting_slot"
        assert s1["booking"]["full_name"] == "Jordan Smith"
        assert s1["booking"]["email"] == "jordan.smith@example.com"
        assert len(s1["citations"]) >= 1
        assert s1["citations"][0]["page"] == 4
        reply_text = "\n\n".join(s1["reply_parts"])
        assert "annually" in reply_text.lower()
        assert "available slots" in reply_text.lower()


@pytest.mark.asyncio
async def test_interleaving_cancellation_during_interleave(tmp_path):
    """User cancels booking after an interleaved FAQ interaction."""
    db_file = str(tmp_path / "checkpoints.sqlite")
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    async with AsyncSqliteSaver.from_conn_string(db_file) as cp:
        await cp.setup()
        graph = build_graph(checkpointer=cp)

        # Turn 1: Start booking
        await graph.ainvoke(
            {"messages": [HumanMessage(content="Book review for Bruce Wayne (bruce@wayne.com)")]},
            config=config,
        )

        # Turn 2: FAQ
        await graph.ainvoke(
            {"messages": [HumanMessage(content="What are the company values according to the handbook?")]},
            config=config,
        )

        # Turn 3: User decides to cancel
        s3 = await graph.ainvoke(
            {"messages": [HumanMessage(content="Cancel the booking please.")]},
            config=config,
        )
        assert s3["booking"]["status"] == "cancelled"
        assert s3["booking"]["full_name"] is None
        assert s3["booking"]["email"] is None
        assert "cancelled" in s3["reply_parts"][-1].lower()
