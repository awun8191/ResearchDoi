import logging
from typing import Any

from firebase_admin import firestore
from src.routers.stream import publish

logger = logging.getLogger(__name__)

# ADK/OpenAI-compatible Tool Definition
UPDATE_THESIS_SECTION_TOOL = {
    "type": "function",
    "function": {
        "name": "update_thesis_section",
        "description": "Updates a specific section of the thesis outline. Uses JSON patch semantics to modify the project's thesis state.",
        "parameters": {
            "type": "object",
            "properties": {
                "section_id": {
                    "type": "string",
                    "description": "The ID or name of the section to update (e.g. 'literature_review', 'methodology')"
                },
                "content": {
                    "type": "string",
                    "description": "The new Markdown content for this section"
                }
            },
            "required": ["section_id", "content"]
        }
    }
}


async def execute_update_thesis_section(uid: str, project_id: str, section_id: str, content: str) -> str:
    """
    Executes the thesis section update:
    1. Updates Firestore document.
    2. Emits a JSON patch to the SSE stream.
    Returns a success message or an error string for the LLM to retry.
    """
    try:
        # 1. Update Firestore
        db = firestore.client()
        ref = db.collection("users").document(uid).collection("projects").document(project_id)
        
        snap = ref.get()
        if not snap.exists:
            return '{"error": "Project not found"}'
            
        # Update the specific section
        ref.set({
            "thesis": {
                section_id: content
            },
            "updatedAt": firestore.SERVER_TIMESTAMP
        }, merge=True)
        
        # 2. Emit JSON Patch
        patch = {
            "op": "replace",
            "path": f"/thesis/{section_id}",
            "value": content
        }
        await publish(project_id, patch)
        
        return '{"status": "success"}'
        
    except Exception as exc:
        logger.error("Failed to update thesis section: %s", exc)
        return f'{{"error": "Failed to update thesis section: {str(exc)}"}}'
