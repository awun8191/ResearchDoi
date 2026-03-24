import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from src.core.dependencies import get_current_user
from src.models.storage import StorageUrlResponse, UploadResponse
from src.service import storage as storage_service

logger = logging.getLogger(__name__)
router = APIRouter()

# 50 MB upload limit
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload a file to Firebase Storage",
)
async def upload_file(
    file: UploadFile = File(..., description="The file to upload (PDF, etc.)"),
    project_id: str = Form(..., description="Firestore project ID this file belongs to"),
    user: dict[str, Any] = Depends(get_current_user),
) -> UploadResponse:
    """
    Upload a file to Firebase Storage under `users/{uid}/projects/{project_id}/{filename}`.

    Returns a non-expiring Firebase download token URL — no expiry, permanently accessible
    to anyone with the link (revocable via Firebase Console).

    Max file size: 50 MB.
    """
    data = await file.read()

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the 50 MB limit ({len(data) / 1024 / 1024:.1f} MB uploaded)",
        )

    filename = file.filename or "upload"

    return await storage_service.upload_file(
        uid=user["uid"],
        project_id=project_id,
        filename=filename,
        data=data,
        content_type=file.content_type or "application/octet-stream",
    )


@router.get(
    "/url",
    response_model=StorageUrlResponse,
    summary="Get the download URL for an uploaded file",
)
async def get_file_url(
    project_id: str,
    filename: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> StorageUrlResponse:
    """
    Retrieve the non-expiring download URL for an existing file in Firebase Storage.
    The uid from the auth token is used to construct the path — users cannot access
    another user's files.
    """
    try:
        return await storage_service.get_download_url(
            uid=user["uid"],
            project_id=project_id,
            filename=filename,
        )
    except Exception as exc:
        logger.error("[storage_router] Could not retrieve URL: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {filename}",
        )


@router.delete(
    "/file",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file from Firebase Storage",
)
async def delete_file(
    project_id: str,
    filename: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """Delete a file from Firebase Storage. This is irreversible."""
    try:
        await storage_service.delete_file(
            uid=user["uid"],
            project_id=project_id,
            filename=filename,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not delete file: {exc}",
        )
