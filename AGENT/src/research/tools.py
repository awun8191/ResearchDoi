import logging
import httpx
import os
import re
import asyncio
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load the local .env file before any module reads the environment.
load_dotenv()

# Arxiv integration
import arxiv

# ADK imports
from google.adk.events import Event
from google.genai import types

# Internal imports
from src import require_api_key
from src.service.doi_lookup import doi_service
from src.service.pdf_resolver import pdf_service

logger = logging.getLogger(__name__)

# Environment Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
API_KEY = require_api_key()
EXA_API_KEY = os.getenv("EXA_API_KEY", "")

# ── 1. Exa Direct API Integration (Replacing MCP due to Task conflict) ───────

async def mcp_exa_web_search_exa(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Directly calls the Exa API to search the web. 
    Bypasses MCP to avoid 'cancel scope' concurrency issues.
    """
    if not EXA_API_KEY:
        logger.error("EXA_API_KEY not found in environment.")
        return []

    url = "https://api.exa.ai/search"
    headers = {
        "x-api-key": EXA_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "query": query,
        "numResults": num_results,
        "useAutoprompt": True
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error(f"[ExaSearch] API error {resp.status_code}: {resp.text}")
                return []
            
            data = resp.json()
            results = data.get("results", [])
            return [
                {
                    "title": r.get("title", "Untitled"),
                    "url": r.get("url", ""),
                    "id": r.get("id", ""),
                    "score": r.get("score", 0),
                    "publishedDate": r.get("publishedDate", "")
                }
                for r in results
            ]
    except Exception as e:
        logger.error(f"[ExaSearch] Connection error: {e}")
        return []

async def mcp_exa_web_fetch_exa(urls: List[str]) -> List[Dict[str, Any]]:
    """
    Directly calls the Exa API to fetch content from specific URLs.
    """
    if not EXA_API_KEY:
        logger.error("EXA_API_KEY not found in environment.")
        return []

    url = "https://api.exa.ai/contents"
    headers = {
        "x-api-key": EXA_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "ids": urls,
        "text": True # Fetch clean text content
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error(f"[ExaFetch] API error {resp.status_code}: {resp.text}")
                return []
            
            data = resp.json()
            results = data.get("results", [])
            return [
                {
                    "title": r.get("title", "Untitled"),
                    "url": r.get("url", ""),
                    "text": r.get("text", "")
                }
                for r in results
            ]
    except Exception as e:
        logger.error(f"[ExaFetch] Connection error: {e}")
        return []

# We create a dummy object to satisfy imports of 'exa_mcp_tools' if any, 
# but we will update agents to use the direct functions.
class ExaToolsetFallback:
    def __init__(self):
        self.mcp_exa_web_search_exa = mcp_exa_web_search_exa
        self.mcp_exa_web_fetch_exa = mcp_exa_web_fetch_exa
    
    async def get_tools(self, ctx=None):
        return [mcp_exa_web_search_exa, mcp_exa_web_fetch_exa]

exa_mcp_tools = ExaToolsetFallback()

# ── 2. Arxiv & DOI Tools ─────────────────────────────────────────────────────

async def arxiv_search_tool(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Searches Arxiv for research papers matching the query.
    Returns title, summary, authors, and PDF links.
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    
    results = []
    try:
        for result in client.results(search):
            results.append({
                "title": result.title,
                "summary": result.summary,
                "authors": [a.name for a in result.authors],
                "pdf_url": result.pdf_url,
                "entry_id": result.entry_id,
                "published": result.published.isoformat() if result.published else None
            })
        return results
    except Exception as e:
        logger.error(f"[arxiv_search_tool] Error: {e}")
        return []

async def doi_lookup_tool(doi: str) -> Dict[str, Any]:
    """
    Fetches standardized metadata for a given DOI (e.g., '10.1038/nphys1170').
    """
    result = await doi_service.fetch_metadata(doi)
    return result or {"error": "DOI not found"}

async def pdf_resolver_tool(doi: str) -> Dict[str, Any]:
    """
    Resolves a DOI to a direct PDF download URL.
    """
    pdf_url = await pdf_service.resolve_pdf(doi)
    return {"pdf_url": pdf_url} if pdf_url else {"error": "Could not resolve PDF"}

def _normalize_doi(doi: Optional[str]) -> Optional[str]:
    """Extracts a normalized DOI from a string."""
    if not doi or not isinstance(doi, str):
        return None
    doi = doi.lower().strip()
    match = re.search(r"10\.\d{4,9}/[-._;()/:a-z0-9]+", doi, re.I)
    return match.group(0) if match else None

async def semantic_scholar_search_tool(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Academic discovery tool using Arxiv.
    """
    return await arxiv_search_tool(query, limit)

# ── 3. RAG Tools ────────────────────────────────────────────────────────────

async def research_retrieval_tool(query: str, project_id: str, uid: str, top_k: int = 20) -> List[Dict[str, Any]]:
    """
    Performs a semantic search in the project's knowledge base.
    """
    url = f"{API_BASE_URL}/api/rag/search"
    headers = {
        "X-Api-Key": API_KEY,
        "X-User-Id": uid,
        "Content-Type": "application/json"
    }
    payload = {"project_id": project_id, "query": query, "top_k": top_k}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
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
    except Exception:
        return []

async def rag_ingestion_tool(text: str, project_id: str, uid: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Ingests text into the RAG vector store.
    """
    url = f"{API_BASE_URL}/api/rag/ingest"
    headers = {
        "X-Api-Key": API_KEY,
        "X-User-Id": uid,
        "Content-Type": "application/json"
    }
    payload = {"project_id": project_id, "text": text, "metadata": metadata or {}}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            return resp.json() if resp.status_code == 200 else {"status": "error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── 4. Storage Tools ────────────────────────────────────────────────────────

async def save_research_document(filename: str, content: str, project_id: str, uid: str) -> Dict[str, Any]:
    """
    Saves a research document to project storage.
    """
    url = f"{API_BASE_URL}/api/storage/upload"
    headers = {"X-Api-Key": API_KEY, "X-User-Id": uid}
    files = {"file": (filename, content.encode("utf-8"), "text/markdown")}
    data = {"project_id": project_id}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, files=files, data=data)
            return resp.json() if resp.status_code == 200 else {"status": "error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
