"""Node: fallback_reply (TECHNICAL_DESIGN §6, Node 5).

Handles user turns that contain neither an FAQ query nor an active booking signal.
Appends a friendly orientation message to reply_parts.
"""

from typing import Any, Dict
from app.graph.state import AgentState


def fallback_reply(state: AgentState) -> Dict[str, Any]:
    """Execute fallback_reply node."""
    reply_parts = list(state.get("reply_parts") or [])
    visited = list(state.get("nodes_visited") or []) + ["fallback_reply"]

    message = (
        "I can help answer questions about company policies from the employee handbook "
        "or assist you in booking a 1-on-1 Performance Review session. How may I help you today?"
    )
    reply_parts.append(message)

    return {
        "reply_parts": reply_parts,
        "nodes_visited": visited,
    }
