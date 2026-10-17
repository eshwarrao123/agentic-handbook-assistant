"""Graph builder and compiler matching docs/TECHNICAL_DESIGN.md §6.4 and §7.2."""

from typing import Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph.nodes.analyze_turn import analyze_turn
from app.graph.nodes.booking_steps import ask_missing_info, confirm_booking, offer_slots
from app.graph.nodes.booking_update import booking_update
from app.graph.nodes.compose_response import compose_response
from app.graph.nodes.fallback_reply import fallback_reply
from app.graph.nodes.faq_rag import faq_rag
from app.graph.nodes.start_turn import start_turn
from app.graph.routing import (
    route_after_analysis,
    route_after_booking_update,
    route_resume_booking,
)
from app.graph.state import AgentState


def build_graph(checkpointer: Optional[BaseCheckpointSaver] = None) -> CompiledStateGraph:
    """Build and compile the 9-node StateGraph for Agentic Handbook Assistant."""
    builder = StateGraph(AgentState)

    # 1. Register all nine design nodes
    builder.add_node("start_turn", start_turn)
    builder.add_node("analyze_turn", analyze_turn)
    builder.add_node("booking_update", booking_update)
    builder.add_node("faq_rag", faq_rag)
    builder.add_node("fallback_reply", fallback_reply)
    builder.add_node("ask_missing_info", ask_missing_info)
    builder.add_node("offer_slots", offer_slots)
    builder.add_node("confirm_booking", confirm_booking)
    builder.add_node("compose_response", compose_response)

    # 2. Add static entry edges
    builder.add_edge(START, "start_turn")
    builder.add_edge("start_turn", "analyze_turn")

    # 3. Add conditional routing edges (TECHNICAL_DESIGN §7.2)
    builder.add_conditional_edges(
        "analyze_turn",
        route_after_analysis,
        {
            "booking_update": "booking_update",
            "faq_rag": "faq_rag",
            "fallback_reply": "fallback_reply",
        },
    )

    builder.add_conditional_edges(
        "booking_update",
        route_after_booking_update,
        {
            "faq_rag": "faq_rag",
            "ask_missing_info": "ask_missing_info",
            "offer_slots": "offer_slots",
            "confirm_booking": "confirm_booking",
            "compose_response": "compose_response",
        },
    )

    builder.add_conditional_edges(
        "faq_rag",
        route_resume_booking,
        {
            "ask_missing_info": "ask_missing_info",
            "offer_slots": "offer_slots",
            "confirm_booking": "confirm_booking",
            "compose_response": "compose_response",
        },
    )

    builder.add_conditional_edges(
        "fallback_reply",
        route_resume_booking,
        {
            "ask_missing_info": "ask_missing_info",
            "offer_slots": "offer_slots",
            "confirm_booking": "confirm_booking",
            "compose_response": "compose_response",
        },
    )

    # 4. Add static convergence edges to compose_response and END
    builder.add_edge("ask_missing_info", "compose_response")
    builder.add_edge("offer_slots", "compose_response")
    builder.add_edge("confirm_booking", "compose_response")
    builder.add_edge("compose_response", END)

    return builder.compile(checkpointer=checkpointer)
