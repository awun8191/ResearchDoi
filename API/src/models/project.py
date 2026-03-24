"""
Pydantic models for the project CRUD API.

Mirrors the Firestore document shape managed by the frontend
`projectService.js` — field names and types match exactly.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Source (DOI entry inside a project) ──────────────────────────────────────

class SourceItem(BaseModel):
    type: str = "doi"  # e.g., "doi", "url", "file"
    doi: Optional[str] = None
    url: Optional[str] = None
    filename: Optional[str] = None
    title: Optional[str] = None
    authors: list[str] = []
    journal: Optional[str] = None
    date: Optional[str] = None
    pdf_url: Optional[str] = None
    is_open_access: bool = False
    oa_status: Optional[str] = None
    resolved_via: str = "none"
    storage_path: Optional[str] = None
    document_url: Optional[str] = None
    added_at: Optional[str] = None  # ISO-8601 string set by the client


# ── Request / Response bodies ────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Project display name")
    instructions: str = Field(
        default="",
        max_length=10_000,
        description="System-prompt instructions passed to Gemini for this project",
    )


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    instructions: Optional[str] = Field(None, max_length=10_000)


class AddSourceRequest(BaseModel):
    type: str = Field("doi", description="Source type: 'doi', 'url', or 'file'")
    doi: Optional[str] = Field(None, description="Cleaned DOI string")
    url: Optional[str] = None
    filename: Optional[str] = None
    title: Optional[str] = None
    authors: list[str] = []
    journal: Optional[str] = None
    date: Optional[str] = None
    pdf_url: Optional[str] = None
    is_open_access: bool = False
    oa_status: Optional[str] = None
    resolved_via: str = "none"
    storage_path: Optional[str] = None
    document_url: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    instructions: str = ""
    sources: list[SourceItem] = []
    corpus_id: Optional[str] = None
    # Firestore Timestamps are serialised to ISO-8601 strings at the service layer
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
