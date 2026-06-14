"""
PDF ingestion pipeline — section-aware text extraction and embedding.

Extracts text from PDF bytes, segments into academic sections
(abstract, introduction, methodology, etc.), and ingests each
section into the ChromaDB vector store via RagService.

This produces better search results than plain chunking because
users can ask about specific sections like "what methodology?"
and the RAG will match against methodology-tagged chunks.
"""

import asyncio
import logging
import re
from typing import Any, Optional

from src.service.rag import rag_service
from src.service.web_loader import extract_text_from_pdf_bytes

logger = logging.getLogger(__name__)

# Academic section keywords — ordered from most specific to most general
_TARGET_SECTIONS = [
    "methodology", "method", "results", "result",
    "background", "related work", "introduction",
    "abstract", "discussion", "conclusion", "references",
]


def _segment_into_sections(md_text: str) -> list[dict[str, str]]:
    """
    Split extracted markdown into logical academic sections.

    Detects section headers (## Methodology, # 3. Results, etc.)
    and maps them to standard categories. Content before the first
    detected header is tagged as "general".
    """
    header_pattern = re.compile(r"^(#{1,3})\s+(.*)", re.MULTILINE)

    sections: list[dict[str, str]] = []
    current_section_name = "general"
    current_content: list[str] = []

    lines = md_text.splitlines()
    for line in lines:
        match = header_pattern.match(line)
        if match:
            raw_header = match.group(2).strip().lower()
            mapped_category = None
            for cat in _TARGET_SECTIONS:
                if cat in raw_header:
                    mapped_category = cat
                    break
            new_section_name = mapped_category if mapped_category else raw_header

            if current_content:
                sections.append({
                    "section": current_section_name,
                    "text": "\n".join(current_content).strip(),
                })
            current_section_name = new_section_name
            current_content = [line]
        else:
            current_content.append(line)

    if current_content:
        sections.append({
            "section": current_section_name,
            "text": "\n".join(current_content).strip(),
        })

    return sections


async def ingest_pdf(
    uid: str,
    project_id: str,
    doi: str,
    pdf_bytes: bytes,
    chat_id: str = "default",
    base_metadata: Optional[dict[str, Any]] = None,
) -> int:
    """
    Full ingestion pipeline for a downloaded PDF.

    1. Extract Markdown text from PDF bytes
    2. Segment into academic sections
    3. Embed each section and store in ChromaDB via RagService

    Args:
        uid: User ID
        project_id: Project ID
        doi: DOI of the paper (used for metadata)
        pdf_bytes: Raw PDF file bytes
        chat_id: Chat session scope (default: "default")
        base_metadata: Additional metadata to attach to all chunks

    Returns:
        Total number of chunks stored in the vector store
    """
    logger.info(
        "[ingestion] Starting ingestion for uid=%s project=%s doi=%s",
        uid, project_id, doi,
    )

    # Step 1: Extract Markdown from PDF
    md_text = extract_text_from_pdf_bytes(pdf_bytes)
    if not md_text:
        logger.warning("[ingestion] No text extracted from PDF for doi=%s", doi)
        return 0

    # Step 2: Segment into academic sections
    sections = _segment_into_sections(md_text)
    logger.info("[ingestion] Segmented into %d sections", len(sections))

    base_metadata = base_metadata or {}
    base_metadata.setdefault("doi", doi)

    # Step 3: Embed each section into ChromaDB
    tasks = []
    for sec in sections:
        sec_metadata = base_metadata.copy()
        sec_metadata["section"] = sec["section"]
        tasks.append(
            rag_service.ingest(
                uid=uid,
                project_id=project_id,
                text=sec["text"],
                metadata=sec_metadata,
                chat_id=chat_id,
            )
        )

    responses = await asyncio.gather(*tasks, return_exceptions=True)
    total_chunks = 0
    for i, resp in enumerate(responses):
        if isinstance(resp, Exception):
            logger.error(
                "[ingestion] Section %d ingestion failed: %s", i, resp,
            )
        else:
            total_chunks += resp.chunks_stored

    logger.info(
        "[ingestion] Successfully ingested %d chunks for doi=%s",
        total_chunks, doi,
    )
    return total_chunks
