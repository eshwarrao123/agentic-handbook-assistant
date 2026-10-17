"""Node: compose_response (TECHNICAL_DESIGN §6, Node 9).

Terminal node:
- Joins accumulated reply_parts with double newlines.
- Constructs an AIMessage and appends it to state["messages"] via add_messages reducer.
- Appends 'compose_response' to nodes_visited.
- Invariant: Never touches or modifies structured booking state.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from langchain_core.messages import AIMessage
from app.graph.state import AgentState


def compose_response(state: AgentState) -> Dict[str, Any]:
    """Execute compose_response node."""
    reply_parts = state.get("reply_parts") or []
    visited = list(state.get("nodes_visited") or []) + ["compose_response"]

    content = "\n\n".join(reply_parts).strip()
    if not content:
        content = "I'm here to help with the employee handbook or scheduling a performance review."

    citations = state.get("citations") or []
    created_at = datetime.now(timezone.utc).isoformat()

    ai_message = AIMessage(
        id=str(uuid.uuid4()),
        content=content,
        additional_kwargs={
            "citations": citations,
            "created_at": created_at,
        },
    )

    return {
        "messages": [ai_message],
        "nodes_visited": visited,
    }
