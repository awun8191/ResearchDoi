"""
Gemini chat service.

Chat history is persisted in Firestore at:
  users/{uid}/projects/{project_id}/documents/{chat_id}
    Fields: title, createdAt, updatedAt
  users/{uid}/projects/{project_id}/documents/{chat_id}/chat_history/{message_id}
    Fields: turn_id, position, role ("user"|"model"), text, timestamp (server timestamp)

This makes history:
  - Durable across server restarts
  - Readable by any horizontal backend instance
  - Visible in Firebase Console for debugging

The Gemini function-calling loop mirrors the JS implementation:
  1. Load history from Firestore
  2. Send message with history context
  3. If model returns a function call → execute local tool → feed result back
  4. Repeat until model returns a text response
  5. Persist both user message + model reply to Firestore
"""

import logging
import time
import uuid
from typing import Any, Optional

from google import genai
from google.genai import types

from google.cloud import firestore as fs
from firebase_admin import firestore

from ..core.config import settings

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"

# ── Firestore helper ──────────────────────────────────────────────────────────


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
        logger.warning("[gemini] Could not ensure chat document metadata: %s", exc)


def _get_chat_title(uid: str, project_id: str, chat_id: str) -> Optional[str]:
    try:
        snap = _chat_doc_ref(uid, project_id, chat_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        title = data.get("title")
        return str(title) if title is not None else None
    except Exception as exc:
        logger.warning("[gemini] Could not load chat title: %s", exc)
        return None


async def _load_history(
    uid: str, project_id: str, chat_id: str
) -> list[dict[str, Any]]:
    """Load ordered chat history from Firestore as Gemini-compatible content objects."""
    try:
        col = _chat_collection(uid, project_id, chat_id)
        docs = col.order_by("timestamp").stream()
        history = []
        for doc in docs:
            d = doc.to_dict()
            history.append(
                {
                    "role": d.get("role", "user"),
                    "parts": [{"text": d.get("text", "")}],
                }
            )
        return history
    except Exception as exc:
        logger.warning("[gemini] Could not load chat history from Firestore: %s", exc)
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

            # Format timestamp to ISO string if it exists
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
        logger.warning(
            "[gemini] Could not load chat history for frontend from Firestore: %s", exc
        )
        return {"chat_id": chat_id, "title": None, "messages": []}


async def list_chat_sessions(uid: str, project_id: str) -> list[dict[str, Any]]:
    """List chat documents for a project ordered by most recently updated."""
    try:
        docs = (
            _chat_docs_collection(uid, project_id)
            .order_by(
                "updatedAt",
                direction=fs.Query.DESCENDING,
            )
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
        logger.warning("[gemini] Could not list chat sessions: %s", exc)
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

        # Deterministic IDs keep user/model order stable when timestamps are equal.
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
        logger.error("[gemini] Failed to persist chat turn to Firestore: %s", exc)


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
            "[gemini] Chat history cleared for uid=%s project=%s chat=%s",
            uid,
            project_id,
            chat_id,
        )
    except Exception as exc:
        logger.error("[gemini] Failed to clear chat history: %s", exc)


async def delete_chat_session(uid: str, project_id: str, chat_id: str) -> None:
    """
    Delete a chat thread document and all messages under its chat_history subcollection.
    """
    try:
        await _clear_history_firestore(uid, project_id, chat_id)
        _chat_doc_ref(uid, project_id, chat_id).delete()
        logger.info(
            "[gemini] Chat session deleted for uid=%s project=%s chat=%s",
            uid,
            project_id,
            chat_id,
        )
    except Exception as exc:
        logger.error("[gemini] Failed to delete chat session: %s", exc)


# ── RAG tool declaration ───────────────────────────────────────────────────────

_RAG_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_knowledge_base",
            description=(
                "Search the project's ingested document knowledge base for information "
                "relevant to the query. Use this when the user asks about specific papers, "
                "methodologies, or technical content from their uploaded sources."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="The semantic search query",
                    )
                },
                required=["query"],
            ),
        )
    ]
)


# ── RAG tool executor (calls /api/rag/search internally via service module) ───


async def _execute_rag_search(
    uid: str, project_id: str, chat_id: str, query: str
) -> str:
    """
    Called when Gemini invokes the search_knowledge_base function.
    Searches the in-process vector store scoped to the active chat session.
    """
    from .rag import rag_service  # avoid circular import at module level

    results = await rag_service.search(
        uid=uid, project_id=project_id, chat_id=chat_id, query=query, top_k=3
    )
    if not results:
        return "No relevant information found in the knowledge base for the query."

    formatted = []
    for r in results:
        title = r.metadata.get("title", "Unknown source")
        formatted.append(f"[Source: {title}]\n{r.text}")
    return "\n\n---\n\n".join(formatted)


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
    Send a message to Gemini and return the model's text reply.
    Handles the full function-calling loop for RAG tool invocations.
    History is loaded from Firestore before the call and saved after.
    """
    _ensure_chat_document(uid, project_id, chat_id, chat_title)
    history = await _load_history(uid, project_id, chat_id)

    default_system = (
        "You are a research assistant helping the user analyse and discuss academic papers. "
        "When the user asks about specific papers or technical content, use the "
        "search_knowledge_base tool to find relevant excerpts from their uploaded sources."
    )

    payload_contents: list[types.Content] = []
    for h in history:
        payload_contents.append(
            types.Content(
                role=h["role"],
                parts=[types.Part.from_text(text=h["parts"][0]["text"])],
            )
        )
    payload_contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_text)],
        )
    )

    client = genai.Client(api_key=settings.gemini_api_key)
    config = types.GenerateContentConfig(
        system_instruction=system_prompt or default_system,
        tools=[_RAG_TOOL],
    )

    model_reply_text = ""
    max_function_call_rounds = 5

    for _ in range(max_function_call_rounds):
        resp = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=payload_contents,
            config=config,
        )

        candidates = resp.candidates
        if not candidates:
            model_reply_text = "I'm sorry, I could not generate a response."
            break

        candidate = candidates[0]
        c_content = candidate.content
        c_parts = c_content.parts if c_content else None
        parts = c_parts if c_parts is not None else []

        # Check for function call
        fn_call_part = next((p for p in parts if p.function_call is not None), None)
        fn_call = fn_call_part.function_call if fn_call_part else None

        if fn_call:
            fn_name = fn_call.name or ""
            fn_args = fn_call.args or {}

            if fn_name == "search_knowledge_base":
                query_val = (
                    fn_args.get("query", "") if isinstance(fn_args, dict) else ""
                )
                tool_result = await _execute_rag_search(
                    uid, project_id, chat_id, query_val
                )
            else:
                tool_result = f"Unknown function: {fn_name}"

            # Append model's function call + our result to the payload contents
            if c_content:
                payload_contents.append(c_content)

            payload_contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=fn_name, response={"result": tool_result}
                        )
                    ],
                )
            )
            continue

        # Plain text response — we're done
        text_part = next((p for p in parts if p.text is not None), None)
        text_val = text_part.text if text_part else None
        model_reply_text = str(text_val) if text_val else "No response generated."
        break
    else:
        model_reply_text = "The maximum number of tool call rounds was reached."

    # Persist this turn to Firestore (fire-and-forget pattern, errors logged not raised)
    _save_turn(uid, project_id, chat_id, user_text, model_reply_text)

    # If caller did not set a title, derive one from the first prompt.
    current_title = _get_chat_title(uid, project_id, chat_id)
    if not current_title or current_title == "Untitled Chat":
        inferred = _chat_title_from_text(user_text)
        _ensure_chat_document(uid, project_id, chat_id, inferred)
        current_title = inferred

    return {"reply": model_reply_text, "chat_id": chat_id, "title": current_title}


async def clear_history(uid: str, project_id: str, chat_id: str) -> None:
    await _clear_history_firestore(uid, project_id, chat_id)
