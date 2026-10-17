"""Node: analyze_turn (TECHNICAL_DESIGN §6, Node 2).

TEMPORARY DEVELOPMENT IMPLEMENTATION:
This node currently uses deterministic heuristic pattern matching to exercise graph
routing paths during development and testing without requiring live external LLM calls.
The full structured LLM intent classifier (Groq / Gemini) will replace this in Phase 4.
"""

import re
from typing import Any, Dict, List, Optional
from app.graph.state import AgentState

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
BOOKING_PATTERN = re.compile(r"\b(book|booking|schedule|performance review|appointment|session|reserve)\b", re.IGNORECASE)
CANCEL_PATTERN = re.compile(r"\b(cancel|never mind|start over|abort)\b", re.IGNORECASE)
SLOT_PATTERN = re.compile(r"\b(option\s*\d+|#?\d+|monday|tuesday|wednesday|thursday|friday)\b", re.IGNORECASE)
FAQ_START_WORDS = ("how", "what", "when", "where", "why", "who", "is", "can", "does")


def analyze_turn(state: AgentState) -> Dict[str, Any]:
    """Execute analyze_turn router brain (deterministic development version)."""
    user_text = state.get("user_text", "").strip()
    user_lower = user_text.lower()
    booking = state.get("booking") or {}
    status = booking.get("status", "none")

    intents: List[str] = []
    booking_requested = False
    cancel_requested = False
    name_candidate: Optional[str] = None
    email_candidate: Optional[str] = None
    slot_text: Optional[str] = None
    faq_question: Optional[str] = None

    # 1. Deterministic email extraction
    email_match = EMAIL_REGEX.search(user_text)
    if email_match:
        email_candidate = email_match.group(0)

    # 2. Check cancellation with word boundary
    if CANCEL_PATTERN.search(user_text):
        cancel_requested = True
        intents.append("booking")

    # 3. Check booking request with word boundary (prevents 'handbook' from matching 'book')
    if BOOKING_PATTERN.search(user_text):
        booking_requested = True
        if "booking" not in intents:
            intents.append("booking")

    # 4. Check FAQ questions
    has_question_mark = "?" in user_text
    starts_with_wh = any(user_lower.startswith(w + " ") for w in FAQ_START_WORDS)
    has_faq_keywords = any(w in user_lower for w in ("handbook", "policy", "conducted", "review"))
    
    if has_question_mark or (starts_with_wh and has_faq_keywords):
        faq_question = user_text
        if "faq" not in intents:
            intents.append("faq")

    # 5. Extract name candidate when in collecting state or details provided
    if email_candidate:
        # Heuristic: Text before email or parentheses might be a name
        prefix = user_text[:user_text.find(email_candidate)].strip(" (,\n\t")
        if prefix and len(prefix.split()) <= 4 and not prefix.endswith("?"):
            name_candidate = prefix

    # 6. Check slot choice candidate (e.g., "option 2", "#2", "2", "Monday at 3pm")
    if status == "awaiting_slot":
        if SLOT_PATTERN.search(user_text):
            slot_text = user_text
            if "booking" not in intents:
                intents.append("booking")

    # If details were extracted while booking is active, ensure booking intent is set
    if (name_candidate or email_candidate or slot_text) and status in ("collecting", "awaiting_slot"):
        if "booking" not in intents:
            intents.append("booking")

    # Appending this node to nodes_visited
    visited = list(state.get("nodes_visited") or []) + ["analyze_turn"]

    return {
        "intents": intents,
        "booking_requested": booking_requested,
        "cancel_requested": cancel_requested,
        "name_candidate": name_candidate,
        "email_candidate": email_candidate,
        "slot_text": slot_text,
        "faq_question": faq_question,
        "nodes_visited": visited,
    }
