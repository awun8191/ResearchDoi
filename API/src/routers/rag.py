import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from src.core.dependencies import get_current_user
from src.models.rag import IngestRequest, IngestResponse, SearchRequest, SearchResult
from src.service.rag import rag_service
from src.service.web_loader import load_web_page, extract_text_from_pdf_bytes

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Chunk and embed a document into the project's RAG store",
)
async def ingest_document(
    body: IngestRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> IngestResponse:
    """
    Chunk the provided text, generate Gemini embeddings for each chunk,
    and store them in the in-process vector store scoped to (uid, project_id, chat_id).

    Call this once per source document when opening a project workspace.
    On page refresh the store is empty — the frontend must re-seed.
    """
    return await rag_service.ingest(
        uid=user["uid"],
        project_id=body.project_id,
        chat_id=body.chat_id,
        text=body.text,
        metadata=body.metadata,
    )


@router.post(
    "/ingest/url",
    response_model=IngestResponse,
    summary="Fetch, chunk and embed a website URL into the project's RAG store",
)
async def ingest_url(
    project_id: str,
    chat_id: str = "default",
    url: str = "",
    user: dict[str, Any] = Depends(get_current_user),
) -> IngestResponse:
    """
    Fetches the content from the given URL, extracts its clean text,
    and ingests it into the project's RAG vector store scoped to (uid, project_id, chat_id).
    """
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is required",
        )

    text = await load_web_page(url)
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not extract meaningful text from URL: {url}",
        )

    return await rag_service.ingest(
        uid=user["uid"],
        project_id=project_id,
        chat_id=chat_id,
        text=text,
        metadata={"url": url, "source_type": "web"},
    )


@router.post(
    "/ingest/file",
    response_model=IngestResponse,
    summary="Upload and ingest a PDF file",
)
async def ingest_file(
    project_id: str,
    chat_id: str = "default",
    file: UploadFile = File(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> IngestResponse:
    """
    Upload a PDF file, extract its text, and ingest into the RAG store.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    try:
        pdf_bytes = await file.read()

        # Check if it's actually a PDF
        if len(pdf_bytes) < 5 or pdf_bytes[:5] != b"%PDF-":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a valid PDF",
            )

        text = extract_text_from_pdf_bytes(pdf_bytes)
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract text from PDF",
            )

        return await rag_service.ingest(
            uid=user["uid"],
            project_id=project_id,
            chat_id=chat_id,
            text=text,
            metadata={"filename": file.filename, "source_type": "upload"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[rag] Failed to ingest file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(exc)}",
        )


@router.post(
    "/ingest/sources",
    response_model=IngestResponse,
    summary="Ingest all sources from project metadata",
)
async def ingest_project_sources(
    project_id: str,
    chat_id: str = "default",
    user: dict[str, Any] = Depends(get_current_user),
) -> IngestResponse:
    """
    Fetches and ingests content from all sources associated with a project.
    This uses the project's stored source URLs to populate the RAG store.
    """
    from google.cloud import firestore

    try:
        db = firestore.Client()
        project_ref = (
            db.collection("users")
            .document(user["uid"])
            .collection("projects")
            .document(project_id)
        )
        project_doc = project_ref.get()

        if not project_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found",
            )

        project_data = project_doc.to_dict()
        sources = project_data.get("sources", [])

        if not sources:
            return IngestResponse(chunks_stored=0)

        total_chunks = 0

        for source in sources:
            url = source.get("url") or source.get("pdfUrl")
            if not url:
                continue

            try:
                text = await load_web_page(url)
                if text:
                    result = await rag_service.ingest(
                        uid=user["uid"],
                        project_id=project_id,
                        chat_id=chat_id,
                        text=text,
                        metadata={
                            "url": url,
                            "title": source.get("title", "Unknown"),
                            "source_type": source.get("type", "web"),
                        },
                    )
                    total_chunks += result.chunks_stored
            except Exception as e:
                logger.warning(f"[rag] Failed to ingest source {url}: {e}")
                continue

        return IngestResponse(chunks_stored=total_chunks)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[rag] Failed to ingest project sources: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest sources: {str(exc)}",
        )


@router.post(
    "/search",
    response_model=list[SearchResult],
    summary="Search the project's RAG vector store",
)
async def search_knowledge_base(
    body: SearchRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[SearchResult]:
    """
    Embed the query and return the top-k most similar document chunks.
    Returns an empty list if the store has not been seeded yet.
    """
    return await rag_service.search(
        uid=user["uid"],
        project_id=body.project_id,
        chat_id=body.chat_id,
        query=body.query,
        top_k=body.top_k,
    )


@router.delete(
    "/store",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear the RAG vector store for a project",
)
async def clear_store(
    project_id: str,
    chat_id: str = "default",
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """
    Removes all vectors for the given project/chat from the in-process store.
    Useful for re-seeding after sources are updated.
    """
    rag_service.clear(uid=user["uid"], project_id=project_id, chat_id=chat_id)
