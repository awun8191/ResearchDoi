"""
Server-side RAG service.

Architecture:
  - In-process vector store (dict keyed by "{uid}:{project_id}:{chat_id}")
  - Embeddings generated via Gemini Embedding API (gemini-embedding-001)
  - Cosine similarity computed with numpy for speed
  - Chunk cap: MAX_CHUNKS_PER_DOC (100) — prevents runaway API quota
  - Chunks are NOT persisted to Firestore (embeddings are deterministic,
    cheap to recompute, and large to store). On restart, the frontend
    re-seeds the store by calling POST /api/rag/ingest for each source.

Chunking strategy:
  - Split on paragraph boundaries (\n\n) first
  - Merge short paragraphs to hit TARGET_CHUNK_SIZE characters
  - Overlap via sliding window: CHUNK_OVERLAP characters from previous chunk
"""

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx
import numpy as np

from src.core.config import settings
from src.models.rag import IngestResponse, SearchResult

logger = logging.getLogger(__name__)

TARGET_CHUNK_SIZE = 500
MAX_CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
MAX_CHUNKS_PER_DOC = 100

EMBEDDING_MODEL = "gemini-embedding-2-preview"
EMBEDDING_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBEDDING_MODEL}:embedContent"


@dataclass
class VectorEntry:
    id: str
    text: str
    embedding: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Text chunking ─────────────────────────────────────────────────────────────


def _chunk_text(text: str) -> list[str]:
    """
    Split text into semantically coherent chunks.
    1. Split on paragraph breaks
    2. Merge short paragraphs until TARGET_CHUNK_SIZE
    3. Split long paragraphs at sentence boundaries
    4. Add CHUNK_OVERLAP from the tail of the previous chunk
    """
    # Normalise whitespace
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    paragraphs = text.split("\n\n")

    chunks: list[str] = []
    buffer = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(buffer) + len(para) < TARGET_CHUNK_SIZE:
            buffer = (buffer + "\n\n" + para).strip() if buffer else para
        else:
            if buffer:
                chunks.append(buffer)
            # Para itself may exceed MAX_CHUNK_SIZE — split at sentences
            if len(para) > MAX_CHUNK_SIZE:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                sub_buffer = ""
                for sent in sentences:
                    if len(sub_buffer) + len(sent) < TARGET_CHUNK_SIZE:
                        sub_buffer = (sub_buffer + " " + sent).strip()
                    else:
                        if sub_buffer:
                            chunks.append(sub_buffer)
                        sub_buffer = sent
                if sub_buffer:
                    buffer = sub_buffer
                else:
                    buffer = ""
            else:
                buffer = para

    if buffer:
        chunks.append(buffer)

    # Apply overlap
    overlapped: list[str] = []
    for i, chunk in enumerate(chunks):
        if i == 0:
            overlapped.append(chunk)
        else:
            tail = chunks[i - 1][-CHUNK_OVERLAP:]
            overlapped.append(tail + " " + chunk)

    return overlapped[:MAX_CHUNKS_PER_DOC]


# ── Embedding ──────────────────────────────────────────────────────────────────


async def _embed(
    client: httpx.AsyncClient, text: str, task_type: str = "RETRIEVAL_DOCUMENT"
) -> np.ndarray:
    """Call Gemini Embedding API and return a numpy unit vector."""
    resp = await client.post(
        EMBEDDING_URL,
        params={"key": settings.gemini_api_key},
        json={
            "model": f"models/{EMBEDDING_MODEL}",
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    values = resp.json()["embedding"]["values"]
    vec = np.array(values, dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Dot product of two pre-normalised unit vectors = cosine similarity."""
    return float(np.dot(a, b))


# ── Service class ──────────────────────────────────────────────────────────────


class RagService:
    """
    Singleton-style RAG service.
    Vector stores are per (uid, project_id, chat_id) triplet and live for the process lifetime.
    This ensures each chat instance has its own RAG context.
    """

    def __init__(self) -> None:
        self._stores: dict[str, list[VectorEntry]] = {}

    def _store_key(self, uid: str, project_id: str, chat_id: str = "default") -> str:
        return f"{uid}:{project_id}:{chat_id}"

    def _get_store(
        self, uid: str, project_id: str, chat_id: str = "default"
    ) -> list[VectorEntry]:
        return self._stores.setdefault(self._store_key(uid, project_id, chat_id), [])

    async def ingest(
        self,
        uid: str,
        project_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        chat_id: str = "default",
    ) -> IngestResponse:
        """
        Chunk text, embed each chunk, and store in the in-process vector store.
        Chunks are batched: we parallelise embedding for up to 10 chunks at once
        to avoid rate-limit issues while still being much faster than purely sequential.
        """
        metadata = metadata or {}
        chunks = _chunk_text(text)
        store = self._get_store(uid, project_id, chat_id)
        batch_size = 10
        stored = 0

        async with httpx.AsyncClient() as client:
            for batch_start in range(0, len(chunks), batch_size):
                batch = chunks[batch_start : batch_start + batch_size]
                tasks = [_embed(client, chunk, "RETRIEVAL_DOCUMENT") for chunk in batch]
                try:
                    embeddings = await asyncio.gather(*tasks)
                    for chunk, embedding in zip(batch, embeddings):
                        store.append(
                            VectorEntry(
                                id=f"chunk_{uuid.uuid4().hex[:12]}",
                                text=chunk,
                                embedding=embedding,
                                metadata=metadata,
                            )
                        )
                        stored += 1
                except Exception as exc:
                    logger.error(
                        "[rag] Embedding batch failed at offset %d: %s",
                        batch_start,
                        exc,
                    )
                    break  # partial ingest — don't raise, caller gets the count

        logger.info(
            "[rag] Ingested %d chunks for uid=%s project=%s chat=%s",
            stored,
            uid,
            project_id,
            chat_id,
        )
        return IngestResponse(chunks_stored=stored)

    async def search(
        self,
        uid: str,
        project_id: str,
        query: str,
        top_k: int = 3,
        chat_id: str = "default",
    ) -> list[SearchResult]:
        """
        Embed the query and return the top-k most similar chunks by cosine similarity.
        """
        store = self._get_store(uid, project_id, chat_id)
        if not store:
            logger.info(
                "[rag] Vector store empty for uid=%s project=%s chat=%s",
                uid,
                project_id,
                chat_id,
            )
            return []

        async with httpx.AsyncClient() as client:
            try:
                query_embedding = await _embed(client, query, "RETRIEVAL_QUERY")
            except Exception as exc:
                logger.error("[rag] Failed to embed query: %s", exc)
                return []

        scored = [
            SearchResult(
                id=entry.id,
                text=entry.text,
                score=_cosine_similarity(query_embedding, entry.embedding),
                metadata=entry.metadata,
            )
            for entry in store
        ]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def clear(self, uid: str, project_id: str, chat_id: str = "default") -> None:
        key = self._store_key(uid, project_id, chat_id)
        self._stores.pop(key, None)
        logger.info(
            "[rag] Vector store cleared for uid=%s project=%s chat=%s",
            uid,
            project_id,
            chat_id,
        )


# Module-level singleton — imported by gemini.py and rag router
rag_service = RagService()
