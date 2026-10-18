"""Node: faq_rag (TECHNICAL_DESIGN §6, Node 4).

Answers handbook queries using persistent ChromaDB vector retrieval and grounded generation.
Security and isolation invariants:
1. NEVER writes to or mutates the structured 'booking' state.
2. Graceful failure isolation: errors set degraded=True without crashing the graph.
3. Citations are built solely from verified chunk metadata, never from LLM output.
"""

import logging
from typing import Any, Dict, Optional
from langchain_core.runnables import RunnableConfig

from app.graph.state import AgentState
from app.llm.gateway import get_llm_gateway
from app.rag.grounding import UNANSWERABLE_HANDBOOK_REPLY, validate_and_build_grounded_response
from app.rag.retriever import get_retriever

logger = logging.getLogger("graph.nodes.faq_rag")


async def faq_rag(state: AgentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Execute faq_rag node with vector retrieval and grounded answer generation."""
    reply_parts = list(state.get("reply_parts") or [])
    visited = list(state.get("nodes_visited") or []) + ["faq_rag"]

    faq_question = (state.get("faq_question") or state.get("user_text") or "").strip()
    if not faq_question:
        reply_parts.append(UNANSWERABLE_HANDBOOK_REPLY)
        return {
            "reply_parts": reply_parts,
            "citations": [],
            "nodes_visited": visited,
        }

    # Dependency injection support via config or fallback to singletons
    configurable = config.get("configurable", {}) if config else {}
    retriever = configurable.get("retriever") or get_retriever()
    llm_gateway = configurable.get("llm_gateway") or get_llm_gateway()

    # 1. Semantic retrieval with distance gating
    try:
        passages = await retriever.retrieve(faq_question)
    except Exception as exc:
        logger.error(f"Retriever failure in faq_rag: {exc}", exc_info=True)
        reply_parts.append(
            "I'm sorry, I encountered a temporary issue accessing the employee handbook. "
            "Please try asking your question again in a moment."
        )
        return {
            "reply_parts": reply_parts,
            "citations": [],
            "nodes_visited": visited,
            "degraded": True,
            "error_code": "RAG_RETRIEVAL_ERROR",
        }

    # 2. Gate check: If no passages passed distance threshold, return unanswerable notice
    if not passages:
        reply_parts.append(UNANSWERABLE_HANDBOOK_REPLY)
        return {
            "reply_parts": reply_parts,
            "citations": [],
            "nodes_visited": visited,
        }

    # 3. Grounded generation and citation construction
    try:
        grounded_answer = await llm_gateway.answer_from_passages(faq_question, passages)
        content, citations = validate_and_build_grounded_response(grounded_answer, passages)
        reply_parts.append(content)
        return {
            "reply_parts": reply_parts,
            "citations": citations,
            "nodes_visited": visited,
        }
    except Exception as exc:
        logger.error(f"Generation failure in faq_rag: {exc}", exc_info=True)
        reply_parts.append(
            "I'm sorry, I encountered an issue formulating an answer from the handbook. "
            "Please try again."
        )
        return {
            "reply_parts": reply_parts,
            "citations": [],
            "nodes_visited": visited,
            "degraded": True,
            "error_code": "RAG_GENERATION_ERROR",
        }
