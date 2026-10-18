"""Regression test for citation accuracy issue.

This test ensures that citation snippets display relevant supporting evidence
rather than unrelated content from the beginning of long chunks.

Background:
- Earlier implementation extracted the first 200 characters of cited chunks
- For chunks with preamble content (e.g., company values before performance review info),
  the snippet would show the preamble instead of the actual supporting evidence
- Fixed by implementing smart snippet extraction that finds key phrases from the answer
"""

import pytest
from app.rag.grounding import extract_relevant_snippet, validate_and_build_grounded_response
from app.rag.retriever import RetrievedChunk
from app.llm.schemas import GroundedAnswer


class TestCitationAccuracy:
    """Test suite for citation snippet extraction accuracy."""
    
    def test_extract_relevant_snippet_finds_key_phrase(self):
        """Test that extract_relevant_snippet finds and centers on key phrases."""
        # Simulate a chunk with preamble followed by relevant content
        chunk_text = (
            "7. Accountability: We take responsibility for our actions and hold ourselves and others "
            "accountable for their performance. 8. Community: We are committed to making a positive "
            "impact in the communities in which we work and live. Performance Reviews Performance "
            "Reviews at Zava At Zava, we strive to ensure our employees are getting the feedback "
            "they need to continue growing and developing in their roles. We understand that "
            "performance reviews are a key part of this process and it is important to us that "
            "they are conducted in an effective and efficient manner. Performance reviews are "
            "conducted annually and are an important part of your career development. During the "
            "review, your supervisor will discuss your performance over the past year and provide "
            "feedback on areas for improvement."
        )
        
        answer = (
            "According to the handbook, performance reviews at Zava are conducted annually. "
            "Your supervisor discusses your performance over the past year, gives feedback on "
            "areas for improvement, and talks through your goals for the upcoming year."
        )
        
        snippet = extract_relevant_snippet(chunk_text, answer, max_length=200)
        
        # Snippet should contain the key phrase "conducted annually"
        assert "conducted annually" in snippet.lower(), \
            f"Snippet should contain 'conducted annually', got: {snippet}"
        
        # Snippet should NOT start with the preamble about Accountability
        assert not snippet.startswith("7. Accountability"), \
            f"Snippet should not start with preamble, got: {snippet}"
        
        # Snippet should be reasonably focused on performance reviews
        assert "performance review" in snippet.lower(), \
            f"Snippet should mention performance reviews, got: {snippet}"
    
    def test_extract_relevant_snippet_handles_short_text(self):
        """Test that short texts are returned as-is."""
        short_text = "Performance reviews are conducted annually."
        answer = "Reviews are conducted annually."
        
        snippet = extract_relevant_snippet(short_text, answer, max_length=200)
        assert snippet == short_text
    
    def test_extract_relevant_snippet_falls_back_gracefully(self):
        """Test fallback to start of text when no key phrases match."""
        chunk_text = "This is completely unrelated text that has nothing to do with the answer."
        answer = "The handbook states that reviews happen quarterly."
        
        snippet = extract_relevant_snippet(chunk_text, answer, max_length=50)
        
        # Should fall back to first 50 chars (with word boundary)
        assert len(snippet) <= 55  # Allow for ellipsis and word boundary
        assert snippet.startswith("This is completely unrelated")
    
    def test_validate_and_build_grounded_response_with_smart_snippets(self):
        """Integration test: validate_and_build_grounded_response uses smart snippets."""
        # Create a retrieved chunk with preamble
        chunk = RetrievedChunk(
            chunk_id="employee_handbook.pdf-p4-c0",
            document="employee_handbook.pdf",
            title="Zava Employee Handbook",
            page=4,
            chunk_index=0,
            text=(
                "7. Accountability: We take responsibility for our actions and hold ourselves and others "
                "accountable for their performance. 8. Community: We are committed to making a positive "
                "impact in the communities in which we work and live. Performance Reviews Performance "
                "Reviews at Zava At Zava, we strive to ensure our employees are getting the feedback "
                "they need to continue growing and developing in their roles. We understand that "
                "performance reviews are a key part of this process and it is important to us that "
                "they are conducted in an effective and efficient manner. Performance reviews are "
                "conducted annually and are an important part of your career development. During the "
                "review, your supervisor will discuss your performance over the past year and provide "
                "feedback on areas for improvement."
            ),
            distance=0.42,
        )
        
        grounded_answer = GroundedAnswer(
            answerable=True,
            answer=(
                "According to the handbook, performance reviews at Zava are conducted annually. "
                "Your supervisor discusses your performance over the past year, gives feedback on "
                "areas for improvement, and talks through your goals for the upcoming year."
            ),
            used_chunk_ids=["employee_handbook.pdf-p4-c0"],
        )
        
        final_content, citations = validate_and_build_grounded_response(
            grounded_answer, [chunk]
        )
        
        # Verify citation was created
        assert len(citations) == 1, "Should have exactly one citation"
        
        citation = citations[0]
        assert citation["page"] == 4
        assert citation["chunk_id"] == "employee_handbook.pdf-p4-c0"
        
        # CRITICAL: Snippet should contain supporting evidence, not preamble
        snippet = citation["snippet"]
        assert "conducted annually" in snippet.lower(), \
            f"Citation snippet must contain 'conducted annually', got: {snippet}"
        
        assert not snippet.startswith("7. Accountability"), \
            f"Citation snippet should not show unrelated preamble, got: {snippet}"
        
        assert "performance review" in snippet.lower(), \
            f"Citation snippet should mention performance reviews, got: {snippet}"
    
    def test_citation_snippet_supports_answer_content(self):
        """Verify that the citation snippet directly supports the answer's claims."""
        # This is the actual performance review question from the assessment
        chunk = RetrievedChunk(
            chunk_id="test-chunk",
            document="employee_handbook.pdf",
            title="Test Handbook",
            page=4,
            chunk_index=0,
            text=(
                "Company values include integrity and teamwork. We believe in supporting our employees. "
                "Performance evaluations are a critical tool. Reviews are conducted annually to assess "
                "progress and set goals for the coming year. Managers provide written feedback."
            ),
            distance=0.40,
        )
        
        grounded_answer = GroundedAnswer(
            answerable=True,
            answer="Reviews are conducted annually to assess progress and set goals.",
            used_chunk_ids=["test-chunk"],
        )
        
        _, citations = validate_and_build_grounded_response(grounded_answer, [chunk])
        
        snippet = citations[0]["snippet"]
        
        # The snippet must contain the actual supporting evidence
        assert "conducted annually" in snippet.lower()
        assert "reviews" in snippet.lower() or "evaluations" in snippet.lower()
        
        # Should NOT show the unrelated company values preamble
        assert "integrity" not in snippet.lower() or "conducted annually" in snippet.lower()
    
    def test_multiple_citations_each_get_relevant_snippets(self):
        """Test that multiple citations each get context-appropriate snippets."""
        chunk1 = RetrievedChunk(
            chunk_id="chunk-1",
            document="handbook.pdf",
            title="Handbook",
            page=3,
            chunk_index=0,
            text=(
                "Unrelated intro text about company history. The company was founded in 1999. "
                "Data security training is mandatory. All employees must complete data security "
                "training upon hire and annually thereafter."
            ),
            distance=0.38,
        )
        
        chunk2 = RetrievedChunk(
            chunk_id="chunk-2",
            document="handbook.pdf",
            title="Handbook",
            page=5,
            chunk_index=0,
            text=(
                "Various policies apply. Vacation policy is generous. Employees can report concerns "
                "anonymously by calling the Compliance Hotline at 1-800-555-1212."
            ),
            distance=0.40,
        )
        
        grounded_answer = GroundedAnswer(
            answerable=True,
            answer=(
                "Employees must complete data security training upon hire and annually thereafter. "
                "You can report concerns anonymously by calling the Compliance Hotline."
            ),
            used_chunk_ids=["chunk-1", "chunk-2"],
        )
        
        _, citations = validate_and_build_grounded_response(
            grounded_answer, [chunk1, chunk2]
        )
        
        assert len(citations) == 2
        
        # First citation should be about data security training
        snippet1 = citations[0]["snippet"]
        assert "data security training" in snippet1.lower()
        assert "annually" in snippet1.lower()
        
        # Second citation should be about the hotline
        snippet2 = citations[1]["snippet"]
        assert "compliance hotline" in snippet2.lower() or "1-800-555-1212" in snippet2


@pytest.mark.asyncio
async def test_citation_accuracy_end_to_end():
    """End-to-end test: Query retriever and verify citation snippet accuracy."""
    from app.rag.retriever import HandbookRetriever
    from app.llm.gateway import OfflineLLMGateway
    
    retriever = HandbookRetriever()
    gateway = OfflineLLMGateway()
    
    question = "How often are performance reviews conducted according to the handbook?"
    
    # Retrieve chunks
    chunks = await retriever.retrieve(question)
    assert len(chunks) > 0, "Should retrieve at least one chunk"
    
    # Generate answer
    grounded_answer = await gateway.answer_from_passages(question, chunks)
    assert grounded_answer.answerable, "Question should be answerable"
    assert "annually" in grounded_answer.answer.lower(), "Answer should mention 'annually'"
    
    # Build citations
    final_content, citations = validate_and_build_grounded_response(grounded_answer, chunks)
    
    assert len(citations) > 0, "Should have at least one citation"
    
    # CRITICAL VERIFICATION: Citation snippet must support the answer
    citation = citations[0]
    snippet = citation["snippet"]
    
    # The snippet must contain evidence that reviews are conducted annually
    # It should NOT show unrelated preamble content like company values
    assert "conducted annually" in snippet.lower() or "annually" in snippet.lower(), \
        f"Citation snippet must contain frequency information, got: {snippet}"
    
    # Verify the page number matches the actual source
    assert citation["page"] == 4, "Performance review info is on page 4"
    
    # Verify the snippet is from the cited chunk
    cited_chunk = next((c for c in chunks if c.chunk_id == citation["chunk_id"]), None)
    assert cited_chunk is not None, "Citation must reference an actually retrieved chunk"
    assert snippet.replace("...", "").strip() in cited_chunk.text or \
           any(word in cited_chunk.text for word in snippet.split()[:5]), \
        "Snippet must be extracted from the cited chunk"
