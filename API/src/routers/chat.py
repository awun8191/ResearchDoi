# Chat router for ResearchDoi
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from src.core.dependencies import get_current_user
from src.models.chat import (
    ChatHistoryResponse,
    ChatMessageItem,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionItem,
    ChatSessionsResponse,
    ClearChatRequest,
)
from src.models.project import ProjectResponse
from src.core.config import settings
from src.service import gemini as gemini_service
from src.service import projects as project_service

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
    return ChatSessionsResponse(
        sessions=[ChatSessionItem(**session) for session in sessions]
    )


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
    messages = [
        ChatMessageItem(**message)
        for message in history.get("messages", [])
        if isinstance(message, dict)
    ]
    return ChatHistoryResponse(
        chat_id=str(history.get("chat_id", chat_id)),
        title=history.get("title")
        if isinstance(history.get("title"), str) or history.get("title") is None
        else None,
        messages=messages,
    )


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

    return ChatMessageResponse(
        reply=reply.get("reply", ""),
        chat_id=str(reply.get("chat_id", body.chat_id)),
        title=reply.get("title")
        if isinstance(reply.get("title"), str) or reply.get("title") is None
        else None,
    )


class AgentMessageRequest(BaseModel):
    project_id: str
    chat_id: str = Field(default="default", min_length=1)
    message: str = Field(..., min_length=1)


class AgentMessageResponse(ChatMessageResponse):
    agent_response: dict[str, Any] | list[Any]


def _build_agent_context(project: ProjectResponse) -> str:
    context_parts = [
        f"You are operating in Project '{project.name}'.",
    ]
    if project.instructions:
        context_parts.append(f"Project instructions: {project.instructions}")
    return f"[System Context: {' '.join(context_parts)}]\n\n"


def _extract_text_from_parts(parts: Any) -> str:
    if not isinstance(parts, list):
        return ""

    text_chunks: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str) and text:
            text_chunks.append(text)
    return " ".join(text_chunks)



def _extract_tool_calls(data: Any) -> list[dict[str, Any]]:
    tool_calls = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("type") == "tool_call":
                tc = item.get("tool_call", {})
                if tc:
                    tool_calls.append({
                        "name": tc.get("name", "unknown_tool"),
                        "args": tc.get("arguments", {})
                    })
            # Also handle ADK event format if different
            if isinstance(item, dict) and "tool_name" in item:
                tool_calls.append({
                    "name": item.get("tool_name"),
                    "args": item.get("tool_args", {})
                })
    return tool_calls

def _extract_agent_reply(data: Any) -> str:

    if isinstance(data, dict):
        content = data.get("content")
        if isinstance(content, dict) and content.get("role") == "model":
            return _extract_text_from_parts(content.get("parts"))
        return ""

    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, dict) and content.get("role") == "model":
                reply_text = _extract_text_from_parts(content.get("parts"))
                if reply_text:
                    return reply_text

    return ""


def _build_upstream_error_detail(prefix: str, response: httpx.Response) -> str:
    body_text = response.text.strip()
    if not body_text:
        return prefix
    return f"{prefix}: {body_text[:500]}"


@router.post(
    "/agent/message",
    response_model=AgentMessageResponse,
    summary="Send a message to the ADK agent",
)
async def send_agent_message(
    body: AgentMessageRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> AgentMessageResponse:
    """
    Proxy endpoint to send messages to the deployed ADK agent.
    This avoids CORS issues by routing through our backend.
    Injects project context so the agent knows about its workspace.
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

    enriched_message = (
        f"{_build_agent_context(project)}User Message: {message}"
    )

    session_url = (
        f"{settings.agent_base_url}/apps/{AGENT_APP_NAME}/users/{user_id}/sessions/{chat_id}"
    )
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

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            session_response = await client.post(session_url, json={})
            if session_response.status_code not in {
                status.HTTP_200_OK,
                status.HTTP_201_CREATED,
                status.HTTP_409_CONFLICT,
            }:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=_build_upstream_error_detail(
                        "Agent session initialization failed",
                        session_response,
                    ),
                )

            response = await client.post(run_url, json=payload)
        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=_build_upstream_error_detail("Agent request failed", response),
            )
    except httpx.HTTPError as exc:
        logger.error("[chat_router] Agent request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach the agent service",
        ) from exc

    try:
        data = response.json()
    except ValueError as exc:
        logger.error("[chat_router] Agent returned invalid JSON: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent service returned invalid JSON",
        ) from exc

    if not isinstance(data, (dict, list)):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent service returned an unexpected response shape",
        )


    return AgentMessageResponse(
        reply=_extract_agent_reply(data),
        chat_id=chat_id,
        title=None,
        agent_response={
            "raw": data,
            "tool_calls": _extract_tool_calls(data)
        },
    )



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
