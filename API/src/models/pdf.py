from typing import Optional
from pydantic import BaseModel


class PdfResolutionResponse(BaseModel):
    """
    Result of the 4-tier cascading PDF resolver.
    resolved_via identifies which tier produced the result.
    """

    pdf_url: Optional[str] = None
    is_open_access: bool = False
    oa_status: Optional[str] = None
    resolved_via: str = "none"
    # Literals: 'unpaywall' | 'semantic_scholar' | 'openalex' | 'heuristic' | 'crossref_link' | 'none'
