"""RAG (Retrieval-Augmented Generation) package for Agentic Handbook Assistant."""

from app.rag.chunking import chunk_pages, extract_pages_from_pdf
from app.rag.ingest import ingest_handbook

__all__ = ["chunk_pages", "extract_pages_from_pdf", "ingest_handbook"]
