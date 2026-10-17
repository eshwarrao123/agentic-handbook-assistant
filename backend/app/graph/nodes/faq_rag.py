"""Node: faq_rag (TECHNICAL_DESIGN §6, Node 4).

TEMPORARY DEVELOPMENT IMPLEMENTATION:
Provides canned handbook answer and mock citations for development and tests.
Full ChromaDB vector retrieval and grounded generation are integrated in Phase 4.

Crucial invariant:
This node NEVER writes to or mutates the structured 'booking' state.
"""

from typing import Any, Dict
from app.graph.state import AgentState


def faq_rag(state: AgentState) -> Dict[str, Any]:
    """Execute faq_rag node (development version)."""
    reply_parts = list(state.get("reply_parts") or [])
    visited = list(state.get("nodes_visited") or []) + ["faq_rag"]

    # Canned handbook answer matching PRD F-3
    faq_answer = (
        "According to the handbook, performance reviews at Zava are conducted annually. "
        "Your supervisor discusses your performance over the past year, gives feedback on areas "
        "for improvement, and talks through your goals for the upcoming year.\n"
        "Source: employee_handbook.pdf, p. 4"
    )
    reply_parts.append(faq_answer)

    mock_citation = {
        "document": "employee_handbook.pdf",
        "title": "Zava Employee Handbook",
        "page": 4,
        "snippet": "Performance reviews are conducted annually and are an important part of your career development.",
        "chunk_id": "employee_handbook.pdf-p4-c0",
    }

    return {
        "reply_parts": reply_parts,
        "citations": [mock_citation],
        "nodes_visited": visited,
    }
