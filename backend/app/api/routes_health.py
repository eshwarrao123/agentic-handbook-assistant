"""Health and diagnostics route."""

from datetime import datetime, timezone
import os
from fastapi import APIRouter

from app.api.schemas import (
    HealthResponse,
    ComponentsHealth,
    VectorStoreHealth,
    CheckpointerHealth,
    LLMHealth,
)
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Return application readiness and component status without invoking external services."""
    # Inspect whether an LLM key is configured in the environment without calling the API
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GOOGLE_API_KEY")
    llm_configured = bool((settings.LLM_PROVIDER == "groq" and groq_key) or
                          (settings.LLM_PROVIDER == "gemini" and gemini_key))

    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        time=datetime.now(timezone.utc).isoformat(),
        components=ComponentsHealth(
            vector_store=VectorStoreHealth(
                status="not_initialized",
                collection="handbook",
                chunk_count=0,
            ),
            checkpointer=CheckpointerHealth(
                status="not_initialized",
                backend="sqlite",
            ),
            llm=LLMHealth(
                status="configured" if llm_configured else "not_configured",
                provider=settings.LLM_PROVIDER,
            ),
        ),
    )
