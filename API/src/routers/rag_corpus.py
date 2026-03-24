"""
Vertex AI RAG Corpus management endpoints.

This module provides API endpoints for creating and managing Vertex AI RAG corpora.
Each project can have its own corpus for storing and querying documents.
"""

import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.core.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Vertex AI Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "researchassistant-3446d")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Initialize Vertex AI lazily
_vertexai_initialized = False


def _init_vertexai():
    global _vertexai_initialized
    if _vertexai_initialized:
        return

    try:
        from vertexai import rag
        import vertexai

        vertexai.init(project=PROJECT_ID, location=LOCATION)
        _vertexai_initialized = True
        logger.info(
            f"Vertex AI RAG initialized with project={PROJECT_ID}, location={LOCATION}"
        )
    except Exception as e:
        logger.warning(f"Failed to initialize Vertex AI RAG: {e}")
        raise


class CreateCorpusRequest(BaseModel):
    display_name: str = Field(..., description="Display name for the corpus")
    description: Optional[str] = Field(None, description="Description of the corpus")


class CreateCorpusResponse(BaseModel):
    corpus_id: str
    display_name: str
    name: str


class AddDocumentRequest(BaseModel):
    gcs_uri: str = Field(..., description="Google Cloud Storage URI of the document")
    display_name: str = Field(..., description="Display name for the document")


class AddDocumentResponse(BaseModel):
    success: bool
    message: str


class ListCorporaResponse(BaseModel):
    corpora: list[dict[str, Any]]


class CorpusInfoResponse(BaseModel):
    corpus_id: str
    display_name: str
    description: Optional[str]
    create_time: str
    update_time: str
    document_count: int = 0


@router.post(
    "/corpora",
    response_model=CreateCorpusResponse,
    summary="Create a new Vertex AI RAG corpus",
)
async def create_corpus(
    body: CreateCorpusRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> CreateCorpusResponse:
    """
    Create a new Vertex AI RAG corpus for storing and querying documents.
    Each corpus can hold multiple documents and is used for RAG queries.
    """
    try:
        _init_vertexai()
        from vertexai import rag

        corpus = rag.create_corpus(
            display_name=body.display_name,
            description=body.description or f"Corpus for {body.display_name}",
        )

        # Extract corpus ID from the full name
        corpus_id = corpus.name.split("/")[-1]

        logger.info(f"Created corpus {corpus_id} for user {user['uid']}")

        return CreateCorpusResponse(
            corpus_id=corpus_id,
            display_name=corpus.display_name,
            name=corpus.name,
        )

    except Exception as exc:
        logger.error(f"Failed to create corpus: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create corpus: {str(exc)}",
        )


@router.get(
    "/corpora",
    response_model=ListCorporaResponse,
    summary="List all Vertex AI RAG corpora",
)
async def list_corpora(
    user: dict[str, Any] = Depends(get_current_user),
) -> ListCorporaResponse:
    """
    List all available Vertex AI RAG corpora in the project.
    """
    try:
        _init_vertexai()
        from vertexai import rag

        corpora = rag.list_corpora()

        corpus_list = []
        for c in corpora:
            corpus_id = c.name.split("/")[-1]
            corpus_list.append(
                {
                    "corpus_id": corpus_id,
                    "display_name": c.display_name,
                    "description": c.description,
                    "name": c.name,
                }
            )

        return ListCorporaResponse(corpora=corpus_list)

    except Exception as exc:
        logger.error(f"Failed to list corpora: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list corpora: {str(exc)}",
        )


@router.get(
    "/corpora/{corpus_id}",
    response_model=CorpusInfoResponse,
    summary="Get information about a corpus",
)
async def get_corpus_info(
    corpus_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> CorpusInfoResponse:
    """
    Get detailed information about a specific RAG corpus.
    """
    try:
        _init_vertexai()
        from vertexai import rag

        corpus = rag.get_corpus(
            name=f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{corpus_id}"
        )

        # Get document count
        documents = list(
            rag.list_documents(
                corpus_id=f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{corpus_id}"
            )
        )

        return CorpusInfoResponse(
            corpus_id=corpus_id,
            display_name=corpus.display_name,
            description=corpus.description,
            create_time=str(corpus.create_time) if corpus.create_time else "",
            update_time=str(corpus.update_time) if corpus.update_time else "",
            document_count=len(documents),
        )

    except Exception as exc:
        logger.error(f"Failed to get corpus info: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get corpus info: {str(exc)}",
        )


@router.delete(
    "/corpora/{corpus_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a corpus",
)
async def delete_corpus(
    corpus_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """
    Delete a Vertex AI RAG corpus and all its documents.
    This action cannot be undone.
    """
    try:
        _init_vertexai()
        from vertexai import rag

        rag.delete_corpus(
            name=f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{corpus_id}"
        )

        logger.info(f"Deleted corpus {corpus_id}")

    except Exception as exc:
        logger.error(f"Failed to delete corpus: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete corpus: {str(exc)}",
        )


@router.post(
    "/corpora/{corpus_id}/documents",
    response_model=AddDocumentResponse,
    summary="Add a document to a corpus",
)
async def add_document_to_corpus(
    corpus_id: str,
    body: AddDocumentRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> AddDocumentResponse:
    """
    Add a document to a RAG corpus from Google Cloud Storage.
    The document will be processed and indexed for semantic search.
    """
    try:
        _init_vertexai()
        from vertexai import rag

        # Import the document
        rag.import_files(
            rag_corpus=f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{corpus_id}",
            paths=[body.gcs_uri],
        )

        logger.info(
            f"Added document {body.display_name} from {body.gcs_uri} to corpus {corpus_id}"
        )

        return AddDocumentResponse(
            success=True,
            message=f"Document '{body.display_name}' added successfully. It will be processed and indexed shortly.",
        )

    except Exception as exc:
        logger.error(f"Failed to add document: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add document: {str(exc)}",
        )


@router.get(
    "/corpora/{corpus_id}/documents",
    response_model=list,
    summary="List documents in a corpus",
)
async def list_corpus_documents(
    corpus_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> list:
    """
    List all documents in a RAG corpus.
    """
    try:
        _init_vertexai()
        from vertexai import rag

        documents = list(
            rag.list_documents(
                corpus_id=f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{corpus_id}"
            )
        )

        doc_list = []
        for doc in documents:
            doc_list.append(
                {
                    "document_id": doc.name.split("/")[-1] if doc.name else "",
                    "display_name": doc.display_name,
                    "create_time": str(doc.create_time) if doc.create_time else "",
                }
            )

        return doc_list

    except Exception as exc:
        logger.error(f"Failed to list documents: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(exc)}",
        )


@router.delete(
    "/corpora/{corpus_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document from a corpus",
)
async def delete_corpus_document(
    corpus_id: str,
    document_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """
    Delete a specific document from a RAG corpus.
    """
    try:
        _init_vertexai()
        from vertexai import rag

        rag.delete_document(
            name=f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{corpus_id}/documents/{document_id}"
        )

        logger.info(f"Deleted document {document_id} from corpus {corpus_id}")

    except Exception as exc:
        logger.error(f"Failed to delete document: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(exc)}",
        )
