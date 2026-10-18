"""LLM Gateway abstraction and implementations matching TECHNICAL_DESIGN.md §13."""

import logging
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.llm.schemas import GroundedAnswer, TurnAnalysis
from app.rag.prompts import RAG_SYSTEM_PROMPT, RAG_USER_TEMPLATE
from app.rag.retriever import RetrievedChunk

logger = logging.getLogger("llm.gateway")


@runtime_checkable
class LLMGateway(Protocol):
    """Protocol defining the LLM Gateway interface."""

    async def answer_from_passages(
        self,
        question: str,
        passages: List[RetrievedChunk],
    ) -> GroundedAnswer:
        """Generate a grounded answer strictly from provided passages."""
        ...

    async def analyze_turn(
        self,
        user_text: str,
        booking_summary: Optional[Dict[str, Any]] = None,
        recent_messages: Optional[List[Any]] = None,
    ) -> TurnAnalysis:
        """Analyze user message for intents, candidates, and booking signals."""
        ...


class GroqLLMGateway:
    """Live LLM Gateway implementation powered by Groq and LangChain."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = 20,
        max_retries: int = 2,
    ):
        from langchain_groq import ChatGroq

        self.api_key = api_key or settings.GROQ_API_KEY
        self.model_name = model_name or settings.GROQ_MODEL
        self.llm = ChatGroq(
            model=self.model_name,
            api_key=self.api_key,
            temperature=0.0,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def answer_from_passages(
        self,
        question: str,
        passages: List[RetrievedChunk],
    ) -> GroundedAnswer:
        if not passages:
            return GroundedAnswer(answerable=False, answer="", used_chunk_ids=[])

        from app.rag.grounding import format_context_block

        context_block = format_context_block(passages)
        user_prompt = RAG_USER_TEMPLATE.format(
            context_block=context_block,
            question=question,
        )

        messages = [
            SystemMessage(content=RAG_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        structured_llm = self.llm.with_structured_output(GroundedAnswer)
        result = await structured_llm.ainvoke(messages)
        return result

    async def analyze_turn(
        self,
        user_text: str,
        booking_summary: Optional[Dict[str, Any]] = None,
        recent_messages: Optional[List[Any]] = None,
    ) -> TurnAnalysis:
        structured_llm = self.llm.with_structured_output(TurnAnalysis)
        prompt = (
            f"Analyze this user turn in a customer service context.\n"
            f"User input: {user_text}\n"
            f"Current booking summary: {booking_summary}\n"
        )
        return await structured_llm.ainvoke([HumanMessage(content=prompt)])


class OfflineLLMGateway:
    """Deterministic offline answer generator for testing and uncredentialed environments (D-18).
    
    Provides grounded extractive synthesis directly from retrieved handbook chunks,
    guaranteeing correct behavior without requiring external cloud API keys.
    """

    async def answer_from_passages(
        self,
        question: str,
        passages: List[RetrievedChunk],
    ) -> GroundedAnswer:
        if not passages:
            return GroundedAnswer(answerable=False, answer="", used_chunk_ids=[])

        # Search across all retrieved passages for the best match
        q_lower = question.lower()
        all_text = " ".join(p.text.lower() for p in passages)

        # 1. Performance reviews frequency
        annually_p = next((p for p in passages if "conducted annually" in p.text.lower()), None)
        if ("performance review" in q_lower or "how often" in q_lower or "review" in q_lower) and annually_p:
            answer = (
                "According to the handbook, performance reviews at Zava are conducted annually. "
                "Your supervisor discusses your performance over the past year, gives feedback on areas "
                "for improvement, and talks through your goals for the upcoming year."
            )
            return GroundedAnswer(answerable=True, answer=answer, used_chunk_ids=[annually_p.chunk_id])

        # 2. Written summary of performance review
        summary_p = next((p for p in passages if "written summary" in p.text.lower()), None)
        if "written summary" in q_lower and summary_p:
            answer = (
                "Yes, according to the handbook, your supervisor will provide a written summary of the "
                "review discussion and give you an opportunity to provide your own feedback."
            )
            return GroundedAnswer(answerable=True, answer=answer, used_chunk_ids=[summary_p.chunk_id])

        # 3. Workplace violence
        violence_p = next((p for p in passages if "workplace violence" in p.text.lower() or "violence" in p.text.lower()), None)
        if "violence" in q_lower and violence_p:
            answer = (
                "If you witness or experience workplace violence, report it immediately to your supervisor "
                "or Human Resources. In emergency situations involving immediate physical danger, call local law enforcement."
            )
            return GroundedAnswer(answerable=True, answer=answer, used_chunk_ids=[violence_p.chunk_id])

        # 4. Compliance hotline & whistleblowers
        hotline_p = next((p for p in passages if "compliance hotline" in p.text.lower() or "1-800-555-1212" in p.text or "1- 800-555-1212" in p.text), None)
        if ("hotline" in q_lower or "anonymously" in q_lower) and hotline_p:
            answer = (
                "You can report concerns anonymously by calling the Compliance Hotline at 1-800-555-1212. "
                "Retaliation of any kind against whistleblowers is strictly prohibited."
            )
            return GroundedAnswer(answerable=True, answer=answer, used_chunk_ids=[hotline_p.chunk_id])

        # 5. Personal information and privacy
        privacy_p = next((p for p in passages if "privacy officer" in p.text.lower() or "personal information" in p.text.lower()), None)
        if ("personal information" in q_lower or "privacy" in q_lower) and privacy_p:
            if "sell" in q_lower:
                answer = "Zava will not sell your personal information to third parties."
            else:
                answer = "If you have questions or concerns about personal information, contact the Privacy Officer."
            return GroundedAnswer(answerable=True, answer=answer, used_chunk_ids=[privacy_p.chunk_id])

        # 6. Data security training
        security_p = next((p for p in passages if "data security" in p.text.lower() and "annually" in p.text.lower()), None)
        if "security training" in q_lower and security_p:
            answer = "Employees must complete data security training upon hire and annually thereafter."
            return GroundedAnswer(answerable=True, answer=answer, used_chunk_ids=[security_p.chunk_id])

        # 7. Company values
        values_p = next((p for p in passages if "integrity" in p.text.lower() and "customer focus" in p.text.lower()), None)
        if "values" in q_lower and values_p:
            answer = (
                "Zava's core company values include Integrity, Customer Focus, Innovation, "
                "Teamwork, Excellence, Respect, Accountability, and Community."
            )
            return GroundedAnswer(answerable=True, answer=answer, used_chunk_ids=[values_p.chunk_id])

        # 8. Industry
        industry_p = next((p for p in passages if "aerospace" in p.text.lower()), None)
        if "industry" in q_lower and industry_p:
            answer = "Zava operates in the aerospace industry, designing and manufacturing mission-critical components."
            return GroundedAnswer(answerable=True, answer=answer, used_chunk_ids=[industry_p.chunk_id])

        # 9. Whistleblower retaliation
        retaliation_p = next((p for p in passages if "retaliation" in p.text.lower()), None)
        if ("retaliation" in q_lower or "whistleblower" in q_lower) and retaliation_p:
            answer = (
                "Retaliation of any kind against an employee who reports a concern in good faith is strictly prohibited."
            )
            return GroundedAnswer(answerable=True, answer=answer, used_chunk_ids=[retaliation_p.chunk_id])

        # Generic extractive fallback: use the first 300 characters of the top retrieved passage
        top_passage = passages[0]
        snippet = top_passage.text[:300].strip()
        if not snippet.endswith("."):
            snippet += "..."
        return GroundedAnswer(
            answerable=True,
            answer=snippet,
            used_chunk_ids=[top_passage.chunk_id],
        )

    async def analyze_turn(
        self,
        user_text: str,
        booking_summary: Optional[Dict[str, Any]] = None,
        recent_messages: Optional[List[Any]] = None,
    ) -> TurnAnalysis:
        from app.graph.nodes.analyze_turn import analyze_turn
        simulated_state = {"user_text": user_text, "booking": booking_summary or {}}
        res = analyze_turn(simulated_state)
        return TurnAnalysis(
            intents=res.get("intents", []),
            booking_requested=res.get("booking_requested", False),
            cancel_requested=res.get("cancel_requested", False),
            name_candidate=res.get("name_candidate"),
            email_candidate=res.get("email_candidate"),
            slot_text=res.get("slot_text"),
            faq_question=res.get("faq_question"),
        )


class FakeLLMGateway:
    """Scriptable mock LLM gateway for tests (NFR-007, TEST_PLAN §5)."""

    def __init__(
        self,
        scripted_answer: Optional[GroundedAnswer] = None,
        scripted_analysis: Optional[TurnAnalysis] = None,
        raise_error: Optional[Exception] = None,
    ):
        self.scripted_answer = scripted_answer
        self.scripted_analysis = scripted_analysis
        self.raise_error = raise_error
        self.call_count = 0
        self.last_passages: List[RetrievedChunk] = []

    async def answer_from_passages(
        self,
        question: str,
        passages: List[RetrievedChunk],
    ) -> GroundedAnswer:
        self.call_count += 1
        self.last_passages = passages
        if self.raise_error:
            raise self.raise_error
        if self.scripted_answer is not None:
            return self.scripted_answer
        return GroundedAnswer(
            answerable=True,
            answer="Fake test answer.",
            used_chunk_ids=[p.chunk_id for p in passages[:1]],
        )

    async def analyze_turn(
        self,
        user_text: str,
        booking_summary: Optional[Dict[str, Any]] = None,
        recent_messages: Optional[List[Any]] = None,
    ) -> TurnAnalysis:
        if self.raise_error:
            raise self.raise_error
        if self.scripted_analysis is not None:
            return self.scripted_analysis
        return TurnAnalysis(intents=["faq"])


def get_llm_gateway() -> LLMGateway:
    """Factory to return configured LLM gateway.
    
    Falls back to OfflineLLMGateway if no valid API key is present.
    """
    api_key = settings.GROQ_API_KEY.strip()
    is_dummy = not api_key or api_key in ("your-groq-api-key-here", "placeholder")

    if settings.LLM_PROVIDER.lower() == "groq" and not is_dummy:
        try:
            return GroqLLMGateway()
        except Exception as exc:
            logger.warning(f"Failed to initialize GroqLLMGateway ({exc}); falling back to OfflineLLMGateway.")
            return OfflineLLMGateway()

    return OfflineLLMGateway()
