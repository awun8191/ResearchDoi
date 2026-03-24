import logging
from urllib.parse import unquote
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies import get_current_user
from src.models.doi import DoiMetadataResponse
from src.service.doi_lookup import DoiLookup

logger = logging.getLogger(__name__)
router = APIRouter()

_doi_service = DoiLookup()


@router.get(
    "/{doi:path}",
    response_model=DoiMetadataResponse,
    summary="Fetch DOI metadata from CrossRef",
    responses={
        404: {"description": "DOI not found in CrossRef"},
        422: {"description": "DOI string is malformed"},
    },
)
async def get_doi_metadata(
    doi: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> DoiMetadataResponse:
    """
    Resolve a DOI to its full CrossRef metadata.

    The `doi` path parameter accepts any of:
    - Bare: `10.1038/nphys1170`
    - URL-encoded: `10.1038%2Fnphys1170`
    - Prefixed: `https://doi.org/10.1038/nphys1170`
    - `doi:10.1038/nphys1170`
    """
    # FastAPI path params don't URL-decode automatically when using `:path`
    doi = unquote(doi)

    try:
        result = _doi_service.fetch_metadata(doi)
    except Exception as exc:
        logger.error("[doi_router] Unexpected error for doi=%s: %s", doi, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to contact CrossRef API",
        )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No CrossRef record found for DOI: {doi}",
        )

    return DoiMetadataResponse(
        doi=result.get("doi", doi),
        title=result.get("title"),
        authors=result.get("authors", []),
        publication_year=result.get("publication_year"),
        venue=result.get("venue"),
        url=result.get("url"),
        # storage_path and document_url are null until user uploads PDF
        storage_path=None,
        document_url=None,
    )
