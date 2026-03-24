import logging
import httpx
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Use the production URL found in .env, fallback to the newly deployed URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
API_KEY = os.getenv("API_KEY", "nas")

async def research_retrieval_tool(query: str, project_id: str, uid: str, top_k: int = 20) -> List[Dict[str, Any]]:
    """
    Performs a semantic search in the project's knowledge base via the API.
    """
    url = f"{API_BASE_URL}/api/rag/search"
    headers = {
        "X-Api-Key": API_KEY,
        "X-User-Id": uid,
        "Content-Type": "application/json"
    }
    payload = {
        "project_id": project_id,
        "query": query,
        "top_k": top_k
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error(f"[retrieval_tool] API error {resp.status_code}: {resp.text}")
                return []
            
            results = resp.json()
            return [
                {
                    "text": r["text"],
                    "doi": r["metadata"].get("doi", "Unknown"),
                    "section": r["metadata"].get("section", "General"),
                    "score": r["score"]
                }
                for r in results
            ]
    except Exception as e:
        logger.error(f"[retrieval_tool] Connection error: {e}")
        return []

async def semantic_scholar_search_tool(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Searches Semantic Scholar for academic papers.
    Returns metadata including title, authors, year, externalIds (for DOI), abstract, and openAccessPdf URL.
    """
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,externalIds,abstract,openAccessPdf,venue,citationCount"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.error(f"[semantic_scholar] API error {resp.status_code}: {resp.text}")
                return []
            
            data = resp.json()
            papers = data.get("data", [])
            return [
                {
                    "title": p.get("title"),
                    "authors": [a.get("name") for a in p.get("authors", [])],
                    "year": p.get("year"),
                    "doi": (p.get("externalIds") or {}).get("DOI"),
                    "abstract": p.get("abstract"),
                    "pdf_url": (p.get("openAccessPdf") or {}).get("url"),
                    "venue": p.get("venue"),
                    "citations": p.get("citationCount")
                }
                for p in papers
            ]
    except Exception as e:
        logger.error(f"[semantic_scholar] Connection error: {e}")
        return []

async def serp_api_search_tool(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Searches Google via SerpApi.
    Returns a list of search results with title, link, and snippet.
    """
    serp_api_key = os.getenv("SERPAPI_API_KEY")
    if not serp_api_key:
        logger.error("[serp_api] SERPAPI_API_KEY not found in environment.")
        return []

    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": serp_api_key,
        "num": limit,
        "engine": "google"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.error(f"[serp_api] API error {resp.status_code}: {resp.text}")
                return []

            data = resp.json()
            results = data.get("organic_results", [])
            return [
                {
                    "title": r.get("title"),
                    "link": r.get("link"),
                    "snippet": r.get("snippet"),
                    "source": "google_serp"
                }
                for r in results
            ]
    except Exception as e:
        logger.error(f"[serp_api] Connection error: {e}")
        return []

async def rag_ingestion_tool(
    text: str, 
    project_id: str, 
    uid: str, 
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Ingests text into the RAG vector store for a specific project.
    """
    url = f"{API_BASE_URL}/api/rag/ingest"
    headers = {
        "X-Api-Key": API_KEY,
        "X-User-Id": uid,
        "Content-Type": "application/json"
    }
    payload = {
        "project_id": project_id,
        "text": text,
        "metadata": metadata or {}
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error(f"[ingestion_tool] API error {resp.status_code}: {resp.text}")
                return {"status": "error", "message": resp.text}
            
            return resp.json()
    except Exception as e:
        logger.error(f"[ingestion_tool] Connection error: {e}")
        return {"status": "error", "message": str(e)}

async def save_research_document(
    filename: str, 
    content: str, 
    project_id: str, 
    uid: str, 
    content_type: str = "text/markdown"
) -> Dict[str, Any]:
    """
    Saves a research document to the project storage via the API.
    """
    url = f"{API_BASE_URL}/api/storage/upload"
    headers = {
        "X-Api-Key": API_KEY,
        "X-User-Id": uid
    }
    
    files = {
        "file": (filename, content.encode("utf-8"), content_type)
    }
    data = {
        "project_id": project_id
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, files=files, data=data)
            if resp.status_code != 200:
                logger.error(f"[storage_tool] API error {resp.status_code}: {resp.text}")
                return {"status": "error", "message": resp.text}
            
            result = resp.json()
            return {
                "storage_path": result["storage_path"],
                "document_url": result["document_url"],
                "status": "success"
            }
    except Exception as e:
        logger.error(f"[storage_tool] Connection error: {e}")
        return {"status": "error", "message": str(e)}
