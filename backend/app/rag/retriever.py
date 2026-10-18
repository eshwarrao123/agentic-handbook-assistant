"""Handbook retriever using persistent ChromaDB and distance gating (TECHNICAL_DESIGN.md §11.2 & §11.3)."""

import sys
if sys.version_info.major == 3 and sys.version_info.minor != 13:
    sys.path = [p for p in sys.path if "Python313" not in p]

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings


@dataclass
class RetrievedChunk:
    """Passage retrieved from vector store with source metadata and cosine distance."""
    chunk_id: str
    document: str
    title: str
    page: int
    chunk_index: int
    text: str
    distance: float


class HandbookRetriever:
    """Semantic retriever over the ingested handbook collection."""

    def __init__(
        self,
        chroma_dir: Optional[Union[str, Path]] = None,
        collection_name: str = "handbook",
    ):
        self.chroma_dir = Path(chroma_dir or settings.CHROMA_DIR)
        self.collection_name = collection_name
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection = None

    def _get_collection(self):
        """Lazily initialize client and collection."""
        if self._collection is None:
            self._client = chromadb.PersistentClient(
                path=str(self.chroma_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            try:
                self._collection = self._client.get_collection(name=self.collection_name)
            except Exception as exc:
                raise RuntimeError(
                    f"Handbook collection '{self.collection_name}' not found at {self.chroma_dir}. "
                    "Run 'python -m app.rag.ingest' to initialize the vector index."
                ) from exc
        return self._collection

    def retrieve_sync(
        self,
        query: str,
        top_k: Optional[int] = None,
        max_distance: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """Synchronously query ChromaDB with distance gating (IR-04: wrap with to_thread in async paths)."""
        k = top_k if top_k is not None else settings.RETRIEVAL_TOP_K
        threshold = max_distance if max_distance is not None else settings.RETRIEVAL_MAX_DISTANCE

        coll = self._get_collection()
        results = coll.query(
            query_texts=[query],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        passages: List[RetrievedChunk] = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return passages

        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for chunk_id, doc_text, meta, dist in zip(ids, docs, metas, distances):
            # Apply calibrated distance gate (TECHNICAL_DESIGN §11.3)
            if threshold is not None and dist > threshold:
                continue

            passages.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document=meta.get("source", "employee_handbook.pdf"),
                    title=meta.get("title", "Zava Employee Handbook"),
                    page=int(meta.get("page", 1)),
                    chunk_index=int(meta.get("chunk_index", 0)),
                    text=doc_text,
                    distance=float(dist),
                )
            )

        # Sort by ascending distance (closest match first)
        passages.sort(key=lambda p: p.distance)
        return passages

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        max_distance: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """Asynchronously query ChromaDB, delegating blocking vector search to a worker thread."""
        return await asyncio.to_thread(self.retrieve_sync, query, top_k, max_distance)


# Default retriever singleton
_default_retriever: Optional[HandbookRetriever] = None


def get_retriever() -> HandbookRetriever:
    """Return singleton HandbookRetriever instance."""
    global _default_retriever
    if _default_retriever is None:
        _default_retriever = HandbookRetriever()
    return _default_retriever
