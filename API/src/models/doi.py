from typing import Optional
from pydantic import BaseModel


class DoiMetadataResponse(BaseModel):
    """
    Standardised DOI metadata returned by the /api/doi/{doi} endpoint.

    storage_path and document_url are populated only if a PDF for this source
    has been uploaded to Firebase Storage via /api/storage/upload.
    """

    doi: str
    title: Optional[str] = None
    authors: list[str] = []
    publication_year: Optional[int] = None
    venue: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    abstract: Optional[str] = None
    # Firebase Storage coupling — null until user uploads PDF
    storage_path: Optional[str] = None
    document_url: Optional[str] = None


class DoiSearchResponse(BaseModel):
    """
    Response model for the /api/doi/search endpoint.
    """
    query: str
    results: list[DoiMetadataResponse]
    total: int
