"""Node: start_turn (TECHNICAL_DESIGN §6, Node 1).

Per-turn hygiene:
- Extracts the latest user message text into state["user_text"].
- Resets all transient per-turn fields (intents, reply_parts, citations, nodes_visited, candidates).
- Initializes booking state ONLY IF it is currently absent. Never touches an existing booking.
"""

from typing import Any, Dict
from langchain_core.messages import HumanMessage
from app.graph.state import AgentState, default_booking_state


def start_turn(state: AgentState) -> Dict[str, Any]:
    """Execute start_turn hygiene node."""
    # Extract latest human message content
    messages = state.get("messages") or []
    user_text = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) or getattr(msg, "type", None) == "human":
            user_text = str(msg.content or "").strip()
            break
        elif isinstance(msg, dict) and msg.get("role") in ("user", "human"):
            user_text = str(msg.get("content") or "").strip()
            break

    # Per-turn reset dictionary (overwrite semantics)
    updates: Dict[str, Any] = {
        "user_text": user_text,
        "intents": [],
        "booking_requested": False,
        "cancel_requested": False,
        "name_candidate": None,
        "email_candidate": None,
        "slot_text": None,
        "faq_question": None,
        "reply_parts": [],
        "citations": [],
        "nodes_visited": ["start_turn"],
        "degraded": False,
        "error_code": None,
    }

    # Initialize booking state ONLY if absent/empty (TECHNICAL_DESIGN §5.2, §6)
    if not state.get("booking"):
        updates["booking"] = default_booking_state()

    return updates
