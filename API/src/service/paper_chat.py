"""
Paper Chat Service — full-document context chat for single papers.

Flow:
1. Resolve paper_id (DOI/ArXiv ID) → get metadata + PDF URL
2. Download PDF → extract text via pymupdf4llm
3. Build system prompt with full paper text as context
4. Call Gemma 4 31B via OpenRouter with conversation history
5. Return response
"""

import json
import logging
from typing import Any, Optional

import httpx

from src.core.config import settings
from src.service.arxiv_lookup import ArxivLookup
from src.service.doi_lookup import DoiLookup
from src.service.pdf_resolver import resolve_pdf
from src.service.web_loader import load_web_page

logger = logging.getLogger(__name__)

CHAT_MODEL = settings.chat_model
OPENROUTER_BASE = settings.openrouter_base
OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {settings.openrouter_api_key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://rast-app.vercel.app",
    "X-Title": "ResearchDoi",
}

# Max tokens to reserve for the paper text (256K - safety margin)
MAX_PAPER_TOKENS = 220000
# Rough estimate: 1 token ≈ 4 characters for English text
MAX_PAPER_CHARS = MAX_PAPER_TOKENS * 4


async def _resolve_paper(paper_id: str) -> dict[str, Any]:
    """
    Resolve a paper identifier to its metadata and full text.
    Tries ArXiv first, then CrossRef DOI.
    """
    arxiv_svc = ArxivLookup()
    doi_svc = DoiLookup(contact_email=settings.unpaywall_email)

    # Step 1: Get metadata
    metadata = None
    resolved_via = None

    # Try ArXiv first
    try:
        metadata = await arxiv_svc.fetch_metadata_async(paper_id)
        if metadata:
            resolved_via = "arxiv"
            logger.info("[paper_chat] Resolved via ArXiv: %s", paper_id)
    except Exception as exc:
        logger.warning("[paper_chat] ArXiv lookup failed: %s", exc)

    # Fall back to CrossRef DOI
    if not metadata:
        try:
            metadata = await doi_svc.fetch_metadata(paper_id)
            if metadata:
                resolved_via = "crossref"
                logger.info("[paper_chat] Resolved via CrossRef: %s", paper_id)
        except Exception as exc:
            logger.warning("[paper_chat] CrossRef lookup failed: %s", exc)

    if not metadata:
        raise ValueError(f"Could not resolve paper identifier: {paper_id}")

    # Step 2: Get PDF URL
    pdf_url = metadata.get("pdf_url")
    if not pdf_url:
        try:
            crossref_links = metadata.get("link", [])
            resolved = await resolve_pdf(doi=paper_id, crossref_links=crossref_links)
            pdf_url = resolved.pdf_url
            if pdf_url:
                metadata["pdf_url"] = pdf_url
                metadata["is_open_access"] = resolved.is_open_access
        except Exception as exc:
            logger.warning("[paper_chat] PDF resolution failed: %s", exc)

    return metadata


async def _download_and_extract_text(pdf_url: str) -> str:
    """Download a PDF and extract its text content."""
    text = await load_web_page(pdf_url)
    if not text:
        raise ValueError(f"Could not extract text from PDF URL: {pdf_url}")

    # Truncate if too long
    if len(text) > MAX_PAPER_CHARS:
        logger.warning(
            "[paper_chat] Paper text too long (%d chars), truncating to %d",
            len(text), MAX_PAPER_CHARS,
        )
        text = text[:MAX_PAPER_CHARS]

    return text


async def _openrouter_chat(
    messages: list[dict[str, Any]],
    max_tokens: int = 4096,
) -> str:
    """Call OpenRouter chat completions and return the model's text."""
    url = f"{OPENROUTER_BASE}/chat/completions"
    payload = {
        "model": CHAT_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=OPENROUTER_HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()

    choice = data.get("choices", [{}])[0]
    return choice.get("message", {}).get("content", "") or "No response generated."


async def chat_about_paper(
    paper_id: str,
    user_message: str,
    history: Optional[list[dict[str, str]]] = None,
    chat_title: Optional[str] = None,
) -> dict[str, Any]:
    """
    Full entry point for the paper chat feature.
    Resolves the paper, downloads text, and chats about it.
    """
    history = history or []

    # Resolve paper metadata
    metadata = await _resolve_paper(paper_id)

    paper_text = None
    pdf_url = metadata.get("pdf_url")

    if pdf_url:
        try:
            paper_text = await _download_and_extract_text(pdf_url)
        except Exception as exc:
            logger.warning("[paper_chat] Failed to download paper text: %s", exc)

    # Build system prompt
    if paper_text:
        system_prompt = (
            "You are a research assistant analyzing an academic paper. "
            "The full paper text is provided below. Answer the user's questions "
            "based on the paper content. Cite specific sections when relevant.\n\n"
            f"## PAPER: {metadata.get('title', 'Unknown')}\n"
            f"## AUTHORS: {', '.join(metadata.get('authors', []) or [])}\n"
            f"## YEAR: {metadata.get('publication_year', 'Unknown')}\n\n"
            f"## FULL TEXT\n{paper_text}"
        )
    else:
        # No PDF available — use abstract/metadata only
        system_prompt = (
            "You are a research assistant. The user is asking about a paper, "
            "but the full text is not available. Answer based on the metadata and abstract below.\n\n"
            f"## PAPER: {metadata.get('title', 'Unknown')}\n"
            f"## AUTHORS: {', '.join(metadata.get('authors', []) or [])}\n"
            f"## YEAR: {metadata.get('publication_year', 'Unknown')}\n"
            f"## ABSTRACT: {metadata.get('abstract', 'Not available')}"
        )

    # Build messages array
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt}
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    # Call Gemma 4 31B via OpenRouter
    reply = await _openrouter_chat(messages)

    return {
        "reply": reply,
        "paper_id": paper_id,
        "title": metadata.get("title"),
        "authors": metadata.get("authors", []) or [],
        "pdf_url": pdf_url,
    }
