"""API request and response schemas matching docs/API_CONTRACT.md."""

from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


# --- Health Diagnostics Schemas (API_CONTRACT §4) ---

class VectorStoreHealth(BaseModel):
    status: str = Field(
        default="not_initialized",
        description="Vector store component status: ok, unavailable, or not_initialized.",
    )
    collection: str = Field(
        default="handbook",
        description="ChromaDB collection name.",
    )
    chunk_count: int = Field(
        default=0,
        description="Number of indexed handbook chunks.",
    )


class CheckpointerHealth(BaseModel):
    status: str = Field(
        default="not_initialized",
        description="Checkpointer component status: ok, unavailable, or not_initialized.",
    )
    backend: str = Field(
        default="sqlite",
        description="Checkpoint persistence backend.",
    )


class LLMHealth(BaseModel):
    status: str = Field(
        default="not_configured",
        description="LLM configuration status: configured or not_configured.",
    )
    provider: str = Field(
        default="groq",
        description="Configured LLM provider name.",
    )


class ComponentsHealth(BaseModel):
    vector_store: VectorStoreHealth = Field(default_factory=VectorStoreHealth)
    checkpointer: CheckpointerHealth = Field(default_factory=CheckpointerHealth)
    llm: LLMHealth = Field(default_factory=LLMHealth)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "unavailable"] = Field(
        description="Overall service health: ok, degraded, or unavailable.",
    )
    version: str = Field(
        description="Backend application version.",
    )
    time: str = Field(
        description="Current server timestamp in ISO-8601 format.",
    )
    components: ComponentsHealth = Field(
        description="Diagnostic status of subsystems.",
    )


# --- Chat and Booking Schemas (API_CONTRACT §2, §3, §6) ---

class Slot(BaseModel):
    slot_id: str = Field(description="Unique slot identifier (e.g., slot-20261019-1500).")
    start: str = Field(description="ISO-8601 start timestamp with timezone offset.")
    label: str = Field(description="Human-readable slot label.")


class Citation(BaseModel):
    document: str = Field(description="Referenced file name (e.g., employee_handbook.pdf).")
    title: str = Field(description="Human-readable document title.")
    page: int = Field(ge=1, description="1-based PDF page index.")
    snippet: str = Field(description="Short quote extracted from the retrieved chunk.")
    chunk_id: str = Field(description="Chunk identifier (e.g., employee_handbook.pdf-p4-c0).")


class Confirmation(BaseModel):
    reference: str = Field(pattern=r"^#REV-\d{4}$", description="Booking reference code.")
    slot: Slot = Field(description="Confirmed appointment slot.")
    full_name: str = Field(description="Attendee's validated full name.")
    email: str = Field(description="Attendee's validated email address.")
    service_type: str = Field(default="performance_review", description="Booked service type.")
    simulated: bool = Field(default=True, description="True for simulated bookings.")


class BookingSnapshot(BaseModel):
    status: Literal["none", "collecting", "awaiting_slot", "confirmed", "cancelled"] = Field(
        default="none",
        description="Current multi-turn booking state machine status.",
    )
    service_type: Optional[str] = Field(default=None, description="Active service type.")
    full_name: Optional[str] = Field(default=None, description="Validated full name.")
    email: Optional[str] = Field(default=None, description="Validated email address.")
    offered_slots: List[Slot] = Field(default_factory=list, description="Currently offered slots.")
    confirmation: Optional[Confirmation] = Field(
        default=None,
        description="Non-null if status is confirmed.",
    )


class AgentInfo(BaseModel):
    status: Literal["ok", "degraded"] = Field(
        default="ok",
        description="Agent execution status.",
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable degradation code (e.g., ANALYSIS_FALLBACK, FAQ_UNAVAILABLE).",
    )
    intents: List[Literal["booking", "faq"]] = Field(
        default_factory=list,
        description="Intents detected in the user's turn.",
    )
    route: List[str] = Field(
        default_factory=list,
        description="List of graph nodes visited during this turn, in order.",
    )


class ChatReply(BaseModel):
    message_id: str = Field(description="Unique UUID for this assistant message.")
    role: Literal["assistant"] = Field(default="assistant", description="Message role.")
    content: str = Field(description="Assistant textual reply.")
    citations: List[Citation] = Field(
        default_factory=list,
        description="Code-built citations for grounded RAG answers.",
    )
    created_at: str = Field(description="ISO-8601 creation timestamp.")


class ChatRequest(BaseModel):
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional conversation thread UUID. Null creates a new thread.",
    )
    message: str = Field(
        description="User message text. Must be between 1 and 2000 non-whitespace characters.",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("must not be empty or whitespace only")
        if len(trimmed) > 2000:
            raise ValueError("message must contain between 1 and 2000 characters.")
        return trimmed


class ChatResponse(BaseModel):
    thread_id: str = Field(description="Conversation thread identifier.")
    is_new_thread: bool = Field(description="True if this turn initialized a new conversation.")
    reply: ChatReply = Field(description="Assistant reply object.")
    booking: BookingSnapshot = Field(description="Structured booking snapshot after this turn.")
    agent: AgentInfo = Field(description="Agent execution metadata.")


# --- Error Envelope Schemas (API_CONTRACT §2) ---

class ErrorDetail(BaseModel):
    code: str = Field(description="Stable machine-readable error code.")
    message: str = Field(description="Human-readable, safe-for-display error message.")
    retryable: bool = Field(description="Hint indicating whether the client may retry.")
    request_id: str = Field(description="Correlating X-Request-ID.")
    details: Optional[Any] = Field(
        default=None,
        description="Additional validation or contextual details.",
    )


class ErrorEnvelope(BaseModel):
    error: ErrorDetail = Field(description="Standardized error envelope.")
