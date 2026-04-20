"""
Projects service — Firestore CRUD operations.

Firestore path: users/{uid}/projects/{project_id}

Document shape:
  {
    name:         str,
    instructions: str,
    sources:      list[dict],   # DOI entries
    createdAt:    Timestamp,
    updatedAt:    Timestamp,
  }

Timestamps are converted to ISO-8601 strings when serialised so they
pass cleanly through Pydantic / JSON without requiring a custom encoder.
"""

import logging
from datetime import timezone
from typing import Any

from firebase_admin import firestore

from src.models.project import ProjectResponse, SourceItem

logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _db() -> Any:
    return firestore.client()


def _projects_ref(uid: str):
    return _db().collection("users").document(uid).collection("projects")


def _project_ref(uid: str, project_id: str):
    return _projects_ref(uid).document(project_id)


def _ts_to_iso(ts) -> str | None:
    """Convert a Firestore Timestamp (or None) to an ISO-8601 string."""
    if ts is None:
        return None
    try:
        dt = ts.astimezone(timezone.utc) if hasattr(ts, "astimezone") else ts
        return dt.isoformat()
    except Exception:
        return str(ts)


def _doc_to_project(snap) -> ProjectResponse:
    data = snap.to_dict() or {}
    raw_sources = data.get("sources", [])

    sources: list[SourceItem] = []
    for s in raw_sources:
        try:
            sources.append(SourceItem(**s))
        except Exception:
            logger.warning("[projects] Skipping malformed source entry: %s", s)

    return ProjectResponse(
        id=snap.id,
        name=data.get("name", ""),
        instructions=data.get("instructions", ""),
        sources=sources,
        created_at=_ts_to_iso(data.get("createdAt")),
        updated_at=_ts_to_iso(data.get("updatedAt")),
    )


# ── Operations ────────────────────────────────────────────────────────────────

async def list_projects(uid: str) -> list[ProjectResponse]:
    """Return all projects for a user, ordered newest-first."""
    snaps = (
        _projects_ref(uid)
        .order_by("createdAt", direction=firestore.Query.DESCENDING)
        .stream()
    )
    return [_doc_to_project(s) for s in snaps]


async def get_project(uid: str, project_id: str) -> ProjectResponse | None:
    snap = _project_ref(uid, project_id).get()
    if not snap.exists:
        return None
    return _doc_to_project(snap)


async def create_project(uid: str, name: str, instructions: str = "") -> ProjectResponse:
    now = firestore.SERVER_TIMESTAMP

    ref = _projects_ref(uid).add({
        "name": name,
        "instructions": instructions,
        "sources": [],
        "createdAt": now,
        "updatedAt": now,
    })[1]  # add() returns (Timestamp, DocumentReference)

    snap = ref.get()
    return _doc_to_project(snap)


async def update_project(
    uid: str,
    project_id: str,
    name: str | None,
    instructions: str | None,
) -> ProjectResponse | None:
    ref = _project_ref(uid, project_id)
    snap = ref.get()
    if not snap.exists:
        return None

    patch: dict[str, Any] = {"updatedAt": firestore.SERVER_TIMESTAMP}
    if name is not None:
        patch["name"] = name
    if instructions is not None:
        patch["instructions"] = instructions

    ref.update(patch)
    return _doc_to_project(ref.get())


async def delete_project(uid: str, project_id: str) -> bool:
    """Returns True if the document existed and was deleted, False if not found."""
    ref = _project_ref(uid, project_id)
    snap = ref.get()
    if not snap.exists:
        return False

    ref.delete()
    return True


# ── Sources ───────────────────────────────────────────────────────────────────

async def add_source(uid: str, project_id: str, source_data: dict) -> ProjectResponse | None:
    """
    Atomically append a source entry to the project's sources array.
    Uses arrayUnion so concurrent adds are safe and duplicate DOIs are
    naturally de-duplicated by Firestore's set semantics.
    """
    ref = _project_ref(uid, project_id)
    if not ref.get().exists:
        return None

    ref.update({
        "sources": firestore.ArrayUnion([source_data]),
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })
    return _doc_to_project(ref.get())


async def remove_source(uid: str, project_id: str, source_data: dict) -> ProjectResponse | None:
    """
    Atomically remove a source entry from the project's sources array.
    The source_data dict must match the stored entry exactly for arrayRemove to work.
    """
    ref = _project_ref(uid, project_id)
    if not ref.get().exists:
        return None

    ref.update({
        "sources": firestore.ArrayRemove([source_data]),
        "updatedAt": firestore.SERVER_TIMESTAMP,
    })
    return _doc_to_project(ref.get())
