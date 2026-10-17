"""LangGraph state schemas and custom reducers matching docs/TECHNICAL_DESIGN.md §5."""

from typing import Annotated, Any, Dict, List, Literal, Optional
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


# Valid status values for the multi-turn booking state machine
BookingStatus = Literal["none", "collecting", "awaiting_slot", "confirmed", "cancelled"]


class BookingState(TypedDict, total=False):
    """Authoritative structured booking state (TECHNICAL_DESIGN §5.1).
    
    Contains only plain JSON-serializable primitives (dict, list, str, None)
    to guarantee safe persistence across SQLite checkpointers.
    """
    status: BookingStatus
    service_type: Optional[str]
    full_name: Optional[str]
    email: Optional[str]
    offered_slots: List[Dict[str, Any]]
    selected_slot_id: Optional[str]
    booking_reference: Optional[str]
    confirmed_slot: Optional[Dict[str, Any]]


def default_booking_state() -> BookingState:
    """Return default empty booking state."""
    return {
        "status": "none",
        "service_type": None,
        "full_name": None,
        "email": None,
        "offered_slots": [],
        "selected_slot_id": None,
        "booking_reference": None,
        "confirmed_slot": None,
    }


def reset_booking_update(status: BookingStatus = "none") -> BookingState:
    """Return an explicit reset dictionary for cancellation or starting a fresh booking (TECHNICAL_DESIGN §5.3)."""
    state = default_booking_state()
    state["status"] = status
    return state


def merge_booking(
    current: Optional[BookingState],
    update: Optional[Dict[str, Any]],
) -> BookingState:
    """Merge reducer for structured booking state (TECHNICAL_DESIGN §5.3).
    
    Rules:
    1. Treats a missing or empty current state as default_booking_state().
    2. If update is None or empty, returns current state (or default).
    3. Keys present in update overwrite current keys; absent keys are preserved.
       An explicit None value intentionally clears that key.
    4. Rejects unknown keys to prevent typos from silently creating orphaned state.
    """
    base = dict(default_booking_state() if not current else current)

    if not update:
        return BookingState(**base)

    valid_keys = set(default_booking_state().keys())
    for key in update.keys():
        if key not in valid_keys:
            raise KeyError(f"Unknown booking field: '{key}'. Valid keys are: {sorted(valid_keys)}")

    for key, value in update.items():
        base[key] = value

    return BookingState(**base)


class AgentState(TypedDict, total=False):
    """Authoritative graph state for Agentic Handbook Assistant (TECHNICAL_DESIGN §5.2)."""
    # Persistent thread-scoped fields with reducers
    messages: Annotated[List[AnyMessage], add_messages]
    booking: Annotated[BookingState, merge_booking]

    # Per-turn transient fields (overwrite semantics; explicitly reset in start_turn)
    user_text: str
    intents: List[str]
    booking_requested: bool
    cancel_requested: bool
    name_candidate: Optional[str]
    email_candidate: Optional[str]
    slot_text: Optional[str]
    faq_question: Optional[str]
    reply_parts: List[str]
    citations: List[Dict[str, Any]]
    nodes_visited: List[str]
    degraded: bool
    error_code: Optional[str]
