"""
Firebase Storage service.

Uses the firebase-admin SDK with download tokens for permanent, non-expiring URLs.

Download token URLs take the form:
  https://firebasestorage.googleapis.com/v0/b/{bucket}/o/{encoded_path}?alt=media&token={uuid}

The token is a UUID generated at upload time and stored in the blob's metadata.
Tokens are permanent (no expiry) and can be revoked via Firebase Console or Admin SDK.

Path convention (enforced by this service, not by Storage rules):
  users/{uid}/projects/{project_id}/{filename}

This ensures each user's files are isolated. The UID comes from the verified
Firebase auth token — users cannot craft a path to another user's files.
"""

import logging
import uuid
from urllib.parse import quote

from firebase_admin import storage

from src.models.storage import StorageUrlResponse, UploadResponse

logger = logging.getLogger(__name__)


def _make_storage_path(uid: str, project_id: str, filename: str) -> str:
    return f"users/{uid}/projects/{project_id}/{filename}"


def _build_download_url(bucket_name: str, storage_path: str, token: str) -> str:
    """
    Construct the non-expiring Firebase Storage download URL.
    The path must be URL-encoded (slashes → %2F) for the REST URL format.
    """
    encoded_path = quote(storage_path, safe="")
    return (
        f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}"
        f"/o/{encoded_path}?alt=media&token={token}"
    )


async def upload_file(
    uid: str,
    project_id: str,
    filename: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> UploadResponse:
    """
    Upload file bytes to Firebase Storage and return a non-expiring download URL.

    A unique download token (UUID4) is attached as blob metadata so the URL
    never expires. It can be revoked by deleting the token via Firebase Console.
    """
    storage_path = _make_storage_path(uid, project_id, filename)
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)

    download_token = str(uuid.uuid4())

    blob.upload_from_string(
        data,
        content_type=content_type,
        # Attach the download token as custom metadata
        # firebase-admin will merge this into the blob's Firebase metadata
    )

    # Patch metadata to attach the download token (Firebase uses this field name exactly)
    blob.metadata = {"firebaseStorageDownloadTokens": download_token}
    blob.patch()

    document_url = _build_download_url(bucket.name, storage_path, download_token)

    logger.info(
        "[storage] Uploaded %s bytes → %s (uid=%s project=%s)",
        len(data),
        storage_path,
        uid,
        project_id,
    )

    return UploadResponse(
        storage_path=storage_path,
        document_url=document_url,
        filename=filename,
        size_bytes=len(data),
    )


async def get_download_url(uid: str, project_id: str, filename: str) -> StorageUrlResponse:
    """
    Retrieve the download URL for an existing blob.
    Reads the firebaseStorageDownloadTokens metadata field from the blob.
    """
    storage_path = _make_storage_path(uid, project_id, filename)
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)

    blob.reload()  # Fetch current metadata
    metadata = blob.metadata or {}
    token = metadata.get("firebaseStorageDownloadTokens")

    if not token:
        # Fallback: generate a new token and patch it
        token = str(uuid.uuid4())
        blob.metadata = {"firebaseStorageDownloadTokens": token}
        blob.patch()
        logger.warning("[storage] No download token found for %s — generated new one", storage_path)

    document_url = _build_download_url(bucket.name, storage_path, token)
    return StorageUrlResponse(storage_path=storage_path, document_url=document_url)


async def delete_file(uid: str, project_id: str, filename: str) -> None:
    """Delete a blob from Firebase Storage."""
    storage_path = _make_storage_path(uid, project_id, filename)
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)

    try:
        blob.delete()
        logger.info("[storage] Deleted %s", storage_path)
    except Exception as exc:
        logger.error("[storage] Failed to delete %s: %s", storage_path, exc)
        raise
