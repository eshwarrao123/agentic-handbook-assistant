from contextlib import asynccontextmanager
import logging
import os
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.errors import generic_exception_handler, register_error_handlers
from app.api.routes_chat import router as chat_router
from app.api.routes_health import router as health_router
from app.api.routes_slots import router as slots_router
from app.config import settings
from app.services.chat_service import ChatService

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage runtime checkpointer lifecycle (TECHNICAL_DESIGN §2 & §10, D-05, AR-012)."""
    db_path = settings.CHECKPOINT_DB_PATH
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    try:
        async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
            await checkpointer.setup()
            app.state.checkpointer = checkpointer
            app.state.chat_service = ChatService(checkpointer=checkpointer)
            logger.info("AsyncSqliteSaver initialized successfully at %s", db_path)
            yield
    except Exception as exc:
        logger.critical("Failed to initialize AsyncSqliteSaver at %s: %s", db_path, exc)
        raise
    finally:
        app.state.checkpointer = None
        app.state.chat_service = None


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Ensure every response carries an X-Request-ID header, echoing incoming or generating a new ID."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:8]}"
        request.state.request_id = request_id
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            return await generic_exception_handler(request, exc)


def create_app() -> FastAPI:
    """Factory creating and configuring the FastAPI application."""
    application = FastAPI(
        title="Agentic Handbook Assistant API",
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Request ID tracing middleware (API_CONTRACT §1)
    application.add_middleware(RequestIdMiddleware)

    # Register standardized error envelope handlers (API_CONTRACT §2, V-11)
    register_error_handlers(application)

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
    application.include_router(chat_router, prefix="/api")
    application.include_router(slots_router, prefix="/api")

    return application


app = create_app()
