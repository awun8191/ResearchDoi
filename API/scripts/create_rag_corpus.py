"""
Script to create a Vertex AI RAG corpus and add documents to it.
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "researchassistant-3446d")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
BUCKET_NAME = os.getenv("GOOGLE_CLOUD_STARTING_BUCKET", "rast-agent")


async def create_corpus():
    from vertexai import rag

    # Initialize Vertex AI
    rag.init(project=PROJECT_ID, location=LOCATION)

    # Create a corpus
    corpus = rag.create_corpus(
        display_name="ResearchDoi Knowledge Base",
        description="Knowledge base for ResearchDoi research assistant",
    )

    print(f"Created corpus: {corpus.name}")
    print(f"Corpus ID: {corpus.name.split('/')[-1]}")

    # Return the corpus ID so we can use it
    return corpus.name.split("/")[-1]


async def list_corpora():
    from vertexai import rag

    rag.init(project=PROJECT_ID, location=LOCATION)

    corpora = rag.list_corpora()
    print("\nAvailable corpora:")
    for c in corpora:
        print(f"  - {c.display_name} (ID: {c.name})")

    return corpora


async def add_documents_to_corpus(corpus_id: str):
    from vertexai import rag

    rag.init(project=PROJECT_ID, location=LOCATION)

    # GCS paths for documents
    gcs_paths = [
        f"gs://{BUCKET_NAME}/documents/",
    ]

    print(f"\nImporting documents to corpus {corpus_id}...")

    # Import files from GCS
    rag.import_files(
        rag_corpus=f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{corpus_id}",
        paths=gcs_paths,
    )

    print("Documents imported successfully!")


async def main():
    import sys

    action = sys.argv[1] if len(sys.argv) > 1 else "create"

    if action == "create":
        corpus_id = await create_corpus()
        print(
            f"\nTo use this corpus, set VERTEX_AI_RAG_CORPUS_ID={corpus_id} in your .env file"
        )

    elif action == "list":
        await list_corpora()

    elif action == "add":
        corpus_id = os.getenv("VERTEX_AI_RAG_CORPUS_ID", "")
        if not corpus_id:
            print("Error: VERTEX_AI_RAG_CORPUS_ID not set in .env")
            return
        await add_documents_to_corpus(corpus_id)

    elif action == "info":
        from vertexai import rag

        rag.init(project=PROJECT_ID, location=LOCATION)

        corpus_id = os.getenv("VERTEX_AI_RAG_CORPUS_ID", "")
        if not corpus_id:
            print("Error: VERTEX_AI_RAG_CORPUS_ID not set in .env")
            return

        corpus = rag.get_corpus(
            name=f"projects/{PROJECT_ID}/locations/{LOCATION}/ragCorpora/{corpus_id}"
        )
        print(f"\nCorpus: {corpus.display_name}")
        print(f"Description: {corpus.description}")
        print(f"Create time: {corpus.create_time}")
        print(f"Update time: {corpus.update_time}")


if __name__ == "__main__":
    asyncio.run(main())
