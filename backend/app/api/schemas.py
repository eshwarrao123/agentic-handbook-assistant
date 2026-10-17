"""API request and response schemas matching docs/API_CONTRACT.md."""

from typing import Literal
from pydantic import BaseModel, Field


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
