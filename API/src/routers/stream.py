import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.core.dependencies import get_current_user
from src.service import projects as project_service

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory pubsub for JSON patch streams
# project_id -> list of queues
_streams: Dict[str, list[asyncio.Queue]] = {}


async def subscribe(project_id: str) -> asyncio.Queue:
    if project_id not in _streams:
        _streams[project_id] = []
    q = asyncio.Queue()
    _streams[project_id].append(q)
    return q


def unsubscribe(project_id: str, q: asyncio.Queue) -> None:
    if project_id in _streams:
        if q in _streams[project_id]:
            _streams[project_id].remove(q)
        if not _streams[project_id]:
            del _streams[project_id]


async def publish(project_id: str, patch: dict[str, Any]) -> None:
    if project_id in _streams:
        for q in _streams[project_id]:
            await q.put(patch)


@router.get("/{project_id}", summary="SSE stream for project state JSON patches")
async def stream_project_state(
    project_id: str,
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    """
    Server-Sent Events endpoint that streams JSON Patch updates for the project state.
    """
    project = await project_service.get_project(uid=user["uid"], project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    q = await subscribe(project_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                # Wait for next patch with a small timeout to check disconnection
                try:
                    patch = await asyncio.wait_for(q.get(), timeout=1.0)
                    yield f"data: {json.dumps(patch)}\n\n"
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe(project_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
