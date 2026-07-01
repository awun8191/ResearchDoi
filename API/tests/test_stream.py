import asyncio
import pytest
from src.routers.stream import subscribe, unsubscribe, publish

@pytest.mark.asyncio
async def test_pubsub_stream():
    project_id = "test-project-123"
    
    # 1. Subscribe
    q = await subscribe(project_id)
    assert q is not None
    
    # 2. Publish
    patch = {"op": "replace", "path": "/thesis/intro", "value": "Hello world"}
    await publish(project_id, patch)
    
    # 3. Receive
    received_patch = await asyncio.wait_for(q.get(), timeout=1.0)
    assert received_patch == patch
    
    # 4. Unsubscribe
    unsubscribe(project_id, q)
    
    # Verify no queues left for this project
    from src.routers.stream import _streams
    assert project_id not in _streams
