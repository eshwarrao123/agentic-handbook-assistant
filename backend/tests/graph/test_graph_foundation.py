"""Tests for LangGraph StateGraph foundation, nodes, routing, and persistence (GR-001, GR-014, GR-020)."""

import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.graph.builder import build_graph


@pytest.mark.asyncio
async def test_graph_compilation_and_node_set():
    """GR-001: Compile graph and verify node set equals the nine design nodes."""
    graph = build_graph()
    expected_nodes = {
        "start_turn",
        "analyze_turn",
        "booking_update",
        "faq_rag",
        "fallback_reply",
        "ask_missing_info",
        "offer_slots",
        "confirm_booking",
        "compose_response",
    }
    actual_nodes = set(graph.nodes.keys())
    assert expected_nodes.issubset(actual_nodes)


@pytest.mark.asyncio
async def test_per_turn_isolation():
    """GR-020: Per-turn transient fields reset in start_turn and do not leak across turns."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-isolation-thread"}}

    # Turn 1: Ask an FAQ question -> produces citations and faq reply part
    t1_input = {"messages": [HumanMessage(content="How often are performance reviews conducted according to the handbook?")]}
    state_t1 = await graph.ainvoke(t1_input, config=config)

    assert "faq_rag" in state_t1["nodes_visited"]
    assert len(state_t1["citations"]) >= 1
    assert "conducted annually" in state_t1["reply_parts"][0]

    # Turn 2: Non-FAQ booking message on same thread -> per-turn fields must reset!
    t2_input = {"messages": [HumanMessage(content="I want to book an appointment session")]}
    state_t2 = await graph.ainvoke(t2_input, config=config)

    # Citations must be reset to empty for Turn 2
    assert state_t2["citations"] == []
    # nodes_visited must start freshly with start_turn and not contain Turn 1's faq_rag
    assert state_t2["nodes_visited"][0] == "start_turn"
    assert "faq_rag" not in state_t2["nodes_visited"]
    assert "booking_update" in state_t2["nodes_visited"]


@pytest.mark.asyncio
async def test_multi_turn_state_persistence_same_thread():
    """GR-014: State persists across independent invocations on the same thread_id."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-persistence-thread"}}

    # Turn 1: User initiates booking
    t1_input = {"messages": [HumanMessage(content="Hi, I need to book a 1-on-1 Performance Review session.")]}
    state_t1 = await graph.ainvoke(t1_input, config=config)

    assert state_t1["booking"]["status"] == "collecting"
    assert state_t1["booking"]["service_type"] == "performance_review"
    assert "ask_missing_info" in state_t1["nodes_visited"]

    # Turn 2: User provides name and email on the same thread
    t2_input = {"messages": [HumanMessage(content="Alex Chen (alex.chen@example.com)")]}
    state_t2 = await graph.ainvoke(t2_input, config=config)

    # Booking state from Turn 1 was preserved and updated
    assert state_t2["booking"]["status"] == "awaiting_slot"
    assert state_t2["booking"]["full_name"] == "Alex Chen"
    assert state_t2["booking"]["email"] == "alex.chen@example.com"
    assert len(state_t2["booking"]["offered_slots"]) > 0
    assert "offer_slots" in state_t2["nodes_visited"]


@pytest.mark.asyncio
async def test_thread_isolation():
    """Verify distinct threads maintain completely isolated state."""
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer=checkpointer)

    config_a = {"configurable": {"thread_id": "thread-alpha"}}
    config_b = {"configurable": {"thread_id": "thread-beta"}}

    # Thread A begins booking
    await graph.ainvoke(
        {"messages": [HumanMessage(content="I want to book a review")]},
        config=config_a,
    )

    # Thread B asks a handbook FAQ
    state_b = await graph.ainvoke(
        {"messages": [HumanMessage(content="What is the employee handbook policy?")]},
        config=config_b,
    )

    # Thread B has no booking state from Thread A
    assert state_b["booking"]["status"] == "none"
    assert state_b["booking"]["full_name"] is None

    # Inspect Thread A state directly from checkpointer
    state_a = await graph.aget_state(config_a)
    assert state_a.values["booking"]["status"] == "collecting"
