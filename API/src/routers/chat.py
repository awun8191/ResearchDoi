# Chat router for ResearchDoi
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from pydantic import BaseModel
from src.core.dependencies import get_current_user
from src.models.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ClearChatRequest,
    ChatHistoryResponse,
    ChatSessionsResponse,
)
from src.service import gemini as gemini_service
from src.service import projects as project_service
from src.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# AGENT_BASE_URL = "https://rast-agent-881013919729.us-central1.run.app"
AGENT_APP_NAME = "src"


@router.get(
    "/sessions/{project_id}",
    response_model=ChatSessionsResponse,
    summary="List chat sessions for a project",
)
async def list_sessions(
    project_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> ChatSessionsResponse:
    sessions = await gemini_service.list_chat_sessions(
        uid=user["uid"], project_id=project_id
    )
    return ChatSessionsResponse(sessions=sessions)


@router.delete(
    "/sessions/{project_id}/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session for a project",
)
async def delete_session(
    project_id: str,
    chat_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    await gemini_service.delete_chat_session(
        uid=user["uid"],
        project_id=project_id,
        chat_id=chat_id,
    )


@router.get(
    "/session/{project_id}",
    response_model=ChatHistoryResponse,
    summary="Get the chat history for a project",
)
async def get_session(
    project_id: str,
    chat_id: str = "default",
    user: dict[str, Any] = Depends(get_current_user),
) -> ChatHistoryResponse:
    """
    Retrieves the ordered chat history from Firestore for a given project/chat thread.
    """
    history = await gemini_service.get_history_firestore(
        uid=user["uid"],
        project_id=project_id,
        chat_id=chat_id,
    )
    return ChatHistoryResponse(**history)


@router.post(
    "/message",
    response_model=ChatMessageResponse,
    summary="Send a message in the project's chat session",
)
async def send_message(
    body: ChatMessageRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> ChatMessageResponse:
    """
    Send a user message to Gemini 2.5 Flash and receive a response.

    - History is loaded from Firestore before the call and saved after.
    - If the model invokes the `search_knowledge_base` tool, the RAG service
      is queried and the result fed back before a final text reply is generated.
    - `system_prompt` overrides the default assistant prompt (use project.instructions).
    """
    try:
        reply = await gemini_service.send_message(
            uid=user["uid"],
            project_id=body.project_id,
            chat_id=body.chat_id,
            user_text=body.message,
            chat_title=body.chat_title,
            system_prompt=body.system_prompt,
        )
    except Exception as exc:
        logger.error("[chat_router] Gemini call failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to get response from Gemini: {str(exc)}",
        )

    return ChatMessageResponse(**reply)


class AgentMessageRequest(BaseModel):
    project_id: str
    chat_id: str
    message: str

@router.post(
    "/agent/message",
    summary="Send a message to the ADK agent",
)
async def send_agent_message(
    body: AgentMessageRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Proxy endpoint to send messages to the deployed ADK agent.
    This avoids CORS issues by routing through our backend.
    Injects project context and corpus_id so the agent knows about its workspace.
    """
    user_id = user["uid"]
    project_id = body.project_id
    chat_id = body.chat_id
    message = body.message

    # Fetch project details for context injection
    project = await project_service.get_project(uid=user_id, project_id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
        
    context_prefix = f"[System Context: You are operating in Project '{project.name}'."
    if project.corpus_id:
        context_prefix += f" Your dedicated Knowledge Base Corpus ID is '{project.corpus_id}'. ALWAYS pass this exact corpus_id to your knowledge base tools (rag_query, add_document_to_corpus)."
    if project.instructions:
        context_prefix += f" Project instructions: {project.instructions}"
    context_prefix += "] \n\n"

    enriched_message = f"{context_prefix}User Message: {message}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Create or get session
        session_url = (
            f"{settings.agent_base_url}/apps/{AGENT_APP_NAME}/users/{user_id}/sessions/{chat_id}"
        )
        await client.post(session_url, json={})

        # Send message
        run_url = f"{settings.agent_base_url}/run"
        payload = {
            "app_name": AGENT_APP_NAME,
            "user_id": user_id,
            "session_id": chat_id,
            "new_message": {
                "role": "user",
                "parts": [{"text": enriched_message}],
            },
        }

        response = await client.post(run_url, json=payload)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Agent request failed: {response.text}",
            )

        data = response.json()

        # Extract the model's response text
        reply_text = ""
        if isinstance(data, list):
            for item in data:
                if item.get("content", {}).get("role") == "model":
                    parts = item.get("content", {}).get("parts", [])
                    reply_text = " ".join(p.get("text", "") for p in parts)
                    break
        elif isinstance(data, dict):
            if data.get("content", {}).get("role") == "model":
                parts = data.get("content", {}).get("parts", [])
                reply_text = " ".join(p.get("text", "") for p in parts)

        return {
            "reply": reply_text,
            "chat_id": chat_id,
            "title": None,
            "agent_response": data,
        }


@router.delete(
    "/session",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear the chat history for a project",
)
async def clear_session(
    body: ClearChatRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """
    Deletes all messages in `users/{uid}/projects/{project_id}/documents/{chat_id}/chat_history`.
    This is irreversible.
    """
    await gemini_service.clear_history(
        uid=user["uid"],
        project_id=body.project_id,
        chat_id=body.chat_id,
    )
