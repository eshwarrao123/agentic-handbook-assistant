"""Grounding context formatting and citation validation matching TECHNICAL_DESIGN.md §11.4."""

import re
from typing import Any, Dict, List, Set, Tuple
from app.llm.schemas import GroundedAnswer
from app.rag.retriever import RetrievedChunk

UNANSWERABLE_HANDBOOK_REPLY = (
    "I couldn't find that in the Employee Handbook. I can help with topics it covers — "
    "such as performance reviews, workplace safety, privacy, whistleblower policy, data "
    "security and job roles — or book a performance review session."
)


def format_context_block(passages: List[RetrievedChunk]) -> str:
    """Format retrieved passages into a clearly delimited context block."""
    if not passages:
        return "No relevant handbook passages found."

    blocks = []
    for idx, passage in enumerate(passages, start=1):
        header = f"[C{idx}] (Document: {passage.document}, Page {passage.page}, ID: {passage.chunk_id})"
        blocks.append(f"{header}\n{passage.text}")

    return "\n\n---\n\n".join(blocks)


def extract_relevant_snippet(chunk_text: str, answer: str, max_length: int = 200) -> str:
    """Extract a relevant snippet from chunk text that supports the answer.
    
    Strategy:
    1. Extract key phrases from the answer (2-4 word sequences)
    2. Search for these phrases in the chunk text
    3. If found, extract context around the phrase
    4. If not found, fall back to first max_length characters
    
    This ensures the displayed snippet actually supports the answer rather than
    showing unrelated content from the beginning of a long chunk.
    """
    if len(chunk_text) <= max_length:
        return chunk_text
    
    # Extract potential key phrases from the answer (bigrams, trigrams, 4-grams)
    # Focus on content words, skip common stopwords
    answer_lower = answer.lower()
    chunk_lower = chunk_text.lower()
    
    # Try to find important phrases from the answer in the chunk
    # Common patterns to look for:
    key_patterns = [
        r'\b(conducted|performed|held)\s+(\w+)\b',  # "conducted annually"
        r'\b(annually|monthly|quarterly|weekly|daily)\b',  # frequency words
        r'\b(\w+)\s+(review|meeting|session|training)\b',  # "performance review"
        r'\b(must|should|will|required to)\s+(\w+)\b',  # obligation phrases
    ]
    
    best_match_pos = None
    best_match_phrase = None
    
    # Try regex patterns first
    for pattern in key_patterns:
        answer_matches = re.finditer(pattern, answer_lower)
        for match in answer_matches:
            phrase = match.group(0)
            if phrase in chunk_lower:
                pos = chunk_lower.find(phrase)
                if pos != -1:
                    best_match_pos = pos
                    best_match_phrase = phrase
                    break
        if best_match_pos is not None:
            break
    
    # If no pattern match, try significant word sequences from answer
    if best_match_pos is None:
        # Split answer into words and try 3-word sequences
        words = re.findall(r'\b\w+\b', answer_lower)
        for i in range(len(words) - 2):
            # Skip if all stopwords
            trigram = ' '.join(words[i:i+3])
            if trigram in chunk_lower:
                best_match_pos = chunk_lower.find(trigram)
                best_match_phrase = trigram
                break
    
    # If we found a match, extract context around it
    if best_match_pos is not None:
        # Calculate snippet window
        snippet_start = max(0, best_match_pos - 80)
        snippet_end = min(len(chunk_text), best_match_pos + len(best_match_phrase) + 120)
        
        snippet = chunk_text[snippet_start:snippet_end]
        
        # Clean up: try to start at a sentence or word boundary
        if snippet_start > 0:
            # Find first sentence start or fallback to word boundary
            sentence_start = re.search(r'[.!?]\s+[A-Z]', snippet)
            if sentence_start:
                snippet = snippet[sentence_start.start() + 2:]
            elif not snippet[0].isupper():
                # Start at word boundary
                word_start = re.search(r'\s+\w', snippet)
                if word_start:
                    snippet = snippet[word_start.start() + 1:]
        
        # Trim to max_length if needed
        if len(snippet) > max_length:
            snippet = snippet[:max_length].rsplit(' ', 1)[0] + '...'
        elif snippet_end < len(chunk_text):
            snippet = snippet + '...'
        
        return snippet.strip()
    
    # Fallback: use first max_length characters
    snippet = chunk_text[:max_length]
    if len(chunk_text) > max_length:
        # Try to break at word boundary
        last_space = snippet.rfind(' ')
        if last_space > max_length * 0.8:  # Only if we don't lose too much
            snippet = snippet[:last_space] + '...'
        else:
            snippet = snippet + '...'
    
    return snippet.strip()


def validate_and_build_grounded_response(
    grounded_answer: GroundedAnswer,
    retrieved_passages: List[RetrievedChunk],
) -> Tuple[str, List[Dict[str, Any]]]:
    """Validate model output against retrieved passages and build authoritative citations.
    
    Security and validation rules (TECHNICAL_DESIGN §11.4):
    1. Filter used_chunk_ids: only IDs actually retrieved are allowed; fabricated IDs are discarded.
    2. If answerable is False OR no valid chunk IDs remain, return grounded 'not found' text with empty citations.
    3. Citations are built solely from chunk metadata, never from LLM hallucinations.
    4. Append deterministic source footer to answer text: 'Source: employee_handbook.pdf, p. 4'.
    """
    if not grounded_answer.answerable or not grounded_answer.answer.strip():
        return UNANSWERABLE_HANDBOOK_REPLY, []

    retrieved_by_id: Dict[str, RetrievedChunk] = {p.chunk_id: p for p in retrieved_passages}

    # 1. Enforce used_chunk_ids ⊆ retrieved_passages
    valid_chunk_ids = [cid for cid in grounded_answer.used_chunk_ids if cid in retrieved_by_id]

    # If the model declared answerable=True but cited no valid retrieved chunks, reject
    if not valid_chunk_ids:
        # Fallback: if retrieved_passages has exactly 1 relevant passage and answer is grounded, or treat as unanswerable
        return UNANSWERABLE_HANDBOOK_REPLY, []

    # 2. Build citations from validated chunk metadata with relevant snippets
    citations: List[Dict[str, Any]] = []
    seen_chunk_ids: Set[str] = set()
    cited_pages: Set[int] = set()
    doc_name = "employee_handbook.pdf"

    for cid in valid_chunk_ids:
        if cid in seen_chunk_ids:
            continue
        seen_chunk_ids.add(cid)
        passage = retrieved_by_id[cid]
        doc_name = passage.document
        cited_pages.add(passage.page)
        
        # Extract snippet that actually supports the answer
        snippet = extract_relevant_snippet(passage.text, grounded_answer.answer, max_length=200)
        
        citations.append({
            "document": passage.document,
            "title": passage.title,
            "page": passage.page,
            "snippet": snippet,
            "chunk_id": passage.chunk_id,
        })

    # 3. Format deterministic source footer
    sorted_pages = sorted(cited_pages)
    if len(sorted_pages) == 1:
        page_str = f"p. {sorted_pages[0]}"
    else:
        page_str = f"pp. {', '.join(str(p) for p in sorted_pages)}"

    source_footer = f"Source: {doc_name}, {page_str}"
    cleaned_answer = grounded_answer.answer.strip()
    final_content = f"{cleaned_answer}\n\n{source_footer}"

    return final_content, citations
