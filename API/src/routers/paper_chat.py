"""
Paper Chat Router — full-document context chat for single papers.
Mounted at /api/chat/paper.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies import get_current_user
from src.models.paper_chat import (
    PaperChatMessage,
    PaperChatRequest,
    PaperChatResponse,
)
from src.service import paper_chat as paper_chat_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "",
    response_model=PaperChatResponse,
    summary="Chat about a single paper with full document context",
    responses={
        404: {"description": "Paper not found"},
        502: {"description": "AI model call failed"},
    },
)
async def chat_about_paper(
    body: PaperChatRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> PaperChatResponse:
    """
    Chat about a single academic paper.

    The full paper text is loaded into Gemma 4 31B's 256K context window —
    no chunking, no embedding, no RAG. This gives the AI complete visibility
    into the paper for accurate summarization and Q&A.

    **Flow:**
    1. Resolve paper_id (DOI or ArXiv ID) → metadata + PDF URL
    2. Download PDF → extract text via pymupdf4llm
    3. Load full text as system context → Gemma 4 31B via OpenRouter
    4. Return AI response

    **Limitations:**
    - One paper at a time (use Project Workspace for multi-document RAG)
    - Papers over ~200K tokens are truncated
    """
    try:
        history_dicts = [
            {"role": msg.role, "content": msg.content}
            for msg in body.history
        ]

        result = await paper_chat_service.chat_about_paper(
            paper_id=body.paper_id,
            user_message=body.message,
            history=history_dicts,
            chat_title=body.chat_title,
        )

        return PaperChatResponse(
            reply=result["reply"],
            paper_id=result["paper_id"],
            title=result.get("title"),
            authors=result.get("authors", []),
            chat_id=body.paper_id,  # Use paper_id as chat_id for session tracking
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("[paper_chat_router] Failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI chat failed: {str(exc)}",
        )
