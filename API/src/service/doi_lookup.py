import logging
from typing import Any, Dict, Optional
from urllib.parse import unquote

import httpx

logger = logging.getLogger(__name__)


class DoiLookup:
    """
    Async service for fetching and standardizing DOI metadata from the Crossref API.
    Handles malformed DOIs, implements polite pool headers for Crossref,
    and uses httpx with timeout for resilience.
    """

    CROSSREF_API_URL = "https://api.crossref.org/works/{doi}"

    def __init__(
        self,
        contact_email: Optional[str] = None,
        timeout: int = 10,
    ) -> None:
        self.timeout = timeout
        self.contact_email = contact_email

    @staticmethod
    def _parse_doi(raw_input: str) -> str:
        """Parse a raw DOI string or URL and extract the canonical DOI identifier."""
        if not raw_input or not isinstance(raw_input, str):
            raise ValueError("Input must be a non-empty string.")

        raw_input = unquote(raw_input.strip())

        prefixes_to_strip = [
            "https://doi.org/",
            "http://doi.org/",
            "https://dx.doi.org/",
            "http://dx.doi.org/",
            "doi:",
            "info:doi/",
        ]

        clean_doi = raw_input
        for prefix in prefixes_to_strip:
            if clean_doi.lower().startswith(prefix):
                clean_doi = clean_doi[len(prefix):]
                break

        if not clean_doi.startswith("10."):
            raise ValueError(
                f"Invalid DOI format: '{clean_doi}'. DOIs should typically begin with '10.'"
            )

        return clean_doi

    async def fetch_metadata(self, raw_doi: str) -> Optional[Dict[str, Any]]:
        """Fetch and standardize metadata for a given DOI from Crossref (async)."""
        try:
            clean_doi = self._parse_doi(raw_doi)
        except ValueError as e:
            logger.error(f"Malformed DOI input ignored: {e}")
            return None

        url = self.CROSSREF_API_URL.format(doi=clean_doi)

        user_agent = "ResearchDoi Service (Python 3)"
        if self.contact_email:
            user_agent += f"; mailto:{self.contact_email}"

        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 404:
                    logger.warning(f"DOI not found in registry: {clean_doi}")
                    return None

                response.raise_for_status()

                try:
                    data = response.json()
                except ValueError as e:
                    logger.error(f"Failed to decode JSON response for DOI '{clean_doi}': {e}")
                    return None

                message = data.get("message", {})
                return self._extract_metadata(message)

        except httpx.HTTPError as e:
            logger.error(f"Network or protocol error fetching DOI metadata for '{clean_doi}': {e}")
            return None

    def _extract_metadata(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Crossref JSON into a standard internal dictionary schema."""
        metadata: Dict[str, Any] = {
            "doi": message.get("DOI"),
            "title": None,
            "authors": [],
            "publication_year": None,
            "venue": None,
            "url": message.get("URL"),
            "link": message.get("link", []),  # CrossRef link array for PDF resolution
        }

        # 1. Title
        titles = message.get("title", [])
        if titles and isinstance(titles, list):
            metadata["title"] = str(titles[0]).strip()

        # 2. Authors
        authors = message.get("author", [])
        if authors and isinstance(authors, list):
            for author in authors:
                if not isinstance(author, dict):
                    continue
                given = author.get("given", "").strip()
                family = author.get("family", "").strip()
                if given and family:
                    metadata["authors"].append(f"{given} {family}")
                elif family:
                    metadata["authors"].append(family)
                elif given:
                    metadata["authors"].append(given)
                elif "name" in author:
                    metadata["authors"].append(str(author.get("name")).strip())

        # 3. Publication year
        date_fields = ["published-print", "published-online", "issued", "created"]
        for field in date_fields:
            date_obj = message.get(field)
            if isinstance(date_obj, dict):
                date_parts = date_obj.get("date-parts")
                if date_parts and isinstance(date_parts, list) and isinstance(date_parts[0], list):
                    if len(date_parts[0]) > 0:
                        try:
                            metadata["publication_year"] = int(date_parts[0][0])
                            break
                        except (ValueError, TypeError):
                            continue

        # 4. Venue
        venues = message.get("container-title", [])
        if venues and isinstance(venues, list) and len(venues) > 0:
            metadata["venue"] = str(venues[0]).strip()

        return metadata
