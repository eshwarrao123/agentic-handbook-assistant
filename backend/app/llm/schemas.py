"""Pydantic schemas for LLM structured outputs matching TECHNICAL_DESIGN.md §13."""

from typing import List, Optional
from pydantic import BaseModel, Field


class GroundedAnswer(BaseModel):
    """Structured response from LLM for grounded handbook question answering."""
    answerable: bool = Field(
        ...,
        description="True if the provided handbook passages directly answer the question; False otherwise.",
    )
    answer: str = Field(
        default="",
        description="Concise, factual answer formulated strictly from the provided passages. Empty if answerable=False.",
    )
    used_chunk_ids: List[str] = Field(
        default_factory=list,
        description="List of chunk_ids from the provided context that directly contributed to this answer.",
    )


class TurnAnalysis(BaseModel):
    """Structured response from LLM for conversational turn analysis."""
    intents: List[str] = Field(
        default_factory=list,
        description="List of detected intents: 'booking', 'faq', 'greeting', 'other'.",
    )
    booking_requested: bool = Field(
        default=False,
        description="True if the user requested to book, schedule, or start a performance review session.",
    )
    cancel_requested: bool = Field(
        default=False,
        description="True if the user explicitly requested to cancel or abort the current booking.",
    )
    name_candidate: Optional[str] = Field(
        default=None,
        description="Extracted full name candidate, if provided by the user in this turn.",
    )
    email_candidate: Optional[str] = Field(
        default=None,
        description="Extracted email address candidate, if provided by the user in this turn.",
    )
    slot_text: Optional[str] = Field(
        default=None,
        description="User's slot selection utterance (e.g. 'option 2', 'Monday 3pm'), if present.",
    )
    faq_question: Optional[str] = Field(
        default=None,
        description="Standalone question about company policy or handbook, if present.",
    )
