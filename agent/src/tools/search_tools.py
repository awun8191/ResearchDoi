"""Search tools for RAST — arXiv, Semantic Scholar, web search, paper reading."""

import re
import logging
from typing import Any

import httpx
import feedparser

from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if value is None:
        return []
    return [str(value)]


# ── arXiv Search ─────────────────────────────────────────────────────────────


def arxiv_search(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search arXiv API for academic papers matching the query.

    Uses the arXiv API (export.arxiv.org) to fetch paper metadata.
    Returns a list of paper dicts with id, title, authors, abstract,
    published date, and pdf_link.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return (default 10).

    Returns:
        List of paper dictionaries.
    """
    import urllib.parse

    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query=all:{urllib.parse.quote(query)}&"
        f"max_results={max_results}&sortBy=relevance&sortOrder=descending"
    )

    try:
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"[arxiv_search] HTTP error: {e}")
        return []

    feed = feedparser.parse(response.text)
    papers: list[dict[str, Any]] = []

    for entry in feed.entries:
        paper_id = entry.get("id", "").strip()
        # Extract arXiv ID from URL
        arxiv_id = paper_id.split("/")[-1].split("v")[0] if paper_id else ""

        # Get PDF link
        pdf_link = ""
        for link in entry.get("links", []):
            if link.get("rel", "") == "related" and link.get("type", "") == "application/pdf":
                pdf_link = link.get("href", "")
                break
            if link.get("title", "") == "pdf":
                pdf_link = link.get("href", "")
                break
        if not pdf_link and paper_id:
            pdf_link = paper_id.replace("abs", "pdf")

        authors = [a.get("name", "") for a in entry.get("authors", []) if a.get("name")]

        papers.append({
            "id": arxiv_id or paper_id,
            "title": _safe_str(entry.get("title", "")).replace("\n", " ").strip(),
            "authors": authors,
            "abstract": _safe_str(entry.get("summary", "")).replace("\n", " ").strip(),
            "published": _safe_str(entry.get("published", "")),
            "pdf_link": pdf_link,
            "source": "arxiv",
            "entry_id": paper_id,
        })

    return papers


arxiv_search_tool = FunctionTool(func=arxiv_search,
)

# ── Semantic Scholar Search ──────────────────────────────────────────────────


def semantic_scholar_search(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search Semantic Scholar API for academic papers.

    Uses the Semantic Scholar REST API (api.semanticscholar.org/graph/v1).
    Returns paper metadata including title, authors, abstract, year, citations.

    Args:
        query: Search query string.
        max_results: Maximum number of results (default 10, max 100).

    Returns:
        List of paper dictionaries.
    """
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": min(max_results, 100),
        "fields": "title,authors,abstract,year,externalIds,url,citationCount,publicationDate,venue",
    }

    try:
        response = httpx.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.error(f"[semantic_scholar_search] Error: {e}")
        return []

    papers: list[dict[str, Any]] = []
    for paper in data.get("data", []):
        authors = [a.get("name", "") for a in paper.get("authors", []) if a.get("name")]
        ext_ids = paper.get("externalIds", {}) or {}

        papers.append({
            "id": paper.get("paperId", ""),
            "title": _safe_str(paper.get("title", "")),
            "authors": authors,
            "abstract": _safe_str(paper.get("abstract", "")),
            "published": _safe_str(paper.get("publicationDate", paper.get("year", ""))),
            "year": str(paper.get("year", "")),
            "venue": _safe_str(paper.get("venue", "")),
            "pdf_link": _safe_str(ext_ids.get("DOI", "")),
            "source": "semantic_scholar",
            "citation_count": paper.get("citationCount", 0),
            "url": _safe_str(paper.get("url", "")),
        })

    return papers


semantic_scholar_search_tool = FunctionTool(func=semantic_scholar_search,
)

# ── Web Search ───────────────────────────────────────────────────────────────


def web_search(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search the web for additional papers, preprints, and grey literature.

    Uses a simple approach: queries arXiv and Semantic Scholar for broader
    coverage, plus returns the query as search suggestion. In production,
    this would use a real web search API (Exa, SerpAPI, etc.).

    Args:
        query: Search query string.
        max_results: Maximum results (default 10).

    Returns:
        List of result dicts.
    """
    # Combine arXiv and Semantic Scholar results for broad coverage
    arxiv_results = arxiv_search(query, max_results=max_results // 2 + 1)
    ss_results = semantic_scholar_search(query, max_results=max_results // 2 + 1)

    # Deduplicate by title
    seen_titles: set[str] = set()
    combined: list[dict[str, Any]] = []

    for paper in arxiv_results + ss_results:
        title_lower = paper.get("title", "").lower().strip()
        if title_lower and title_lower not in seen_titles:
            seen_titles.add(title_lower)
            paper["source"] = "web"
            combined.append(paper)

    return combined[:max_results]


web_search_tool = FunctionTool(func=web_search,
)

# ── Read Paper ───────────────────────────────────────────────────────────────


def read_paper(url: str) -> dict[str, Any]:
    """Fetch and extract paper text from a URL.

    Handles arXiv abstract pages and general web pages.
    Returns the extracted text content.

    Args:
        url: URL of the paper (arXiv page, PDF link, etc.).

    Returns:
        Dict with 'text' key containing extracted content,
        'title', 'success' flag, and error info if applicable.
    """
    if not url:
        return {"text": "", "title": "", "success": False, "error": "No URL provided"}

    try:
        response = httpx.get(url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")

        # Check if it's a PDF
        if "application/pdf" in content_type or url.endswith(".pdf"):
            return {
                "text": "[PDF content — use PDF parser in production]",
                "title": url.split("/")[-1],
                "success": True,
                "note": "PDF binary — full extraction requires PyMuPDF or similar",
            }

        text = response.text
        title = _extract_html_title(text)

        # Try to extract main content
        body_text = _extract_body_text(text)

        return {
            "text": body_text or text[:10000],
            "title": title,
            "url": url,
            "success": True,
        }

    except Exception as e:
        logger.error(f"[read_paper] Error fetching {url}: {e}")
        return {"text": "", "title": "", "success": False, "error": str(e)}


def _extract_html_title(html: str) -> str:
    """Extract <title> from HTML."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_body_text(html: str) -> str:
    """Simple HTML-to-text extraction (strip tags, normalize whitespace)."""
    # Remove scripts and styles
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.IGNORECASE | re.DOTALL)
    # Remove tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Limit to first 15000 chars
    return text[:15000]


read_paper_tool = FunctionTool(func=read_paper,
)

# ── Extract Findings ─────────────────────────────────────────────────────────


def extract_findings(paper_content: str) -> list[dict[str, str]]:
    """Extract structured findings from paper content.

    Attempts to identify key findings, claims, methodologies, and results
    from the paper text.

    Args:
        paper_content: Full or partial paper text.

    Returns:
        List of finding dicts with 'type' and 'text' keys.
    """
    findings: list[dict[str, str]] = []

    if not paper_content or len(paper_content.strip()) < 50:
        return findings

    # Simple heuristic-based extraction
    # Look for sentences containing indicator phrases
    indicator_patterns = [
        (r"we find\s+that\s+(.*?)[.;]?", "finding"),
        (r"we show\s+that\s+(.*?)[.;]?", "finding"),
        (r"we demonstrate\s+that\s+(.*?)[.;]?", "finding"),
        (r"our results\s+(show|indicate|demonstrate|suggest)\s+that\s+(.*?)[.;]?", "result"),
        (r"we propose\s+(.*?)[.;]?", "method"),
        (r"we introduce\s+(.*?)[.;]?", "method"),
        (r"we develop\s+(.*?)[.;]?", "method"),
        (r"we achieve\s+(.*?)[.;]?", "result"),
        (r"the main contribution[s]?\s+(?:is|are)\s+(.*?)[.;]?", "contribution"),
        (r"key insight[s]?\s+(?:is|are)\s+(.*?)[.;]?", "insight"),
        (r"state-of-the-art\s+(.*?)[.;]?", "result"),
        (r"outperform[s]?\s+(.*?)[.;]?", "result"),
    ]

    sentences = re.split(r"(?<=[.!?])\s+", paper_content)

    seen: set[str] = set()
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 20:
            continue

        for pattern, finding_type in indicator_patterns:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                # Use the last non-None group
                text = [g for g in match.groups() if g][-1]
                text = text.strip()
                if text and text not in seen and len(text) > 15:
                    seen.add(text)
                    findings.append({"type": finding_type, "text": text})
                break

    return findings


extract_findings_tool = FunctionTool(func=extract_findings,
)

# ── All Search Tools ─────────────────────────────────────────────────────────

ALL_SEARCH_TOOLS: list[FunctionTool] = [
    arxiv_search_tool,
    semantic_scholar_search_tool,
    web_search_tool,
]
