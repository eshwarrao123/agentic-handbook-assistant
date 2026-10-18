"""API router for conversational chat endpoint matching docs/API_CONTRACT.md §6."""

from fastapi import APIRouter, Request, status
from app.api.errors import InvalidThreadIdException, validate_thread_id
from app.api.schemas import ChatRequest, ChatResponse
from app.services.chat_service import get_chat_service

router = APIRouter(tags=["Chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Process conversational turn through LangGraph assistant",
)
async def post_chat(
    chat_request: ChatRequest,
    request: Request,
) -> ChatResponse:
    """Process a user chat message and return the assistant response.
    
    Validates thread_id (HTTP 400 if malformed).
    Delegates graph execution to the service layer.
    """
    if chat_request.thread_id is not None:
        if not validate_thread_id(chat_request.thread_id):
            raise InvalidThreadIdException("thread_id must be a valid UUID.")

    svc = get_chat_service(request)
    return await svc.handle_chat(
        message_text=chat_request.message,
        thread_id=chat_request.thread_id,
    )
