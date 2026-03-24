from typing import Any
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    project_id: str = Field(
        ..., description="Firestore project ID to scope the vector store"
    )
    chat_id: str = Field(
        default="default", description="Chat session ID to scope the vector store"
    )
    text: str = Field(
        ..., min_length=1, description="Raw document text to chunk and embed"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata attached to each chunk (e.g. doi, title, source)",
    )


class IngestResponse(BaseModel):
    chunks_stored: int = Field(
        ..., description="Number of embedding chunks written to the vector store"
    )


class SearchRequest(BaseModel):
    project_id: str = Field(
        ..., description="Firestore project ID to scope the vector store"
    )
    chat_id: str = Field(
        default="default", description="Chat session ID to scope the vector store"
    )
    query: str = Field(..., min_length=1, description="Semantic search query")
    top_k: int = Field(3, ge=1, le=20, description="Number of top results to return")


class SearchResult(BaseModel):
    id: str
    text: str
    score: float = Field(..., description="Cosine similarity score in [−1, 1]")
    metadata: dict[str, Any] = {}
