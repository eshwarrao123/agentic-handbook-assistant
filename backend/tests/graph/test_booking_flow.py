"""Multi-turn end-to-end booking flow tests matching TEST_PLAN.md §5 (GR-003, GR-004, GR-005, GR-016..018)."""

import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.booking.service import get_booking_service
from app.graph.builder import build_graph


@pytest.fixture(autouse=True)
def reset_booking_service():
    """Reset singleton booking service before each test."""
    svc = get_booking_service()
    svc.reset()
    yield
    svc.reset()


@pytest.mark.asyncio
async def test_multiturn_booking_happy_path():
    """GR-003, GR-004, GR-005: Complete 3-turn happy path dialogue for booking a review."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-happy-path-thread"}}

    # Turn 1: User initiates booking
    t1_input = {"messages": [HumanMessage(content="Hi, I need to book a 1-on-1 Performance Review session.")]}
    s1 = await graph.ainvoke(t1_input, config=config)

    assert s1["booking"]["status"] == "collecting"
    assert s1["booking"]["service_type"] == "performance_review"
    assert "ask_missing_info" in s1["nodes_visited"]
    assert "full name and email" in s1["reply_parts"][-1].lower()

    # Turn 2: User provides name and email
    t2_input = {"messages": [HumanMessage(content="Alex Chen (alex.chen@example.com)")]}
    s2 = await graph.ainvoke(t2_input, config=config)

    assert s2["booking"]["status"] == "awaiting_slot"
    assert s2["booking"]["full_name"] == "Alex Chen"
    assert s2["booking"]["email"] == "alex.chen@example.com"
    assert len(s2["booking"]["offered_slots"]) == 3
    assert "offer_slots" in s2["nodes_visited"]
    assert "1)" in s2["reply_parts"][-1]

    # Turn 3: User selects option 2
    t3_input = {"messages": [HumanMessage(content="option 2")]}
    s3 = await graph.ainvoke(t3_input, config=config)

    assert s3["booking"]["status"] == "confirmed"
    assert s3["booking"]["booking_reference"].startswith("#REV-")
    assert s3["booking"]["confirmed_slot"]["slot_id"] == s2["booking"]["offered_slots"][1]["slot_id"]
    assert "confirm_booking" in s3["nodes_visited"]
    assert "Confirmed!" in s3["reply_parts"][-1]
    assert "(This is a simulated booking; no real calendar entry was created.)" in s3["reply_parts"][-1]


@pytest.mark.asyncio
async def test_booking_slot_selection_by_day_and_time():
    """GR-005: User selects slot using natural language day and time expression ('Mon 3pm')."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-day-time-thread"}}

    # Turn 1: Provide details immediately
    t1_input = {"messages": [HumanMessage(content="I want to book a review. Jordan Smith (jordan@example.com)")]}
    s1 = await graph.ainvoke(t1_input, config=config)
    assert s1["booking"]["status"] == "awaiting_slot"

    # Turn 2: User specifies "Mon 3pm"
    t2_input = {"messages": [HumanMessage(content="Mon 3pm")]}
    s2 = await graph.ainvoke(t2_input, config=config)

    assert s2["booking"]["status"] == "confirmed"
    assert s2["booking"]["confirmed_slot"]["weekday"] == "Monday"
    assert s2["booking"]["confirmed_slot"]["time"] == "15:00"
    assert s2["booking"]["full_name"] == "Jordan Smith"


@pytest.mark.asyncio
async def test_booking_out_of_range_and_recovery():
    """GR-016: Option outside offered range (e.g. 'option 7') explains range and re-offers slots."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-out-of-range-thread"}}

    # Turn 1 & 2: Reach awaiting_slot
    await graph.ainvoke(
        {"messages": [HumanMessage(content="I want to book. Alex Chen (alex@example.com)")]},
        config=config,
    )

    # Turn 2: User says "option 7" (only 3 options offered)
    s2 = await graph.ainvoke(
        {"messages": [HumanMessage(content="option 7")]},
        config=config,
    )

    # Stays in awaiting_slot, explains out of range, re-presents slots
    assert s2["booking"]["status"] == "awaiting_slot"
    assert s2["booking"]["confirmed_slot"] is None
    assert "outside the offered options" in s2["reply_parts"][0]
    assert "offer_slots" in s2["nodes_visited"]

    # Turn 3: User corrects to "1"
    s3 = await graph.ainvoke(
        {"messages": [HumanMessage(content="1")]},
        config=config,
    )
    assert s3["booking"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_booking_ambiguous_selection_and_recovery():
    """GR-017: Ambiguous day-only selection (e.g. 'Monday') requests time specification."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-ambiguous-thread"}}

    await graph.ainvoke(
        {"messages": [HumanMessage(content="Book review for Alex Chen (alex@example.com)")]},
        config=config,
    )

    # Turn 2: User sends "Monday" (ambiguous: 10:30 and 15:00 available)
    s2 = await graph.ainvoke(
        {"messages": [HumanMessage(content="Monday")]},
        config=config,
    )

    assert s2["booking"]["status"] == "awaiting_slot"
    assert "multiple matching slots" in s2["reply_parts"][0]
    assert "offer_slots" in s2["nodes_visited"]

    # Turn 3: User clarifies with option number
    s3 = await graph.ainvoke(
        {"messages": [HumanMessage(content="option 1")]},
        config=config,
    )
    assert s3["booking"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_booking_partial_name_then_email():
    """NEG-002: User provides name only, then provides email on the subsequent turn."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-partial-details-thread"}}

    # Turn 1: Start booking
    await graph.ainvoke(
        {"messages": [HumanMessage(content="Please schedule an appointment.")]},
        config=config,
    )

    # Turn 2: User sends name only
    s2 = await graph.ainvoke(
        {"messages": [HumanMessage(content="My name is Alex Chen")]},
        config=config,
    )

    assert s2["booking"]["status"] == "collecting"
    assert s2["booking"]["full_name"] == "Alex Chen"
    assert s2["booking"]["email"] is None
    assert "What is your email address?" in s2["reply_parts"][-1]
    assert "offer_slots" not in s2["nodes_visited"]

    # Turn 3: User provides email
    s3 = await graph.ainvoke(
        {"messages": [HumanMessage(content="alex.chen@example.com")]},
        config=config,
    )

    assert s3["booking"]["status"] == "awaiting_slot"
    assert s3["booking"]["full_name"] == "Alex Chen"
    assert s3["booking"]["email"] == "alex.chen@example.com"
    assert "offer_slots" in s3["nodes_visited"]


@pytest.mark.asyncio
async def test_booking_invalid_email_stays_collecting():
    """NEG-001: Invalid email input prompts for valid email and retains name."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-invalid-email-thread"}}

    # Turn 1: User provides name
    await graph.ainvoke(
        {"messages": [HumanMessage(content="Book appointment for Alex Chen")]},
        config=config,
    )

    # Turn 2: User provides invalid email
    s2 = await graph.ainvoke(
        {"messages": [HumanMessage(content="alex at notanemail dot com")]},
        config=config,
    )

    assert s2["booking"]["status"] == "collecting"
    assert s2["booking"]["full_name"] == "Alex Chen"
    assert s2["booking"]["email"] is None
    assert "valid email" in s2["reply_parts"][-1].lower()


@pytest.mark.asyncio
async def test_booking_cancellation():
    """User can cancel an in-progress booking at any time."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-cancel-thread"}}

    # Turn 1: Start booking
    await graph.ainvoke(
        {"messages": [HumanMessage(content="I want to schedule a performance review.")]},
        config=config,
    )

    # Turn 2: User cancels
    s2 = await graph.ainvoke(
        {"messages": [HumanMessage(content="Cancel the booking please.")]},
        config=config,
    )

    assert s2["booking"]["status"] == "cancelled"
    assert "cancelled that booking request" in s2["reply_parts"][-1]
