"""Page-aware PDF text extraction and chunking matching TECHNICAL_DESIGN.md §11.1."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Union
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


def extract_pages_from_pdf(
    pdf_path: Union[str, Path],
    min_chars_per_page: int = 30,
) -> List[Dict[str, Any]]:
    """Extract text from a PDF page by page with whitespace normalization.
    
    Pages with fewer than min_chars_per_page (e.g. title pages or blanks)
    are skipped per TECHNICAL_DESIGN.md §11.1.
    """
    path_obj = Path(pdf_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF file not found at: {path_obj}")

    reader = PdfReader(str(path_obj))
    extracted_pages: List[Dict[str, Any]] = []

    for page_num, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        # Normalize whitespace into single spaces
        normalized_text = re.sub(r"\s+", " ", raw_text).strip()

        if len(normalized_text) < min_chars_per_page:
            continue

        extracted_pages.append({
            "page": page_num,
            "text": normalized_text,
        })

    return extracted_pages


def chunk_pages(
    pages: List[Dict[str, Any]],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    source_filename: str = "employee_handbook.pdf",
    doc_title: str = "Zava Employee Handbook",
) -> List[Dict[str, Any]]:
    """Split extracted pages into overlapping chunks bounded strictly by page.
    
    Invariant: Chunks NEVER cross pages.
    Each chunk retains source, title, page, and chunk_index metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
        length_function=len,
    )

    all_chunks: List[Dict[str, Any]] = []

    for p in pages:
        page_num = p["page"]
        page_text = p["text"]
        page_chunks = splitter.split_text(page_text)

        for chunk_idx, chunk_text in enumerate(page_chunks):
            chunk_id = f"{source_filename}-p{page_num}-c{chunk_idx}"
            all_chunks.append({
                "chunk_id": chunk_id,
                "source": source_filename,
                "title": doc_title,
                "page": page_num,
                "chunk_index": chunk_idx,
                "text": chunk_text,
            })

    return all_chunks
