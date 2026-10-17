"""Standardized error envelope and exception handlers matching docs/API_CONTRACT.md §2."""

import re
import uuid
from typing import Any, Optional
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def validate_thread_id(thread_id: Optional[str]) -> bool:
    """Validate that thread_id is a valid UUIDv4 string (UT-020).
    
    Rejects empty strings, strings without hyphens, strings with braces,
    SQL-like injections, or lengths other than 36.
    """
    if not isinstance(thread_id, str):
        return False
    if len(thread_id) != 36:
        return False
    return bool(UUID_PATTERN.match(thread_id))


class InvalidThreadIdException(Exception):
    """Raised when an incoming thread_id is present but malformed (HTTP 400)."""

    def __init__(self, message: str = "thread_id must be a valid UUID."):
        self.message = message
        super().__init__(self.message)


def _get_request_id(request: Request) -> str:
    """Retrieve or generate correlating request ID."""
    return (
        getattr(request.state, "request_id", None)
        or request.headers.get("X-Request-ID")
        or f"req-{uuid.uuid4().hex[:8]}"
    )


def make_error_envelope(
    code: str,
    message: str,
    retryable: bool,
    request_id: str,
    details: Optional[Any] = None,
) -> dict:
    """Build the standardized error envelope dictionary."""
    return {
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "request_id": request_id,
            "details": details,
        }
    }


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Translate FastAPI Pydantic validation errors into the contract envelope (HTTP 422)."""
    request_id = _get_request_id(request)
    formatted_details = []
    first_message = "Validation error occurred."

    for error in exc.errors():
        loc = error.get("loc", ())
        # Extract field name, ignoring "body" prefix
        field = str(loc[-1]) if loc else "unknown"
        problem = error.get("msg", "invalid value")
        # Strip ValueError prefix if present
        if problem.startswith("Value error, "):
            problem = problem[len("Value error, "):]
        formatted_details.append({"field": field, "problem": problem})
        if field == "message":
            first_message = problem if "character" in problem else "message must contain between 1 and 2000 characters."

    payload = make_error_envelope(
        code="VALIDATION_ERROR",
        message=first_message,
        retryable=False,
        request_id=request_id,
        details=formatted_details,
    )
    return JSONResponse(
        status_code=422,
        content=payload,
        headers={"X-Request-ID": request_id},
    )


async def invalid_thread_id_handler(request: Request, exc: InvalidThreadIdException) -> JSONResponse:
    """Handle malformed thread_id queries or bodies (HTTP 400)."""
    request_id = _get_request_id(request)
    payload = make_error_envelope(
        code="INVALID_THREAD_ID",
        message=exc.message,
        retryable=False,
        request_id=request_id,
        details=None,
    )
    return JSONResponse(
        status_code=400,
        content=payload,
        headers={"X-Request-ID": request_id},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette/FastAPI HTTPExceptions using the error envelope."""
    request_id = _get_request_id(request)
    code = "HTTP_ERROR"
    retryable = False

    if exc.status_code == 400:
        code = "BAD_REQUEST"
    elif exc.status_code == 404:
        code = "THREAD_NOT_FOUND"
    elif exc.status_code == 503:
        code = "SERVICE_UNAVAILABLE"
        retryable = True

    payload = make_error_envelope(
        code=code,
        message=str(exc.detail),
        retryable=retryable,
        request_id=request_id,
        details=None,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload,
        headers={"X-Request-ID": request_id},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled exceptions and return safe internal error envelope (HTTP 500)."""
    request_id = _get_request_id(request)
    payload = make_error_envelope(
        code="INTERNAL_ERROR",
        message="Something went wrong on our side.",
        retryable=True,
        request_id=request_id,
        details=None,
    )
    return JSONResponse(
        status_code=500,
        content=payload,
        headers={"X-Request-ID": request_id},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all standardized exception handlers on the FastAPI application."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(InvalidThreadIdException, invalid_thread_id_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
