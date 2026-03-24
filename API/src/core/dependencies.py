from typing import Any
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.core.config import settings

# X-Api-Key header scheme — shown in /docs Swagger UI
_api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)

# Mock user injected in development mode
_DEV_USER: dict[str, Any] = {
    "uid": "dev-user",
    "email": "dev@localhost",
}


async def get_current_user(
    api_key: str | None = Security(_api_key_header),
    user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, Any]:
    """
    FastAPI dependency that authenticates requests via a static API key.

    - DEVELOPMENT (APP_ENV=development):
        No key required. Returns a stable mock user so every endpoint works
        out of the box with curl or the dev frontend.

    - PRODUCTION (APP_ENV=production):
        Every request must include the header:
            X-Api-Key: <your_api_key>
        Returns 403 if the key is missing or incorrect.

    Firebase Admin SDK is still used for Firestore + Storage operations,
    but it is no longer involved in per-request authentication.
    """
    if settings.is_development:
        if user_id:
            return {"uid": user_id, "email": "dev@localhost"}
        return _DEV_USER

    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key. Provide it in the X-Api-Key header.",
        )

    # If provided, trust a forwarded user id to keep API writes aligned with
    # client Firestore user paths. Otherwise, use the single-tenant fallback.
    if user_id:
        return {"uid": user_id, "email": "api@researchdoi"}
    return {"uid": "api-key-user", "email": "api@researchdoi"}
