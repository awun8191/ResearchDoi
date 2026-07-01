import pytest
from src.tools.project_state import execute_update_thesis_section
from src.routers.stream import subscribe

@pytest.mark.asyncio
async def test_execute_update_thesis_section(mocker):
    # Mock firestore
    mock_db = mocker.patch("src.tools.project_state.firestore.client")
    mock_ref = mock_db.return_value.collection.return_value.document.return_value.collection.return_value.document.return_value
    
    mock_snap = mocker.Mock()
    mock_snap.exists = True
    mock_ref.get.return_value = mock_snap

    project_id = "test-project-999"
    q = await subscribe(project_id)
    
    # Execute the tool
    res = await execute_update_thesis_section("uid", project_id, "intro", "Hello Intro")
    assert '"status": "success"' in res
    
    # Verify firestore set called
    mock_ref.set.assert_called_once()
    
    # Verify stream got patch
    patch = await q.get()
    assert patch["op"] == "replace"
    assert patch["path"] == "/thesis/intro"
    assert patch["value"] == "Hello Intro"
