"""Handbook ingestion CLI and pipeline matching TECHNICAL_DESIGN.md §11.1.

Downloads (if needed), parses page-by-page, chunks with page-boundary preservation,
computes file SHA-256, and indexes chunks into a persistent ChromaDB collection.
Ingestion is strictly idempotent: re-running with the same file hash and chunk count is a no-op.
"""

import sys
if sys.version_info.major == 3 and sys.version_info.minor != 13:
    sys.path = [p for p in sys.path if "Python313" not in p]

import argparse
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.rag.chunking import chunk_pages, extract_pages_from_pdf

logger = logging.getLogger("rag.ingest")


def compute_file_sha256(file_path: Union[str, Path]) -> str:
    """Compute the SHA-256 hash of a file for idempotence tracking."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def ingest_handbook(
    pdf_path: Optional[Union[str, Path]] = None,
    chroma_dir: Optional[Union[str, Path]] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """Execute handbook ingestion and persistent ChromaDB indexing (idempotent).
    
    Args:
        pdf_path: Path to employee handbook PDF. Defaults to DATA_DIR/raw/HANDBOOK_FILENAME.
        chroma_dir: Directory for persistent Chroma storage. Defaults to CHROMA_DIR.
        force: If True, re-indexes even if stored SHA-256 and chunk count match.
        
    Returns:
        Summary dict containing status, counts, and SHA-256 hash.
    """
    resolved_pdf = Path(pdf_path or (Path(settings.DATA_DIR) / "raw" / settings.HANDBOOK_FILENAME))
    resolved_chroma = Path(chroma_dir or settings.CHROMA_DIR)

    if not resolved_pdf.exists():
        raise FileNotFoundError(
            f"Employee handbook PDF not found at: {resolved_pdf}. "
            "Please ensure employee_handbook.pdf is placed in data/raw/."
        )

    resolved_chroma.mkdir(parents=True, exist_ok=True)
    file_sha256 = compute_file_sha256(resolved_pdf)

    # 1. Parse pages (whitespace-normalized, pages with < 30 chars skipped)
    extracted_pages = extract_pages_from_pdf(resolved_pdf, min_chars_per_page=30)

    # 2. Page-bounded chunking
    chunks = chunk_pages(
        extracted_pages,
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        source_filename=resolved_pdf.name,
        doc_title="Zava Employee Handbook",
    )

    # 3. Connect to persistent ChromaDB
    client = chromadb.PersistentClient(
        path=str(resolved_chroma),
        settings=ChromaSettings(anonymized_telemetry=False),
    )

    collection_name = "handbook"
    existing_collection = None

    try:
        existing_collection = client.get_collection(name=collection_name)
    except Exception:
        existing_collection = None

    # 4. Idempotency check: if hash and counts match and not force, no-op
    if existing_collection is not None and not force:
        stored_hash = existing_collection.metadata.get("file_sha256") if existing_collection.metadata else None
        current_count = existing_collection.count()
        if stored_hash == file_sha256 and current_count == len(chunks):
            return {
                "status": "skipped",
                "reason": "already_indexed",
                "pages_extracted": len(extracted_pages),
                "chunks_indexed": current_count,
                "file_sha256": file_sha256,
                "collection_count": current_count,
                "chroma_dir": str(resolved_chroma),
            }

    # 5. Recreate collection if hash changed, count mismatch, or force re-index
    if existing_collection is not None:
        client.delete_collection(name=collection_name)

    collection_metadata = {
        "hnsw:space": "cosine",
        "file_sha256": file_sha256,
        "doc_title": "Zava Employee Handbook",
        "source_file": resolved_pdf.name,
    }

    collection = client.create_collection(
        name=collection_name,
        metadata=collection_metadata,
    )

    ids = [c["chunk_id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {
            "chunk_id": c["chunk_id"],
            "source": c["source"],
            "title": c["title"],
            "page": c["page"],
            "chunk_index": c["chunk_index"],
        }
        for c in chunks
    ]

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    return {
        "status": "indexed",
        "pages_extracted": len(extracted_pages),
        "chunks_indexed": len(chunks),
        "file_sha256": file_sha256,
        "collection_count": collection.count(),
        "chroma_dir": str(resolved_chroma),
    }


def main():
    """CLI entry point for handbook ingestion."""
    parser = argparse.ArgumentParser(description="Ingest employee handbook PDF into persistent ChromaDB.")
    parser.add_argument("--force", action="store_true", help="Force re-indexing even if file hash matches.")
    parser.add_argument("--pdf", type=str, default=None, help="Path to employee handbook PDF.")
    parser.add_argument("--chroma-dir", type=str, default=None, help="Path to ChromaDB persistent storage directory.")
    args = parser.parse_args()

    result = ingest_handbook(pdf_path=args.pdf, chroma_dir=args.chroma_dir, force=args.force)

    print("\n================ Handbook Ingestion Report ================")
    print(f"Status           : {result['status'].upper()} ({result.get('reason', 'completed')})")
    print(f"File SHA-256     : {result['file_sha256']}")
    print(f"Pages Extracted  : {result['pages_extracted']}")
    print(f"Chunks Indexed   : {result['chunks_indexed']}")
    print(f"Collection Count : {result['collection_count']}")
    print(f"Chroma Directory : {result['chroma_dir']}")
    print("===========================================================\n")


if __name__ == "__main__":
    main()
