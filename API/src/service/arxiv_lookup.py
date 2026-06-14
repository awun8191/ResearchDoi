import asyncio
import logging
from typing import Any, Dict, Optional
from urllib.parse import unquote

import arxiv

logger = logging.getLogger(__name__)


class ArxivLookup:
    """
    A service for fetching and standardizing metadata from the ArXiv API using the official `arxiv` python package.
    Sync methods are wrapped with async variants so callers don't block the event loop.
    """

    def __init__(self, timeout: int = 10) -> None:
        self.client = arxiv.Client()

    async def fetch_metadata_async(self, query: str) -> Optional[Dict[str, Any]]:
        """Async wrapper around fetch_metadata — runs in thread pool to avoid blocking."""
        return await asyncio.to_thread(self.fetch_metadata, query)

    def fetch_metadata(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Fetches and standardizes metadata for a given query from ArXiv (synchronous).
        """
        if not query or not isinstance(query, str):
            logger.error("Query must be a non-empty string.")
            return None

        clean_val = unquote(query.strip())

        prefixes = ["https://doi.org/", "http://doi.org/", "doi:", "https://arxiv.org/abs/", "http://arxiv.org/abs/", "arxiv:"]
        original_clean = clean_val
        clean_lower = clean_val.lower()
        for p in prefixes:
            if clean_lower.startswith(p):
                original_clean = original_clean[len(p):]
                clean_lower = clean_lower[len(p):]
                break

        if original_clean.startswith("10."):
            search = arxiv.Search(query=f"doi:{original_clean}", max_results=1)
        elif " " not in original_clean and any(char.isdigit() for char in original_clean):
            try:
                search = arxiv.Search(id_list=[original_clean], max_results=1)
            except Exception:
                search = arxiv.Search(query=f"all:{original_clean}", max_results=1)
        else:
            search = arxiv.Search(query=f"all:{original_clean}", max_results=1)

        try:
            results = list(self.client.results(search))
            if not results:
                logger.warning(f"No results found in ArXiv for query: {query}")
                return None
            return self._to_metadata(results[0])
        except Exception as e:
            logger.error(f"Error fetching ArXiv metadata for '{query}': {e}")
            return None

    async def search_async(self, query: str, max_results: int = 10) -> list[Dict[str, Any]]:
        """Async wrapper around search — runs in thread pool to avoid blocking."""
        return await asyncio.to_thread(self.search, query, max_results)

    def search(self, query: str, max_results: int = 10) -> list[Dict[str, Any]]:
        """Searches ArXiv for multiple research papers matching the keyword query (synchronous)."""
        if not query or not isinstance(query, str):
            return []

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        results = []
        try:
            for entry in self.client.results(search):
                results.append(self._to_metadata(entry))
            return results
        except Exception as e:
            logger.error(f"Error searching ArXiv for '{query}': {e}")
            return []

    def _to_metadata(self, entry: arxiv.Result) -> Dict[str, Any]:
        """Standardizes an ArXiv result object into a metadata dictionary."""
        resolved_doi = entry.doi if entry.doi else entry.get_short_id()

        return {
            "doi": resolved_doi,
            "title": entry.title,
            "authors": [author.name for author in entry.authors],
            "publication_year": entry.published.year if entry.published else None,
            "venue": "ArXiv",
            "url": entry.entry_id,
            "pdf_url": entry.pdf_url,
            "abstract": entry.summary,
        }
