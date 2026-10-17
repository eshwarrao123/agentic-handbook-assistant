"""FastAPI application entrypoint for Agentic Handbook Assistant."""

import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes_health import router as health_router
from app.config import settings


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Ensure every response carries an X-Request-ID header, echoing incoming or generating a new ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:8]}"
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def create_app() -> FastAPI:
    """Factory creating and configuring the FastAPI application."""
    application = FastAPI(
        title="Agentic Handbook Assistant API",
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Request ID tracing middleware (API_CONTRACT §1)
    application.add_middleware(RequestIdMiddleware)

    # CORS configuration for local frontend development (ARCHITECTURE §10, API_CONTRACT §1)
    origins = (
        settings.CORS_ORIGINS
        if isinstance(settings.CORS_ORIGINS, list)
        else [settings.CORS_ORIGINS]
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Mount API routes
    application.include_router(health_router, prefix="/api")

    return application


app = create_app()
