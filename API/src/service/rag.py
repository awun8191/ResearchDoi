"""
Server-side RAG service — ChromaDB-backed vector store.

Architecture:
  - ChromaDB PersistentClient — data survives server restarts
  - One collection per (uid, project_id, chat_id) triplet
  - Embeddings generated via OpenRouter embedding API
  - Cosine similarity (default HNSW distance metric in ChromaDB)
  - Chunk cap: MAX_CHUNKS_PER_DOC (100)

Chunking strategy:
  - Split on paragraph boundaries (\n\n) first
  - Merge short paragraphs to hit TARGET_CHUNK_SIZE characters
  - Overlap via sliding window: CHUNK_OVERLAP characters from previous chunk
"""

import asyncio
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any

import chromadb
import httpx

from src.core.config import settings
from src.models.rag import IngestResponse, SearchResult

logger = logging.getLogger(__name__)

TARGET_CHUNK_SIZE = 500
MAX_CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
MAX_CHUNKS_PER_DOC = 100

EMBEDDING_MODEL = settings.embedding_model
OPENROUTER_BASE = settings.openrouter_base
OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {settings.openrouter_api_key}",
    "Content-Type": "application/json",
}

# ChromaDB persistence path
_CHROMA_DIR = Path.home() / ".hermes" / "chromadb" / "rast"


def _collection_name(uid: str, project_id: str, chat_id: str = "default") -> str:
    """Sanitized collection name — ChromaDB allows alphanumeric + hyphens/underscores."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", f"rast_{uid}_{project_id}_{chat_id}")
    # ChromaDB has a 63-char limit on collection names
    return safe[:63]


# ── Text chunking ─────────────────────────────────────────────────────────────


def _chunk_text(text: str) -> list[str]:
    """
    Split text into semantically coherent chunks.
    1. Split on paragraph breaks
    2. Merge short paragraphs until TARGET_CHUNK_SIZE
    3. Split long paragraphs at sentence boundaries
    4. Add CHUNK_OVERLAP from the tail of the previous chunk
    """
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
    client: httpx.AsyncClient, text: str
) -> list[float]:
    """Call OpenRouter embedding API and return the embedding vector."""
    url = f"{OPENROUTER_BASE}/embeddings"
    resp = await client.post(
        url,
        headers=OPENROUTER_HEADERS,
        json={
            "model": EMBEDDING_MODEL,
            "input": text,
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["data"][0]["embedding"]


# ── ChromaDB-backed service ────────────────────────────────────────────────────


class RagService:
    """
    RAG service backed by ChromaDB PersistentClient.

    Each (uid, project_id, chat_id) triplet gets its own collection.
    Data persists across server restarts — no re-seeding needed.
    """

    def __init__(self) -> None:
        os.makedirs(_CHROMA_DIR, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
        self._collection_cache: dict[str, Any] = {}

    def _get_collection(self, uid: str, project_id: str, chat_id: str = "default") -> Any:
        """Get or create a ChromaDB collection for the given scope."""
        name = _collection_name(uid, project_id, chat_id)

        # Return cached if available (avoids repeated metadata checks)
        if name in self._collection_cache:
            return self._collection_cache[name]

        try:
            collection = self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            logger.error("[rag] Failed to get/create collection %s: %s", name, exc)
            raise

        self._collection_cache[name] = collection
        return collection

    async def ingest(
        self,
        uid: str,
        project_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        chat_id: str = "default",
    ) -> IngestResponse:
        """
        Chunk text, embed each chunk, and store in ChromaDB collection.
        Chunks are batched: we parallelise embedding for up to 10 chunks at once.
        """
        metadata = metadata or {}
        chunks = _chunk_text(text)
        collection = self._get_collection(uid, project_id, chat_id)
        batch_size = 10
        stored = 0

        async with httpx.AsyncClient() as client:
            for batch_start in range(0, len(chunks), batch_size):
                batch = chunks[batch_start : batch_start + batch_size]
                tasks = [_embed(client, chunk) for chunk in batch]
                try:
                    embeddings = await asyncio.gather(*tasks)
                    ids = [f"chunk_{uuid.uuid4().hex[:12]}" for _ in batch]
                    metadatas = [{**metadata, "doc_id": ids[i]} for i in range(len(batch))]

                    collection.add(
                        ids=ids,
                        embeddings=embeddings,
                        metadatas=metadatas,
                        documents=batch,
                    )
                    stored += len(batch)
                except Exception as exc:
                    logger.error(
                        "[rag] Embedding batch failed at offset %d: %s",
                        batch_start, exc,
                    )
                    break

        logger.info(
            "[rag] Ingested %d chunks for uid=%s project=%s chat=%s",
            stored, uid, project_id, chat_id,
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
        Embed the query and return the top-k most similar chunks.
        Uses ChromaDB's built-in ANN search (HNSW with cosine distance).
        """
        collection = self._get_collection(uid, project_id, chat_id)

        # Quick check if collection has data
        try:
            count = collection.count()
        except Exception:
            count = 0

        if count == 0:
            logger.info(
                "[rag] ChromaDB collection empty for uid=%s project=%s chat=%s",
                uid, project_id, chat_id,
            )
            return []

        async with httpx.AsyncClient() as client:
            try:
                query_embedding = await _embed(client, query)
            except Exception as exc:
                logger.error("[rag] Failed to embed query: %s", exc)
                return []

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, count),
            )
        except Exception as exc:
            logger.error("[rag] ChromaDB query failed: %s", exc)
            return []

        # ChromaDB returns lists-of-lists (one per query, we have one query)
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if not ids:
            return []

        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity score: 1 - (distance / 2) → 0..1 range
        scored = []
        for i in range(len(ids)):
            distance = distances[i] if i < len(distances) else 1.0
            score = 1.0 - (distance / 2.0)
            scored.append(
                SearchResult(
                    id=ids[i],
                    text=documents[i] if i < len(documents) else "",
                    score=max(0.0, score),
                    metadata=metadatas[i] if i < len(metadatas) else {},
                )
            )

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored

    def clear(self, uid: str, project_id: str, chat_id: str = "default") -> None:
        """Delete the entire ChromaDB collection for the given scope."""
        name = _collection_name(uid, project_id, chat_id)
        try:
            self._client.delete_collection(name)
            self._collection_cache.pop(name, None)
            logger.info(
                "[rag] ChromaDB collection deleted: uid=%s project=%s chat=%s",
                uid, project_id, chat_id,
            )
        except Exception as exc:
            logger.warning(
                "[rag] Failed to delete collection %s: %s", name, exc,
            )


# Module-level singleton — imported by gemini.py and rag router
rag_service = RagService()
