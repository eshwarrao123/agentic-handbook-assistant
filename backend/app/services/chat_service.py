"""Service layer for chat orchestration and graph invocation matching TECHNICAL_DESIGN §2 & §5.4."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from app.api.schemas import (
    AgentInfo,
    BookingSnapshot,
    ChatReply,
    ChatResponse,
    Citation,
    Confirmation,
    Slot,
)
from app.graph.builder import build_graph
from app.graph.state import default_booking_state


class ChatService:
    """Orchestrates chat turn execution through the compiled LangGraph StateGraph."""

    def __init__(self, checkpointer: Optional[BaseCheckpointSaver] = None):
        # Use MemorySaver by default for Phase 2/3 deterministic in-memory persistence
        self.checkpointer = checkpointer if checkpointer is not None else MemorySaver()
        self.graph = build_graph(checkpointer=self.checkpointer)
        self._thread_locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _get_lock_for_thread(self, thread_id: str) -> asyncio.Lock:
        """Get or create an asyncio.Lock for serializing turns on a specific thread (API_CONTRACT §6.2)."""
        async with self._global_lock:
            if thread_id not in self._thread_locks:
                self._thread_locks[thread_id] = asyncio.Lock()
            return self._thread_locks[thread_id]

    async def handle_chat(self, message_text: str, thread_id: Optional[str] = None) -> ChatResponse:
        """Execute one conversational turn on the graph.
        
        Strict adherence to TECHNICAL_DESIGN §5.4:
        The graph input contains ONLY {"messages": [HumanMessage(...)]}.
        Never injects booking fields or fabricated message history.
        """
        is_new_thread = False

        if not thread_id:
            thread_id = str(uuid.uuid4())
            is_new_thread = True

        config = {"configurable": {"thread_id": thread_id}}
        lock = await self._get_lock_for_thread(thread_id)

        async with lock:
            if not is_new_thread:
                # Inspect existing checkpoint state
                current_state = await self.graph.aget_state(config)
                # If no values have been recorded yet, this is a fresh thread (API_CONTRACT §6.2)
                is_new_thread = not bool(current_state and current_state.values)

            # Construct graph input with user message only (TECHNICAL_DESIGN §5.4)
            human_msg = HumanMessage(
                id=str(uuid.uuid4()),
                content=message_text,
            )
            graph_input = {"messages": [human_msg]}

            # Execute graph turn
            final_state = await self.graph.ainvoke(graph_input, config=config)

            # Map final state to ChatResponse DTO
            messages = final_state.get("messages") or []
            last_msg = messages[-1] if messages else None
            reply_content = getattr(last_msg, "content", "") if last_msg else ""
            reply_id = getattr(last_msg, "id", None) or str(uuid.uuid4())
            
            citations_raw = final_state.get("citations") or []
            citations = [
                Citation(
                    document=c.get("document", "employee_handbook.pdf"),
                    title=c.get("title", "Zava Employee Handbook"),
                    page=c.get("page", 1),
                    snippet=c.get("snippet", ""),
                    chunk_id=c.get("chunk_id", ""),
                )
                for c in citations_raw
            ]

            created_at = datetime.now(timezone.utc).isoformat()
            reply = ChatReply(
                message_id=reply_id,
                role="assistant",
                content=reply_content,
                citations=citations,
                created_at=created_at,
            )

            # Map structured booking state
            booking_raw = final_state.get("booking") or default_booking_state()
            offered_slots = [
                Slot(
                    slot_id=s["slot_id"],
                    start=s["start"],
                    label=s["label"],
                )
                for s in booking_raw.get("offered_slots") or []
            ]

            confirmation = None
            if booking_raw.get("status") == "confirmed" and booking_raw.get("booking_reference"):
                confirmed_slot_raw = booking_raw.get("confirmed_slot") or {}
                confirmation = Confirmation(
                    reference=booking_raw["booking_reference"],
                    slot=Slot(
                        slot_id=confirmed_slot_raw.get("slot_id", "slot-default"),
                        start=confirmed_slot_raw.get("start", datetime.now(timezone.utc).isoformat()),
                        label=confirmed_slot_raw.get("label", "Scheduled Slot"),
                    ),
                    full_name=booking_raw.get("full_name") or "Attendee",
                    email=booking_raw.get("email") or "attendee@example.com",
                    service_type=booking_raw.get("service_type") or "performance_review",
                    simulated=True,
                )

            booking_snapshot = BookingSnapshot(
                status=booking_raw.get("status", "none"),
                service_type=booking_raw.get("service_type"),
                full_name=booking_raw.get("full_name"),
                email=booking_raw.get("email"),
                offered_slots=offered_slots,
                confirmation=confirmation,
            )

            # Map agent execution info
            agent_info = AgentInfo(
                status="degraded" if final_state.get("degraded") else "ok",
                error_code=final_state.get("error_code"),
                intents=final_state.get("intents") or [],
                route=final_state.get("nodes_visited") or [],
            )

            return ChatResponse(
                thread_id=thread_id,
                is_new_thread=is_new_thread,
                reply=reply,
                booking=booking_snapshot,
                agent=agent_info,
            )


# Default singleton service instance
chat_service = ChatService()
