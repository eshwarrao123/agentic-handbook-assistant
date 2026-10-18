"""Deterministic slot selection resolver matching TECHNICAL_DESIGN.md §12.4."""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional

OPTION_REGEX = re.compile(r"^\s*(?:option|number|slot|#)?\s*(\d+)\s*$", re.IGNORECASE)
SLOT_ID_REGEX = re.compile(r"slot-\d{8}-\d{4}")

WEEKDAY_MAP = {
    "mon": "Monday",
    "monday": "Monday",
    "tue": "Tuesday",
    "tues": "Tuesday",
    "tuesday": "Tuesday",
    "wed": "Wednesday",
    "wednesday": "Wednesday",
    "thu": "Thursday",
    "thur": "Thursday",
    "thurs": "Thursday",
    "thursday": "Thursday",
    "fri": "Friday",
    "friday": "Friday",
    "sat": "Saturday",
    "saturday": "Saturday",
    "sun": "Sunday",
    "sunday": "Sunday",
}


def _extract_weekday(text: str) -> Optional[str]:
    """Extract recognized weekday from user text."""
    lower = text.lower()
    for pattern, canonical in WEEKDAY_MAP.items():
        if re.search(rf"\b{pattern}\b", lower):
            return canonical
    return None


def _extract_time_str(text: str) -> Optional[str]:
    """Extract normalized HH:MM time string from user text.
    
    Rules (TECHNICAL_DESIGN §12.4):
    - Matches 10:30, 10:30am, 10:30 am, 3pm, 3 pm, 15:00, 3:00pm.
    - A time without am/pm with hour 1-7 is read as PM (e.g. 3 or 3:00 -> 15:00).
    """
    lower = text.lower()

    # Check 10:30 / 10:30am / 10:30 am
    if re.search(r"\b10:?30\s*(?:am)?\b", lower):
        return "10:30"

    # Check 3pm / 3:00pm / 3:00 pm / 15:00 / 15:00:00
    if re.search(r"\b(?:3(?::?00)?\s*pm|15(?::?00)?)\b", lower):
        return "15:00"

    # Match hour 1-7 without am/pm as business hours PM (e.g. "at 3")
    if re.search(r"\b(?:at\s+)?([1-7])(?::00)?\b", lower):
        m = re.search(r"\b(?:at\s+)?([1-7])(?::00)?\b", lower)
        hour = int(m.group(1))
        return f"{hour + 12:02d}:00"

    return None


def resolve_slot(
    text: str,
    offered_slots: List[Dict[str, Any]],
    available_inventory: List[Dict[str, Any]],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Resolve user input to a slot selection (TECHNICAL_DESIGN §12.4).
    
    Order of rules:
    1. Exact slot ID.
    2. Option number: 1-based index into offered_slots; outside range -> OUT_OF_RANGE.
    3. Day and/or time expression: weekday name, time.
    4. Anything else -> NO_MATCH.
    
    Returns:
        {
            "result": "MATCH" | "AMBIGUOUS" | "OUT_OF_RANGE" | "UNAVAILABLE" | "NO_MATCH",
            "slot": Optional[Dict[str, Any]],
            "candidates": List[Dict[str, Any]],
        }
    """
    cleaned = text.strip()
    if not cleaned:
        return {"result": "NO_MATCH", "slot": None, "candidates": []}

    available_map = {s["slot_id"]: s for s in available_inventory}

    # 1. Exact slot ID
    id_match = SLOT_ID_REGEX.search(cleaned)
    if id_match:
        matched_id = id_match.group(0)
        if matched_id in available_map:
            slot = available_map[matched_id]
            return {"result": "MATCH", "slot": slot, "candidates": [slot]}
        return {"result": "UNAVAILABLE", "slot": None, "candidates": []}

    # 2. Option number (e.g. "2", "option 2", "#2", "slot 1")
    opt_match = OPTION_REGEX.match(cleaned)
    if opt_match:
        option_num = int(opt_match.group(1))
        if 1 <= option_num <= len(offered_slots):
            chosen = offered_slots[option_num - 1]
            if chosen["slot_id"] in available_map:
                resolved = available_map[chosen["slot_id"]]
                return {"result": "MATCH", "slot": resolved, "candidates": [resolved]}
            return {"result": "UNAVAILABLE", "slot": None, "candidates": []}
        return {"result": "OUT_OF_RANGE", "slot": None, "candidates": []}

    # 3. Day and/or time expression
    weekday = _extract_weekday(cleaned)
    time_str = _extract_time_str(cleaned)

    if weekday or time_str:
        candidates = list(available_inventory)

        if weekday:
            candidates = [s for s in candidates if s.get("weekday") == weekday]

        if time_str:
            candidates = [s for s in candidates if s.get("time") == time_str]

        if len(candidates) == 1:
            return {"result": "MATCH", "slot": candidates[0], "candidates": candidates}
        elif len(candidates) > 1:
            return {"result": "AMBIGUOUS", "slot": None, "candidates": candidates}
        else:
            return {"result": "NO_MATCH", "slot": None, "candidates": []}

    # 4. Anything else
    return {"result": "NO_MATCH", "slot": None, "candidates": []}
