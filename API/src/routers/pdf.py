import logging
from typing import Any

from fastapi import APIRouter, Depends, Query

from src.core.dependencies import get_current_user
from src.models.pdf import PdfResolutionResponse
from src.service.pdf_resolver import resolve_pdf

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/resolve",
    response_model=PdfResolutionResponse,
    summary="Resolve a DOI to a PDF URL using 4-tier cascading strategy",
)
async def resolve_pdf_url(
    doi: str = Query(..., description="Cleaned DOI string (with or without URL prefix)"),
    user: dict[str, Any] = Depends(get_current_user),
) -> PdfResolutionResponse:
    """
    Attempts to find a free PDF for the given DOI using, in order:
    1. Unpaywall (verified open access)
    2. Semantic Scholar + OpenAlex (parallel)
    3. Publisher URL heuristics (arXiv, bioRxiv, PLoS, PeerJ, Frontiers)
    4. CrossRef link array

    Returns the first successful result. `resolved_via` indicates the tier.
    `pdf_url` is null if no PDF was found.
    """
    from src.service.doi_lookup import DoiLookup
    doi_service = DoiLookup()
    meta = await doi_service.fetch_metadata(doi) or {}
    crossref_links = meta.get("link", [])  # raw CrossRef link array if present

    return await resolve_pdf(doi=doi, crossref_links=crossref_links)
