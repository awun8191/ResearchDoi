"""
Vertex AI RAG Tools for the ADK Agent.

This module provides tools for querying and managing Vertex AI RAG corpora
using the official Google Cloud Vertex AI Python SDK.
"""

import os
from typing import Optional
from pydantic import BaseModel, Field
import vertexai
from vertexai import rag
from dotenv import load_dotenv

load_dotenv()

# Configure Vertex AI
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "researchassistant-3446d")

# Isolate the RAG Engine location to a supported region to avoid allowlist restrictions
RAG_LOCATION = os.getenv("VERTEX_RAG_LOCATION", "europe-west4")

# Initialize Vertex AI for the local SDK
vertexai.init(project=PROJECT_ID, location=RAG_LOCATION)

# Default corpus ID - can be overridden via environment or user input
DEFAULT_CORPUS_ID = os.getenv("VERTEX_AI_RAG_CORPUS_ID", "")


def _get_corpus_name(corpus_id: str) -> str:
    """Helper to ensure the corpus ID is a fully qualified resource name."""
    if "/" in corpus_id:
        return corpus_id
    return f"projects/{PROJECT_ID}/locations/{RAG_LOCATION}/ragCorpora/{corpus_id}"


class RagQueryInput(BaseModel):
    query: str = Field(
        description="The search query to find relevant information in the knowledge base."
    )
    corpus_id: Optional[str] = Field(
        None,
        description="The RAG corpus ID to query. If not provided, uses the default corpus.",
    )


class ListCorporaInput(BaseModel):
    pass


class GetCorpusInfoInput(BaseModel):
    corpus_id: Optional[str] = Field(
        None,
        description="The RAG corpus ID to get info for. If not provided, uses the default corpus.",
    )


class AddDocumentInput(BaseModel):
    corpus_id: Optional[str] = Field(
        None,
        description="The RAG corpus ID to add document to. If not provided, uses the default corpus.",
    )
    gcs_uri: str = Field(
        description="Google Cloud Storage URI of the document to add (e.g., gs://bucket-name/document.pdf)"
    )
    display_name: str = Field(
        description="Display name for the document in the corpus."
    )


def create_corpus(display_name: str, description: Optional[str] = None) -> str:
    """
    Create a new Vertex AI RAG corpus via the Vertex AI SDK.
    """
    try:
        corpus = rag.create_corpus(
            display_name=display_name,
            description=description or ""
        )
        return f"Successfully created new RAG corpus '{display_name}' with ID: {corpus.name}"

    except Exception as e:
        return f"Error creating RAG corpus: {str(e)}"


def rag_query(query: str, corpus_id: Optional[str] = None) -> str:
    """
    Query the Vertex AI RAG corpus via the Vertex AI SDK.
    """
    use_corpus = corpus_id or DEFAULT_CORPUS_ID

    if not use_corpus:
        return "No RAG corpus configured. Please set VERTEX_AI_RAG_CORPUS_ID in environment or provide a corpus_id."

    try:
        corpus_name = _get_corpus_name(use_corpus)

        response = rag.retrieval_query(
            rag_resources=[rag.RagResource(rag_corpus=corpus_name)],
            text=query,
            similarity_top_k=5,
        )

        if not response or not response.contexts or not response.contexts.contexts:
            return f"No relevant information found in the knowledge base for query: {query}"

        # Format the results
        formatted_results = []
        for i, result in enumerate(response.contexts.contexts, 1):
            text = result.text
            source = result.source_uri
            formatted_results.append(f"[Result {i}]\n{text}\n\nSource: {source}")

        return "\n\n".join(formatted_results)

    except Exception as e:
        return f"Error querying RAG corpus: {str(e)}"


def list_corpora() -> str:
    """
    List all available Vertex AI RAG corpora via the Vertex AI SDK.
    """
    try:
        corpora = rag.list_corpora()

        if not corpora:
            return "No RAG corpora found in this project."

        result_lines = ["Available RAG Corpora:"]
        for corpus in corpora:
            result_lines.append(f"- {corpus.display_name} (ID: {corpus.name})")

        return "\n".join(result_lines)

    except Exception as e:
        return f"Error listing corpora: {str(e)}"


def get_corpus_info(corpus_id: Optional[str] = None) -> str:
    """
    Get information about a specific RAG corpus via the Vertex AI SDK.
    """
    use_corpus = corpus_id or DEFAULT_CORPUS_ID

    if not use_corpus:
        return "No RAG corpus configured. Please set VERTEX_AI_RAG_CORPUS_ID in environment or provide a corpus_id."

    try:
        corpus_name = _get_corpus_name(use_corpus)
        corpus = rag.get_corpus(name=corpus_name)

        info = [
            f"Corpus: {corpus.display_name}",
            f"ID: {corpus.name}",
            f"Description: {corpus.description or 'N/A'}",
            f"Create Time: {corpus.create_time}",
            f"Update Time: {corpus.update_time}",
        ]

        return "\n".join(info)

    except Exception as e:
        return f"Error getting corpus info: {str(e)}"


def add_document_to_corpus(
    gcs_uri: str, display_name: str, corpus_id: Optional[str] = None
) -> str:
    """
    Add a document to a Vertex AI RAG corpus via the Vertex AI SDK.
    """
    use_corpus = corpus_id or DEFAULT_CORPUS_ID

    if not use_corpus:
        return "No RAG corpus configured. Please set VERTEX_AI_RAG_CORPUS_ID in environment or provide a corpus_id."

    try:
        corpus_name = _get_corpus_name(use_corpus)

        # Import the file directly from Google Cloud Storage
        rag.import_files(
            corpus_name=corpus_name,
            paths=[gcs_uri]
        )

        return f"Successfully added document '{display_name}' from {gcs_uri} to corpus {use_corpus}. The document will be processed and indexed shortly."

    except Exception as e:
        return f"Error adding document to corpus: {str(e)}"