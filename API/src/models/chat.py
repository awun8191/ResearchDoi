from typing import Optional
from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    project_id: str = Field(..., description="The Firestore project document ID")
    chat_id: str = Field(
        default="default",
        min_length=1,
        description="Chat thread document ID under projects/{project_id}/documents/{chat_id}",
    )
    message: str = Field(..., min_length=1, description="The user's message text")
    chat_title: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional title for the chat thread (stored on the chat document).",
    )
    system_prompt: Optional[str] = Field(
        None,
        description="Project-level instructions to inject as the system prompt. "
                    "Typically project.instructions from Firestore.",
    )


class ChatMessageResponse(BaseModel):
    reply: str = Field(..., description="The model's text response")
    chat_id: str = Field(..., description="The chat thread ID")
    title: Optional[str] = Field(None, description="The chat thread title")


class ClearChatRequest(BaseModel):
    project_id: str = Field(..., description="The project whose chat history should be cleared")
    chat_id: str = Field(
        default="default",
        min_length=1,
        description="Chat thread document ID under projects/{project_id}/documents/{chat_id}",
    )


class ChatMessageItem(BaseModel):
    id: str = Field(..., description="The message document ID")
    role: str = Field(..., description="The role of the message sender ('user' or 'model')")
    text: str = Field(..., description="The content of the message")
    timestamp: Optional[str] = Field(None, description="The timestamp of the message")


class ChatHistoryResponse(BaseModel):
    chat_id: str = Field(..., description="The chat thread ID")
    title: Optional[str] = Field(None, description="The chat thread title")
    messages: list[ChatMessageItem] = Field(description="List of ordered chat messages for a project")


class ChatSessionItem(BaseModel):
    chat_id: str = Field(..., description="The chat thread ID")
    title: Optional[str] = Field(None, description="The chat thread title")
    created_at: Optional[str] = Field(None, description="ISO-8601 created timestamp")
    updated_at: Optional[str] = Field(None, description="ISO-8601 updated timestamp")


class ChatSessionsResponse(BaseModel):
    sessions: list[ChatSessionItem] = Field(description="All chat threads for a project")
