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

    async def search_async(self, query: str, max_results: int = 10, offset: int = 0) -> list[Dict[str, Any]]:
        """Async wrapper around search — runs in thread pool to avoid blocking."""
        return await asyncio.to_thread(self.search, query, max_results, offset)

    def _build_search_query(self, raw_query: str) -> str:
        """Constructs a high-relevance query by filtering out stop and generic words and joining with AND."""
        import re
        STOP_WORDS = {
            'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'arent', 'as', 
            'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'cant', 'cannot', 
            'could', 'couldnt', 'did', 'didnt', 'do', 'does', 'doesnt', 'doing', 'dont', 'down', 'during', 'each', 'few', 
            'for', 'from', 'further', 'had', 'hadnt', 'has', 'hasnt', 'have', 'havent', 'having', 'he', 'hed', 'hell', 
            'hes', 'her', 'here', 'heres', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'hows', 'i', 'id', 'ill', 
            'im', 'ive', 'if', 'in', 'into', 'is', 'isnt', 'it', 'its', 'itself', 'lets', 'me', 'more', 'most', 'mustnt', 
            'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 
            'ourselves', 'out', 'over', 'own', 'same', 'shant', 'she', 'shed', 'shell', 'shes', 'should', 'shouldnt', 
            'so', 'some', 'such', 'than', 'that', 'thats', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 
            'there', 'theres', 'these', 'they', 'theyd', 'theyll', 'theyre', 'theyve', 'this', 'those', 'through', 'to', 
            'too', 'under', 'until', 'up', 'very', 'was', 'wasnt', 'we', 'wed', 'well', 'were', 'weve', 'werent', 'what', 
            'whats', 'when', 'whens', 'where', 'wheres', 'which', 'while', 'who', 'whos', 'whom', 'why', 'whys', 'with', 
            'wont', 'would', 'wouldnt', 'you', 'youd', 'youll', 'youre', 'youve', 'your', 'yours', 'yourself', 'yourselves'
        }

        GENERIC_WORDS = {
            'system', 'systems', 'detection', 'ai', 'artificial', 'intelligence', 'method', 'methods', 
            'approach', 'approaches', 'model', 'models', 'analysis', 'study', 'design', 'paper', 'papers', 
            'research', 'framework', 'frameworks', 'algorithm', 'algorithms', 'using', 'based', 'via', 
            'application', 'applications', 'evaluation', 'performance', 'results', 'new', 'novel', 'modern'
        }

        words = re.findall(r'[a-zA-Z0-9]+', raw_query.lower())
        filtered = [w for w in words if w not in STOP_WORDS and w not in GENERIC_WORDS]
        if not filtered:
            # Fall back to removing just stop words
            filtered = [w for w in words if w not in STOP_WORDS]
        if not filtered:
            return raw_query
        return ' AND '.join(filtered)

    def search(self, query: str, max_results: int = 10, offset: int = 0) -> list[Dict[str, Any]]:
        """Searches ArXiv for multiple research papers matching the keyword query (synchronous)."""
        if not query or not isinstance(query, str):
            return []

        formatted_query = self._build_search_query(query)
        logger.info(f"Formulated search query for '{query}': '{formatted_query}'")

        results = []
        # Try search with formulated AND query first
        search = arxiv.Search(
            query=formatted_query,
            max_results=offset + max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        try:
            generator = self.client.results(search)
            from itertools import islice
            sliced_results = islice(generator, offset, offset + max_results)
            for entry in sliced_results:
                results.append(self._to_metadata(entry))
        except Exception as e:
            logger.warning(f"Strict search failed or timed out for '{formatted_query}': {e}")
            results = []

        # Fall back to raw user query if strict AND query returns no results
        if not results and formatted_query != query:
            logger.info(f"Strict search returned 0 results for '{formatted_query}'. Falling back to raw query: '{query}'")
            search = arxiv.Search(
                query=query,
                max_results=offset + max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )
            try:
                generator = self.client.results(search)
                from itertools import islice
                sliced_results = islice(generator, offset, offset + max_results)
                for entry in sliced_results:
                    results.append(self._to_metadata(entry))
            except Exception as e:
                logger.error(f"Fallback search failed for '{query}': {e}")

        return results

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
