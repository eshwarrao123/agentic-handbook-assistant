"""Deterministic slot inventory and booking service matching TECHNICAL_DESIGN.md §12.1."""

import asyncio
from datetime import datetime, time, timedelta
import random
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

from app.booking.validation import validate_email, validate_full_name
from app.config import settings

# Canonical base date matching API_CONTRACT §5: Monday, 19 Oct 2026
DEFAULT_REFERENCE_DATETIME = datetime(2026, 10, 18, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata"))


class BookingService:
    """Manages deterministic slot inventory, availability, and simulated reservations."""

    def __init__(
        self,
        timezone: Optional[str] = None,
        clock: Optional[Callable[[], datetime]] = None,
        base_datetime: Optional[datetime] = None,
    ):
        self.timezone_name = timezone or settings.BOOKING_TIMEZONE
        self.tz = ZoneInfo(self.timezone_name)
        self.clock = clock or (lambda: datetime.now(self.tz))
        self.base_datetime = base_datetime or DEFAULT_REFERENCE_DATETIME

        self._lock = asyncio.Lock()
        self._booked: Dict[str, Dict[str, Any]] = {}
        self._reference_counter = 4081
        self._inventory: List[Dict[str, Any]] = self._generate_inventory()

    def _generate_inventory(self) -> List[Dict[str, Any]]:
        """Generate the next 5 weekdays x {10:30, 15:00} = 10 slots (TECHNICAL_DESIGN §12.1)."""
        ref_dt = self.base_datetime.astimezone(self.tz)
        slots: List[Dict[str, Any]] = []

        current_date = ref_dt.date()
        # Find next 5 upcoming weekdays (Monday=0 ... Friday=4)
        weekdays_found = 0
        step_days = 0

        while weekdays_found < 5:
            candidate_date = current_date + timedelta(days=step_days)
            step_days += 1

            # Skip weekends (Saturday=5, Sunday=6)
            if candidate_date.weekday() >= 5:
                continue

            # If the candidate date is the reference date itself, only include slots in the future
            weekdays_found += 1

            slot_times = [
                (time(10, 30), "1030", "10:30 AM"),
                (time(15, 0), "1500", "3:00 PM"),
            ]

            for slot_t, id_time_str, label_time_str in slot_times:
                slot_dt = datetime.combine(candidate_date, slot_t, tzinfo=self.tz)
                date_compact = candidate_date.strftime("%Y%m%d")
                slot_id = f"slot-{date_compact}-{id_time_str}"
                label = f"{candidate_date.strftime('%a, %d %b %Y')}, {label_time_str} IST"

                slots.append({
                    "slot_id": slot_id,
                    "start": slot_dt.isoformat(),
                    "label": label,
                    "date": candidate_date.isoformat(),
                    "time": slot_t.strftime("%H:%M"),
                    "weekday": candidate_date.strftime("%A"),
                })

        return slots

    @property
    def inventory(self) -> List[Dict[str, Any]]:
        """Return raw slot inventory list."""
        return list(self._inventory)

    @property
    def timezone(self) -> str:
        """Return configured timezone string."""
        return self.timezone_name

    def get_available_slots(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return available (unbooked) slots, optionally capped by limit."""
        available = [s for s in self._inventory if s["slot_id"] not in self._booked]
        if limit is not None and limit > 0:
            return available[:limit]
        return available

    def get_total_available_count(self) -> int:
        """Return total count of available slots across full inventory."""
        return len(self.get_available_slots())

    def get_slot_by_id(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Look up a slot by its unique slot_id."""
        for s in self._inventory:
            if s["slot_id"] == slot_id:
                return dict(s)
        return None

    def is_slot_available(self, slot_id: str) -> bool:
        """Check if a slot exists and has not been booked."""
        slot = self.get_slot_by_id(slot_id)
        if not slot:
            return False
        return slot_id not in self._booked

    def generate_reference(self) -> str:
        """Generate a simulated booking reference in the format #REV-NNNN."""
        ref_num = self._reference_counter
        self._reference_counter += 1
        if self._reference_counter > 9999:
            self._reference_counter = 1000
        return f"#REV-{ref_num:04d}"

    async def create_booking(
        self,
        full_name: str,
        email: str,
        slot_id: str,
    ) -> Dict[str, Any]:
        """Create a simulated booking with authoritative validation and locking (TECHNICAL_DESIGN §12.2).
        
        Returns:
            Success: {ok: True, reference: str, slot: dict, full_name: str, email: str, service_type: str, simulated: True}
            Failure: {ok: False, code: str, message: str}
        """
        # 1. Authoritative application validation (never trust LLM for validation)
        is_name_valid, clean_name_or_err = validate_full_name(full_name)
        if not is_name_valid:
            return {
                "ok": False,
                "code": "INVALID_NAME",
                "message": clean_name_or_err,
            }

        is_email_valid, clean_email_or_err = validate_email(email)
        if not is_email_valid:
            return {
                "ok": False,
                "code": "INVALID_EMAIL",
                "message": clean_email_or_err,
            }

        # 2. Verify slot existence
        slot = self.get_slot_by_id(slot_id)
        if not slot:
            return {
                "ok": False,
                "code": "SLOT_NOT_FOUND",
                "message": f"Appointment slot '{slot_id}' does not exist in inventory.",
            }

        # 3. Guard against concurrent race conditions
        async with self._lock:
            if slot_id in self._booked:
                return {
                    "ok": False,
                    "code": "SLOT_UNAVAILABLE",
                    "message": f"The selected slot ({slot['label']}) has already been booked. Please choose another time.",
                }

            reference = self.generate_reference()
            booking_record = {
                "reference": reference,
                "slot": slot,
                "full_name": clean_name_or_err,
                "email": clean_email_or_err,
                "service_type": "performance_review",
                "simulated": True,
                "created_at": datetime.now(self.tz).isoformat(),
            }
            self._booked[slot_id] = booking_record

            return {
                "ok": True,
                "reference": reference,
                "slot": slot,
                "full_name": clean_name_or_err,
                "email": clean_email_or_err,
                "service_type": "performance_review",
                "simulated": True,
            }

    def reset(self) -> None:
        """Reset booked slots for test isolation."""
        self._booked.clear()
        self._reference_counter = 4081


# Singleton booking service instance
booking_service = BookingService()


def get_booking_service() -> BookingService:
    """Return singleton BookingService instance."""
    return booking_service
