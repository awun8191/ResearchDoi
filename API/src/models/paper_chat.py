from typing import Optional
from pydantic import BaseModel, Field


class PaperChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class PaperChatRequest(BaseModel):
    paper_id: str = Field(..., description="DOI or ArXiv ID of the paper")
    message: str = Field(..., min_length=1, description="The user's question about the paper")
    history: list[PaperChatMessage] = Field(
        default_factory=list,
        description="Previous conversation turns about this paper",
    )
    chat_title: Optional[str] = Field(
        None, max_length=200, description="Optional title for the chat session"
    )


class PaperChatResponse(BaseModel):
    reply: str = Field(..., description="The model's text response")
    paper_id: str = Field(..., description="The paper identifier")
    title: Optional[str] = Field(None, description="Resolved paper title")
    authors: list[str] = Field(default_factory=list, description="Paper authors")
    chat_id: str = Field(..., description="Chat session ID for history persistence")
