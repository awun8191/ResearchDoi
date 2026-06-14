import logging
from datetime import timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from firebase_admin import firestore

from src.core.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

_MAX_STREAM_WITHOUT_QUERY = 10000  # Absolute ceiling: never load more than this


def _history_ref(uid: str):
    return firestore.client().collection("users").document(uid).collection("history")


def _ts_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    try:
        dt = value.astimezone(timezone.utc) if hasattr(value, "astimezone") else value
        return dt.isoformat()
    except Exception:
        return str(value)


_TIMESTAMP_FIELDS = ("lookedUpAt", "looked_up_at", "createdAt", "created_at",
                     "timestamp", "date", "updatedAt", "updated_at")


def _extract_timestamp(data: dict[str, Any]) -> str | None:
    for field in _TIMESTAMP_FIELDS:
        if field in data and data[field] is not None:
            return _ts_to_iso(data[field])
    return None


def _normalize_authors(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        authors: list[str] = []
        for item in raw:
            if isinstance(item, str):
                value = item.strip()
                if value:
                    authors.append(value)
            elif isinstance(item, dict):
                given = str(item.get("given", "")).strip()
                family = str(item.get("family", "")).strip()
                full_name = " ".join(part for part in (given, family) if part).strip()
                if full_name:
                    authors.append(full_name)
        return authors
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(";") if part.strip()]
    return []


def _normalize_entry(doc) -> dict[str, Any]:
    data = doc.to_dict() or {}
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    authors = _normalize_authors(
        data.get("authors") or data.get("author") or metadata.get("authors")
    )
    return {
        "id": doc.id,
        "doi": str(data.get("doi") or "").strip(),
        "title": str(
            data.get("title")
            or data.get("articleTitle")
            or data.get("article_title")
            or ""
        ).strip(),
        "authors": authors,
        "date": _extract_timestamp(data),
        "url": data.get("url")
        or (
            f"https://doi.org/{data.get('doi')}"
            if data.get("doi")
            else None
        ),
        "raw": data,
    }


def _matches_search(entry: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    haystack = " ".join(
        [
            entry.get("doi", ""),
            entry.get("title", ""),
            " ".join(entry.get("authors", [])),
        ]
    ).lower()
    return query.lower() in haystack


@router.get("", summary="List DOI history for the current user")
async def list_history(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, max_length=200),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    List DOI lookup history with server-side pagination.

    **Without search query (`q` empty):** Fully server-side paginated via
    Firestore `.offset().limit()`. Fast and memory-efficient.

    **With search query (`q` set):** Falls back to streaming and client-side
    filtering capped at _MAX_STREAM_WITHOUT_QUERY entries for search support.
    """
    query = (q or "").strip()
    uid = user["uid"]

    try:
        if not query:
            # ── Fast path: fully server-side paginated ─────────────────
            docs_raw = (
                _history_ref(uid)
                .order_by("lookedUpAt", direction=firestore.Query.DESCENDING)
                .offset(offset)
                .limit(limit)
                .stream()
            )
            items = [_normalize_entry(doc) for doc in docs_raw]

            # Count total (lightweight — Firestore collection size estimate)
            total = 0
            try:
                count_snapshot = _history_ref(uid).count().get()
                total = count_snapshot[0].value if count_snapshot else 0
            except Exception as exc:
                logger.debug("[history] Count fallback: %s", exc)
                total = offset + len(items)

            return {
                "items": items,
                "total": total,
                "limit": limit,
                "offset": offset,
                "query": None,
            }

        # ── Slow path: search with client-side filter ─────────────────
        docs_raw = _history_ref(uid).stream()
        all_entries = []
        for i, doc in enumerate(docs_raw):
            if i >= _MAX_STREAM_WITHOUT_QUERY:
                break
            all_entries.append(_normalize_entry(doc))

        filtered = [e for e in all_entries if _matches_search(e, query)]
        filtered.sort(key=lambda e: e.get("date") or "", reverse=True)
        page = filtered[offset : offset + limit]

        return {
            "items": page,
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
            "query": query or None,
        }

    except Exception as exc:
        logger.error("[history] Failed to load history for uid=%s: %s", uid, exc)
        return {"items": [], "total": 0, "limit": limit, "offset": offset, "query": query or None}
