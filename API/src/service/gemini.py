"""
OpenRouter chat service.

Replaces the old Gemini SDK with direct OpenRouter calls using OpenAI-compatible API format.
Chat history is persisted in Firestore (to be migrated to Appwrite later).

The function-calling loop supports the `search_knowledge_base` tool for RAG.
"""

import json
import logging
import time
import uuid
from typing import Any, Optional

import httpx
from google.cloud import firestore as fs
from firebase_admin import firestore

from src.core.config import settings
from src.tools.project_state import UPDATE_THESIS_SECTION_TOOL, execute_update_thesis_section

logger = logging.getLogger(__name__)

CHAT_MODEL = settings.chat_model
OPENROUTER_BASE = settings.openrouter_base
OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {settings.openrouter_api_key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://rast-app.vercel.app",
    "X-Title": "ResearchDoi",
}

# ── Firestore helpers (keep until Appwrite migration) ─────────────────────────


def _chat_doc_ref(uid: str, project_id: str, chat_id: str):
    """Returns the Firestore document reference for a chat thread."""
    db = firestore.client()
    return (
        db.collection("users")
        .document(uid)
        .collection("projects")
        .document(project_id)
        .collection("documents")
        .document(chat_id)
    )


def _chat_docs_collection(uid: str, project_id: str):
    db = firestore.client()
    return (
        db.collection("users")
        .document(uid)
        .collection("projects")
        .document(project_id)
        .collection("documents")
    )


def _chat_collection(uid: str, project_id: str, chat_id: str):
    """Returns the Firestore collection reference for a chat thread history."""
    return _chat_doc_ref(uid, project_id, chat_id).collection("chat_history")


def _chat_title_from_text(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) <= 80:
        return compact or "Untitled Chat"
    return f"{compact[:77].rstrip()}..."


def _ts_to_iso(ts) -> Optional[str]:
    if ts is None:
        return None
    try:
        return ts.isoformat()
    except Exception:
        return str(ts)


def _ensure_chat_document(
    uid: str, project_id: str, chat_id: str, title: Optional[str]
) -> None:
    """Create the chat document if missing and optionally set/refresh title metadata."""
    try:
        ref = _chat_doc_ref(uid, project_id, chat_id)
        snap = ref.get()
        now = fs.SERVER_TIMESTAMP
        requested_title = title.strip() if title else None

        if not snap.exists:
            ref.set(
                {
                    "title": requested_title or "Untitled Chat",
                    "createdAt": now,
                    "updatedAt": now,
                }
            )
            return

        if requested_title:
            ref.set({"title": requested_title, "updatedAt": now}, merge=True)
    except Exception as exc:
        logger.warning("[openrouter] Could not ensure chat document metadata: %s", exc)


def _get_chat_title(uid: str, project_id: str, chat_id: str) -> Optional[str]:
    try:
        snap = _chat_doc_ref(uid, project_id, chat_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        title = data.get("title")
        return str(title) if title is not None else None
    except Exception as exc:
        logger.warning("[openrouter] Could not load chat title: %s", exc)
        return None


async def _load_history(
    uid: str, project_id: str, chat_id: str
) -> list[dict[str, Any]]:
    """Load ordered chat history from Firestore as OpenAI-compatible message objects."""
    try:
        col = _chat_collection(uid, project_id, chat_id)
        docs = col.order_by("timestamp").stream()
        history = []
        for doc in docs:
            d = doc.to_dict()
            role = d.get("role", "user")
            # Gemini uses 'model' role, OpenAI uses 'assistant'
            openai_role = "assistant" if role == "model" else "user"
            history.append(
                {"role": openai_role, "content": d.get("text", "")}
            )
            
        # Sliding window: keep only the last 20 messages to prevent context blowout
        return history[-20:]
    except Exception as exc:
        logger.warning("[openrouter] Could not load chat history: %s", exc)
        return []


async def get_history_firestore(
    uid: str, project_id: str, chat_id: str
) -> dict[str, Any]:
    """Load chat metadata and ordered chat history from Firestore for the frontend."""
    try:
        col = _chat_collection(uid, project_id, chat_id)
        docs = col.order_by("timestamp").stream()
        history = []
        for doc in docs:
            d = doc.to_dict()
            ts = d.get("timestamp")
            if ts:
                ts = ts.isoformat()
            history.append(
                {
                    "id": doc.id,
                    "role": d.get("role", "user"),
                    "text": d.get("text", ""),
                    "timestamp": ts,
                }
            )
        return {
            "chat_id": chat_id,
            "title": _get_chat_title(uid, project_id, chat_id),
            "messages": history,
        }
    except Exception as exc:
        logger.warning("[openrouter] Could not load chat history for frontend: %s", exc)
        return {"chat_id": chat_id, "title": None, "messages": []}


async def list_chat_sessions(uid: str, project_id: str) -> list[dict[str, Any]]:
    """List chat documents for a project ordered by most recently updated."""
    try:
        docs = (
            _chat_docs_collection(uid, project_id)
            .order_by("updatedAt", direction=fs.Query.DESCENDING)
            .stream()
        )
        sessions: list[dict[str, Any]] = []
        for doc in docs:
            d = doc.to_dict() or {}
            sessions.append(
                {
                    "chat_id": doc.id,
                    "title": d.get("title"),
                    "created_at": _ts_to_iso(d.get("createdAt")),
                    "updated_at": _ts_to_iso(d.get("updatedAt")),
                }
            )
        return sessions
    except Exception as exc:
        logger.warning("[openrouter] Could not list chat sessions: %s", exc)
        return []


def _save_turn(
    uid: str, project_id: str, chat_id: str, user_text: str, model_text: str
) -> None:
    """Persist a user/model turn to Firestore. Non-blocking — errors are logged, not raised."""
    try:
        col = _chat_collection(uid, project_id, chat_id)
        server_ts = fs.SERVER_TIMESTAMP
        turn_id = uuid.uuid4().hex
        base_ns = time.time_ns()

        user_ref = col.document(f"{base_ns:020d}_0_{turn_id}")
        model_ref = col.document(f"{base_ns + 1:020d}_1_{turn_id}")

        batch = firestore.client().batch()
        batch.set(
            user_ref,
            {
                "turn_id": turn_id,
                "position": 0,
                "role": "user",
                "text": user_text,
                "timestamp": server_ts,
            },
        )
        batch.set(
            model_ref,
            {
                "turn_id": turn_id,
                "position": 1,
                "role": "model",
                "text": model_text,
                "timestamp": server_ts,
            },
        )
        batch.commit()
    except Exception as exc:
        logger.error("[openrouter] Failed to persist chat turn to Firestore: %s", exc)


async def _clear_history_firestore(uid: str, project_id: str, chat_id: str) -> None:
    """Delete all documents in the chat_history subcollection."""
    try:
        col = _chat_collection(uid, project_id, chat_id)
        batch_size = 100
        while True:
            docs = list(col.limit(batch_size).stream())
            if not docs:
                break
            batch = firestore.client().batch()
            for doc in docs:
                batch.delete(doc.reference)
            batch.commit()
        logger.info(
            "[openrouter] Chat history cleared for uid=%s project=%s chat=%s",
            uid, project_id, chat_id,
        )
    except Exception as exc:
        logger.error("[openrouter] Failed to clear chat history: %s", exc)


async def delete_chat_session(uid: str, project_id: str, chat_id: str) -> None:
    """Delete a chat thread document and all messages under its chat_history subcollection."""
    try:
        await _clear_history_firestore(uid, project_id, chat_id)
        _chat_doc_ref(uid, project_id, chat_id).delete()
        logger.info(
            "[openrouter] Chat session deleted for uid=%s project=%s chat=%s",
            uid, project_id, chat_id,
        )
    except Exception as exc:
        logger.error("[openrouter] Failed to delete chat session: %s", exc)


async def record_external_turn(
    uid: str,
    project_id: str,
    chat_id: str,
    user_text: str,
    model_text: str,
    chat_title: Optional[str] = None,
) -> str:
    """
    Persist a turn produced outside the OpenRouter chat path.

    The project workspace uses the same Firestore chat documents for regular
    chat and ADK-agent chat, so proxy responses must create/update the session
    metadata and write the turn before the frontend refreshes history.
    """
    _ensure_chat_document(uid, project_id, chat_id, chat_title)
    _save_turn(uid, project_id, chat_id, user_text, model_text)

    current_title = _get_chat_title(uid, project_id, chat_id)
    if not current_title or current_title == "Untitled Chat":
        current_title = _chat_title_from_text(user_text)
        _ensure_chat_document(uid, project_id, chat_id, current_title)

    return current_title


# ── RAG tool declaration (OpenAI function-calling format) ────────────────────

_RAG_TOOL = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": (
            "Search the project's ingested document knowledge base for information "
            "relevant to the query. Use this when the user asks about specific papers, "
            "methodologies, or technical content from their uploaded sources."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The semantic search query",
                }
            },
            "required": ["query"],
        },
    },
}


# ── RAG tool executor ─────────────────────────────────────────────────────────


async def _execute_rag_search(
    uid: str, project_id: str, chat_id: str, query: str
) -> str:
    """Called when the model invokes search_knowledge_base."""
    from .rag import rag_service

    results = await rag_service.search(
        uid=uid, project_id=project_id, chat_id=chat_id, query=query, top_k=3
    )
    if not results:
        return "No relevant information found in the knowledge base for the query."

    formatted = []
    for r in results:
        title = r.metadata.get("title", "Unknown source")
        formatted.append(f"[Cite: {title}]\n{r.text}")
    return "\n\n---\n\n".join(formatted)


# ── OpenRouter chat completion ────────────────────────────────────────────────


async def _openrouter_chat(
    messages: list[dict[str, Any]],
    tools: Optional[list[dict]] = None,
    max_tokens: int = 8192,
) -> dict[str, Any]:
    """
    Call OpenRouter chat completions endpoint (OpenAI-compatible).
    Returns the raw response data dict.
    """
    url = f"{OPENROUTER_BASE}/chat/completions"
    payload: dict[str, Any] = {
        "model": CHAT_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=OPENROUTER_HEADERS, json=payload)
        resp.raise_for_status()
        return resp.json()


# ── Core send logic ─────────────────────────────────────────────────────────────


async def send_message(
    uid: str,
    project_id: str,
    chat_id: str,
    user_text: str,
    chat_title: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> dict[str, Any]:
    """
    Send a message to Gemma 4 31B via OpenRouter and return the model's text reply.
    Handles the full function-calling loop for RAG tool invocations.
    History is loaded from Firestore before the call and saved after.
    """
    _ensure_chat_document(uid, project_id, chat_id, chat_title)
    history = await _load_history(uid, project_id, chat_id)

    default_system = (
        "You are a research assistant helping the user analyse and discuss academic papers. "
        "When the user asks about specific papers or technical content, use the "
        "search_knowledge_base tool to find relevant excerpts from their uploaded sources. "
        "You also have access to update the thesis sections using the update_thesis_section tool. "
        "CRITICAL INSTRUCTION: When using information from the knowledge base, you MUST cite your sources deterministically using EXACTLY this format: [Cite: Source Title]. "
        "Do NOT hallucinate citations or invent your own citation formats. Only use the titles provided by the search tool."
    )
    
    # Inject thesis state to system prompt to maintain context
    from src.service import projects as project_service
    project = await project_service.get_project(uid=uid, project_id=project_id)
    if project and project.thesis:
        thesis_parts = ["\nCurrent Thesis State (Truncated for Context Window):"]
        for section_id, content in project.thesis.items():
            words = content.split()
            if len(words) > 300:
                truncated = " ".join(words[:300]) + "... [TRUNCATED]"
            else:
                truncated = content
            thesis_parts.append(f"### Section: {section_id}\n{truncated}")
        default_system += "\n".join(thesis_parts)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt or default_system}
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    model_reply_text = ""
    max_function_call_rounds = 5

    for _ in range(max_function_call_rounds):
        try:
            data = await _openrouter_chat(messages, tools=[_RAG_TOOL, UPDATE_THESIS_SECTION_TOOL])
        except Exception as exc:
            logger.error("[openrouter] API call failed: %s", exc)
            model_reply_text = "I'm sorry, I could not generate a response."
            break

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        finish_reason = choice.get("finish_reason", "stop")

        if finish_reason == "tool_calls" and message.get("tool_calls"):
            # Execute tool calls and append results
            for tool_call in message["tool_calls"]:
                fn_name = tool_call["function"]["name"]
                try:
                    fn_args = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    fn_args = {}

                if fn_name == "search_knowledge_base":
                    query_val = fn_args.get("query", "")
                    tool_result = await _execute_rag_search(
                        uid, project_id, chat_id, query_val
                    )
                elif fn_name == "update_thesis_section":
                    section_id_val = fn_args.get("section_id", "")
                    content_val = fn_args.get("content", "")
                    tool_result = await execute_update_thesis_section(
                        uid, project_id, section_id_val, content_val
                    )
                else:
                    tool_result = f"Unknown function: {fn_name}"

                # Append the model's tool call request
                messages.append(message)
                # Append the tool result
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": tool_result,
                    }
                )
            continue

        # Plain text response — we're done
        model_reply_text = message.get("content", "") or "No response generated."
        break
    else:
        model_reply_text = "The maximum number of tool call rounds was reached."

    # Persist this turn to Firestore
    _save_turn(uid, project_id, chat_id, user_text, model_reply_text)

    # Derive title from the first prompt if not set
    current_title = _get_chat_title(uid, project_id, chat_id)
    if not current_title or current_title == "Untitled Chat":
        inferred = _chat_title_from_text(user_text)
        _ensure_chat_document(uid, project_id, chat_id, inferred)
        current_title = inferred

    return {"reply": model_reply_text, "chat_id": chat_id, "title": current_title}


async def clear_history(uid: str, project_id: str, chat_id: str) -> None:
    await _clear_history_firestore(uid, project_id, chat_id)
