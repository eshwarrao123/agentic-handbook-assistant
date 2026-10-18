"""Node: analyze_turn (TECHNICAL_DESIGN §6, Node 2).

Deterministic development router analyzing user turns for booking intents,
cancellations, name/email candidates, slot selection utterances, and FAQ queries.
"""

import re
from typing import Any, Dict, List, Optional
from app.graph.state import AgentState

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
BOOKING_PATTERN = re.compile(
    r"\b(book|booking|schedule|performance review|appointment|session|reserve)\b",
    re.IGNORECASE,
)
CANCEL_PATTERN = re.compile(r"\b(cancel|never mind|start over|abort)\b", re.IGNORECASE)
SLOT_PATTERN = re.compile(
    r"\b(option\s*\d+|#?\d+|monday|tuesday|wednesday|thursday|friday|10:30|3pm|15:00|slot-\d{8}-\d{4})\b",
    re.IGNORECASE,
)
FAQ_START_WORDS = ("how", "what", "when", "where", "why", "who", "is", "can", "does")


def analyze_turn(state: AgentState) -> Dict[str, Any]:
    """Execute analyze_turn router brain (deterministic version)."""
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

    # 1. Check cancellation with word boundary
    if CANCEL_PATTERN.search(user_text):
        cancel_requested = True
        intents.append("booking")

    # 2. Check booking request with word boundary (prevents 'handbook' matching 'book')
    if BOOKING_PATTERN.search(user_text):
        booking_requested = True
        if "booking" not in intents:
            intents.append("booking")

    # 3. Check FAQ questions
    has_question_mark = "?" in user_text
    starts_with_wh = any(user_lower.startswith(w + " ") for w in FAQ_START_WORDS)
    has_faq_keywords = any(
        w in user_lower for w in ("handbook", "policy", "conducted", "review", "pto", "vacation", "benefits")
    )

    if has_question_mark:
        # If user text is a compound message (e.g. booking details + question), isolate the question part
        sentences = [s.strip() for s in re.split(r"(?<=[.?])\s+", user_text) if s.strip()]
        q_sentences = [s for s in sentences if "?" in s or any(s.lower().startswith(w + " ") for w in FAQ_START_WORDS)]
        faq_question = " ".join(q_sentences) if q_sentences else user_text
        if "faq" not in intents:
            intents.append("faq")
    elif starts_with_wh and has_faq_keywords:
        faq_question = user_text
        if "faq" not in intents:
            intents.append("faq")

    # 4. Deterministic email extraction
    email_match = EMAIL_REGEX.search(user_text)
    if email_match:
        email_candidate = email_match.group(0)
    elif status == "collecting" and booking.get("full_name") and not booking.get("email") and not cancel_requested and not faq_question:
        email_candidate = user_text.strip()

    # 5. Extract name candidate
    if email_match:
        # Text preceding email address or parentheses
        prefix = user_text[:email_match.start()].strip(" (,\n\t")
        if "." in prefix:
            prefix = prefix.rsplit(".", 1)[-1].strip()
        for_split = re.split(r"\bfor\s+", prefix, flags=re.IGNORECASE)
        if len(for_split) > 1:
            prefix = for_split[-1].strip()

        tokens = prefix.split()
        if 2 <= len(tokens) <= 4 and not prefix.endswith("?"):
            name_candidate = prefix
    elif not email_candidate:
        # Check patterns like "Book appointment for Alex Chen", "My name is Alex Chen", or direct "Alex Chen"
        for_match = re.search(
            r"\b(?:for|my name is|i am|i'm|this is)\s+([a-zA-Z\s'\-\.]+)",
            user_text,
            re.IGNORECASE,
        )
        if for_match:
            candidate = for_match.group(1).strip()
            tokens = candidate.split()
            if 2 <= len(tokens) <= 4:
                name_candidate = candidate
        elif status == "collecting" and not booking_requested and not cancel_requested and not faq_question:
            tokens = user_text.strip().split()
            if 2 <= len(tokens) <= 4 and not any(user_lower.startswith(w) for w in FAQ_START_WORDS):
                name_candidate = user_text.strip()

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
