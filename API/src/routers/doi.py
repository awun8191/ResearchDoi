import logging
from urllib.parse import unquote
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore
import datetime
from datetime import timezone

from src.core.dependencies import get_current_user
from src.models.doi import DoiMetadataResponse, DoiSearchResponse
from src.service.arxiv_lookup import ArxivLookup
from src.service.doi_lookup import DoiLookup

logger = logging.getLogger(__name__)
router = APIRouter()

_arxiv_service = ArxivLookup()
_doi_service = DoiLookup()


@router.get(
    "/{doi:path}",
    response_model=DoiMetadataResponse,
    summary="Fetch Metadata from ArXiv/CrossRef",
    responses={
        404: {"description": "Identifier not found in ArXiv or CrossRef"},
        422: {"description": "Identifier string is malformed"},
    },
)
async def get_doi_metadata(
    doi: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> DoiMetadataResponse:
    """
    Resolve an identifier to its full metadata.
    Checks ArXiv first (best for preprints/IDs), then falls back to CrossRef (exhaustive DOI registry).
    """
    # FastAPI path params don't URL-decode automatically when using `:path`
    doi = unquote(doi)

    result = None
    try:
        # 1. Try ArXiv (supports native ArXiv IDs and some DOIs)
        result = await _arxiv_service.fetch_metadata_async(doi)
    except Exception as exc:
        logger.warning("[doi_router] ArXiv lookup failed for %s: %s", doi, exc)

    if result is None:
        try:
            # 2. Try CrossRef fallback (supports all scholarly DOIs)
            result = await _doi_service.fetch_metadata(doi)
        except Exception as exc:
            logger.error("[doi_router] CrossRef lookup failed for %s: %s", doi, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to contact metadata providers",
            )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No record found for identifier: {doi}",
        )

    # Automatically save to user's history
    uid = user.get("uid")
    if uid:
        try:
            db = firestore.client()
            safe_doi_id = doi.replace("/", "_")
            history_ref = db.collection("users").document(uid).collection("history").document(safe_doi_id)
            
            history_doc = result.copy()
            history_doc["doi"] = result.get("doi", doi)
            history_doc["lookedUpAt"] = datetime.datetime.now(timezone.utc).isoformat()
            
            history_ref.set(history_doc, merge=True)
        except Exception as e:
            logger.error(f"[doi_router] Failed to save history for uid={uid}, doi={doi}: {e}")

    return DoiMetadataResponse(
        doi=result.get("doi", doi),
        title=result.get("title"),
        authors=result.get("authors", []),
        publication_year=result.get("publication_year"),
        venue=result.get("venue"),
        url=result.get("url"),
        pdf_url=result.get("pdf_url"),
        abstract=result.get("abstract"),
        # storage_path and document_url are null until user uploads PDF
        storage_path=None,
        document_url=result.get("pdf_url"),
    )


@router.get(
    "/search",
    response_model=DoiSearchResponse,
    summary="Search papers in ArXiv by keyword",
)
async def search_arxiv(
    q: str,
    limit: int = 10,
    user: dict[str, Any] = Depends(get_current_user),
) -> DoiSearchResponse:
    """
    Search ArXiv for papers based on a keyword query.
    """
    try:
        results = await _arxiv_service.search_async(q, max_results=limit)
        
        # Convert raw service results to Pydantic models
        models = [
            DoiMetadataResponse(
                doi=r.get("doi"),
                title=r.get("title"),
                authors=r.get("authors", []),
                publication_year=r.get("publication_year"),
                venue=r.get("venue"),
                url=r.get("url"),
                pdf_url=r.get("pdf_url"),
                abstract=r.get("abstract"),
                storage_path=None,
                document_url=r.get("pdf_url"),
            )
            for r in results
        ]
        
        return DoiSearchResponse(query=q, results=models, total=len(models))
    except Exception as exc:
        logger.error("[doi_router] Search failed for q=%s: %s", q, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ArXiv search failed",
        )

