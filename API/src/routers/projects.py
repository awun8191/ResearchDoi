"""
Projects router — full CRUD + source management.

All paths are prefixed with /api/projects (see main.py).

Endpoints:
  GET    /                    List all projects for the authenticated user
  POST   /                    Create a new project
  GET    /{project_id}        Get a single project
  PATCH  /{project_id}        Update name and/or instructions
  DELETE /{project_id}        Delete a project
  POST   /{project_id}/sources          Add a source (DOI entry)
  DELETE /{project_id}/sources/{doi}    Remove a source by DOI
"""

import logging
from urllib.parse import unquote
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form

from src.core.dependencies import get_current_user
from src.models.project import (
    AddSourceRequest,
    CreateProjectRequest,
    ProjectResponse,
    UpdateProjectRequest,
)
from src.service import projects as project_service
from src.service.web_loader import load_web_page
from src.service import storage as storage_service
import re
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_project(project: ProjectResponse | None, project_id: str) -> ProjectResponse:
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project  # type: ignore[return-value]



# ── Collection endpoints ──────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List all projects for the current user",
)
async def list_projects(
    user: dict[str, Any] = Depends(get_current_user),
) -> list[ProjectResponse]:
    return await project_service.list_projects(uid=user["uid"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(
    body: CreateProjectRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> ProjectResponse:
    return await project_service.create_project(
        uid=user["uid"],
        name=body.name,
        instructions=body.instructions,
    )


# ── Document endpoints ────────────────────────────────────────────────────────

@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a single project",
)
async def get_project(
    project_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> ProjectResponse:
    project = await project_service.get_project(uid=user["uid"], project_id=project_id)
    return _require_project(project, project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project's name and/or instructions",
)
async def update_project(
    project_id: str,
    body: UpdateProjectRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> ProjectResponse:
    if body.name is None and body.instructions is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update (name or instructions)",
        )
    project = await project_service.update_project(
        uid=user["uid"],
        project_id=project_id,
        name=body.name,
        instructions=body.instructions,
    )
    return _require_project(project, project_id)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project and all its metadata",
)
async def delete_project(
    project_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    deleted = await project_service.delete_project(uid=user["uid"], project_id=project_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )


# ── Sources endpoints ─────────────────────────────────────────────────────────

_PDF_DOWNLOAD_TIMEOUT = 30.0   # seconds
_PDF_MAX_BYTES = 50 * 1024 * 1024  # 50 MB
_PDF_MAGIC = b"%PDF-"  # all valid PDFs start with this


def _is_pdf_content_type(ct: str) -> bool:
    ct = ct.lower().split(";")[0].strip()
    return ct in ("application/pdf", "application/octet-stream", "binary/octet-stream")


def _is_pdf_bytes(data: bytes) -> bool:
    """Check the PDF magic number — ensures we never store HTML as a PDF."""
    return data[:5] == _PDF_MAGIC


async def _try_upload_pdf(
    uid: str,
    project_id: str,
    doi: str,
    pdf_url: str,
) -> tuple[str | None, str | None, bytes | None]:
    """
    Download the PDF at `pdf_url`, validate it is genuine, and upload to Firebase Storage.

    Validation:
      1. Content-Type must be application/pdf (or octet-stream)
      2. First 5 bytes must be %PDF-  ← catches HTML abstract pages posing as PDFs

    Returns (storage_path, document_url, pdf_bytes) on success, (None, None, None) on any failure.
    All errors are logged but never re-raised — source metadata is always saved.
    """
    import re
    import httpx
    from src.service import storage as storage_service

    # Sanitise DOI into a safe filename: "10.1038/nphys1170" → "10.1038_nphys1170.pdf"
    filename = re.sub(r"[^\w.\-]", "_", doi) + ".pdf"

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # ── HEAD pre-flight: bail early on obviously non-PDF responses ──
            try:
                head = await client.head(
                    pdf_url,
                    timeout=10.0,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                    },
                )
                ct = head.headers.get("content-type", "")
                if ct and not _is_pdf_content_type(ct):
                    logger.warning(
                        "[projects] URL does not serve a PDF (content-type=%r) for doi=%s — skipping upload",
                        ct, doi,
                    )
                    return None, None, None
            except Exception:
                pass  # HEAD not supported by all servers — fall through to GET

            # ── Full GET ────────────────────────────────────────────────────
            resp = await client.get(
                pdf_url,
                timeout=_PDF_DOWNLOAD_TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
            )
            resp.raise_for_status()
            data = resp.content

        # ── Validate: Content-Type ──────────────────────────────────────────
        ct = resp.headers.get("content-type", "")
        if ct and not _is_pdf_content_type(ct):
            logger.warning(
                "[projects] GET response is not a PDF (content-type=%r) for doi=%s — skipping upload",
                ct, doi,
            )
            return None, None, None

        # ── Validate: PDF magic bytes (%PDF-) ───────────────────────────────
        if not _is_pdf_bytes(data):
            logger.warning(
                "[projects] Response does not have PDF magic bytes (got %r...) for doi=%s "
                "— URL likely points to an HTML abstract page, skipping upload",
                data[:20], doi,
            )
            return None, None, None

        # ── Size guard ──────────────────────────────────────────────────────
        if len(data) > _PDF_MAX_BYTES:
            logger.warning(
                "[projects] PDF too large to store (%d MB) for doi=%s",
                len(data) // 1024 // 1024, doi,
            )
            return None, None, None

        upload = await storage_service.upload_file(
            uid=uid,
            project_id=project_id,
            filename=filename,
            data=data,
            content_type="application/pdf",
        )
        logger.info("[projects] PDF stored: %s (%d bytes)", upload.storage_path, len(data))
        return upload.storage_path, upload.document_url, data

    except Exception as exc:
        logger.warning("[projects] PDF upload failed for doi=%s: %s", doi, exc)
        return None, None, None



@router.post(
    "/{project_id}/sources",
    response_model=ProjectResponse,
    summary="Add a DOI or URL source to a project",
)
async def add_source(
    project_id: str,
    body: AddSourceRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> ProjectResponse:
    """
    Adds a DOI or URL source to the project's sources array.
    """
    from datetime import datetime, timezone

    uid = user["uid"]
    source_dict = body.model_dump(exclude_none=False)
    source_dict["added_at"] = datetime.now(timezone.utc).isoformat()

    storage_path = None
    document_url = None
    pdf_bytes = None

    if body.type == "doi":
        # ── PDF auto-upload ──────────────────────────────────────────────────────
        pdf_url = body.pdf_url
        if not pdf_url and body.doi:
            try:
                from src.service.pdf_resolver import resolve_pdf
                resolved = await resolve_pdf(doi=body.doi, crossref_links=[])
                pdf_url = resolved.pdf_url
                if pdf_url:
                    source_dict["pdf_url"] = pdf_url
                    source_dict["is_open_access"] = resolved.is_open_access
                    source_dict["oa_status"] = resolved.oa_status
                    source_dict["resolved_via"] = resolved.resolved_via
            except Exception as exc:
                logger.warning("[projects] PDF resolver failed for doi=%s: %s", body.doi, exc)

        if pdf_url:
            storage_path, document_url, pdf_bytes = await _try_upload_pdf(
                uid=uid,
                project_id=project_id,
                doi=body.doi,
                pdf_url=pdf_url,
            )
            source_dict["storage_path"] = storage_path
            source_dict["document_url"] = document_url

            # Automatically ingest PDF into RAG with section-aware segmentation
            if pdf_bytes and body.doi:
                try:
                    from src.service.ingestion import ingest_pdf
                    chunks = await ingest_pdf(
                        uid=uid,
                        project_id=project_id,
                        doi=body.doi,
                        pdf_bytes=pdf_bytes,
                    )
                    logger.info(
                        "[projects] Auto-ingested %d chunks for doi=%s",
                        chunks, body.doi,
                    )
                except Exception as exc:
                    logger.warning(
                        "[projects] Auto-ingestion failed for doi=%s: %s",
                        body.doi, exc,
                    )
            
    elif body.type == "url" and body.url:
        # Scrape URL, save as txt
        text = await load_web_page(body.url)
        if text:
            # Safe filename from URL
            safe_name = re.sub(r"[^\w.\-]", "_", body.url.replace("https://", "").replace("http://", ""))[:100]
            filename = f"{safe_name}.txt"
            try:
                upload = await storage_service.upload_file(
                    uid=uid,
                    project_id=project_id,
                    filename=filename,
                    data=text.encode("utf-8"),
                    content_type="text/plain",
                )
                storage_path = upload.storage_path
                document_url = upload.document_url
                source_dict["storage_path"] = storage_path
                source_dict["document_url"] = document_url
            except Exception as exc:
                logger.warning("[projects] Failed to upload scraped text for url=%s: %s", body.url, exc)

    # ────────────────────────────────────────────────────────────────────────

    project = await project_service.add_source(
        uid=uid,
        project_id=project_id,
        source_data=source_dict,
    )

    return _require_project(project, project_id)


@router.post(
    "/{project_id}/sources/file",
    response_model=ProjectResponse,
    summary="Upload a file as a project source",
)
async def add_source_file(
    project_id: str,
    file: UploadFile = File(...),
    title: str = Form(None),
    user: dict[str, Any] = Depends(get_current_user),
) -> ProjectResponse:
    """
    Uploads a file directly (PDF, TXT, DOCX) and saves it to Firebase Storage.
    """
    from datetime import datetime, timezone
    
    uid = user["uid"]
    
    # Read file
    try:
        file_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(exc)}")
        
    if len(file_bytes) > _PDF_MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large (limit 50MB)")
        
    filename = file.filename or f"uploaded_{uuid.uuid4().hex[:8]}"
    # sanitize filename
    filename = re.sub(r"[^\w.\-]", "_", filename)
    
    try:
        upload = await storage_service.upload_file(
            uid=uid,
            project_id=project_id,
            filename=filename,
            data=file_bytes,
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(exc)}")

    source_dict = {
        "type": "file",
        "doi": None,
        "url": None,
        "filename": file.filename,
        "title": title or file.filename,
        "authors": [],
        "storage_path": upload.storage_path,
        "document_url": upload.document_url,
        "added_at": datetime.now(timezone.utc).isoformat(),
    }

    project = await project_service.add_source(
        uid=uid,
        project_id=project_id,
        source_data=source_dict,
    )
    
    return _require_project(project, project_id)



@router.delete(
    "/{project_id}/sources/{doi:path}",
    response_model=ProjectResponse,
    summary="Remove a source from a project by DOI",
)
async def remove_source(
    project_id: str,
    doi: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> ProjectResponse:
    """
    The DOI path segment is URL-decoded automatically.
    To remove a source, a full scan of the sources array is performed
    and the matching entry (by DOI) is removed via arrayRemove.
    """
    doi = unquote(doi)

    # Fetch the project first to find the exact source dict (arrayRemove needs exact match)
    existing = await project_service.get_project(uid=user["uid"], project_id=project_id)
    _require_project(existing, project_id)

    source_obj = next(
        (s.model_dump(exclude_none=False) for s in existing.sources if s.doi == doi),
        None,
    )
    if source_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with DOI '{doi}' not found in project '{project_id}'",
        )

    project = await project_service.remove_source(
        uid=user["uid"],
        project_id=project_id,
        source_data=source_obj,
    )
    return _require_project(project, project_id)
