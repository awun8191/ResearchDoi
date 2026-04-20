import logging
from typing import Any, Dict, Optional
from urllib.parse import unquote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class DoiLookup:
    """
    A robust service for fetching and standardizing DOI metadata from the Crossref API.
    Handles malformed DOIs, implements polite pool headers for Crossref, 
    and incorporates connection pooling with exponential backoff for resilience.
    """

    CROSSREF_API_URL = "https://api.crossref.org/works/{doi}"
    
    def __init__(
        self, 
        contact_email: Optional[str] = None, 
        max_retries: int = 3, 
        timeout: int = 10
    ) -> None:
        """
        Initializes the DoiLookup service.

        Args:
            contact_email (Optional[str]): Used to enter the Crossref 'polite pool' 
                                           for more reliable API access.
            max_retries (int): Total number of retries for transient networking or server errors.
            timeout (int): Timeout in seconds for API requests.
        """
        self.timeout = timeout
        self.session = requests.Session()
        
        # Configure User-Agent. Crossref polite pool requires a mailto address if possible.
        user_agent = "ResearchDoi Service (Python 3)"
        if contact_email:
            user_agent += f"; mailto:{contact_email}"
        
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "application/json"
        })
        
        # Configure exponential backoff for transient errors
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["GET", "OPTIONS"],
            backoff_factor=1.0  # Sleeps 1s, 2s, 4s between retries
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)  # type: ignore
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _parse_doi(self, raw_input: str) -> str:
        """
        Parses a raw DOI string or URL and extracts the canonical DOI identifier.

        Args:
            raw_input (str): The raw text (e.g. 'doi:10.1234/abc', 'https://doi.org/10.1234/abc').

        Returns:
            str: The sanitized DOI identifier.

        Raises:
            ValueError: If the extracted value is structurally invalid.
        """
        if not raw_input or not isinstance(raw_input, str):
            raise ValueError("Input must be a non-empty string.")

        # URL decoding in case the DOI is passed encoded
        raw_input = unquote(raw_input.strip())

        prefixes_to_strip = [
            "https://doi.org/",
            "http://doi.org/",
            "https://dx.doi.org/",
            "http://dx.doi.org/",
            "doi:",
            "info:doi/"
        ]

        clean_doi = raw_input
        for prefix in prefixes_to_strip:
            if clean_doi.lower().startswith(prefix):
                clean_doi = clean_doi[len(prefix):]
                break

        # A valid DOI invariably starts with "10."
        if not clean_doi.startswith("10."):
            raise ValueError(f"Invalid DOI format: '{clean_doi}'. DOIs should typically begin with '10.'")

        return clean_doi

    def fetch_metadata(self, raw_doi: str) -> Optional[Dict[str, Any]]:
        """
        Fetches and standardizes metadata for a given DOI from Crossref.

        Args:
            raw_doi (str): The raw DOI identifier or URL.

        Returns:
            Optional[Dict[str, Any]]: Standardized metadata dictionary, or None if not found/error.
            
            Standard output schema:
            {
                "doi": str,
                "title": Optional[str],
                "authors": List[str],
                "publication_year": Optional[int],
                "venue": Optional[str],
                "url": Optional[str]
            }
        """
        try:
            clean_doi = self._parse_doi(raw_doi)
        except ValueError as e:
            logger.error(f"Malformed DOI input ignored: {e}")
            return None

        url = self.CROSSREF_API_URL.format(doi=clean_doi)

        try:
            response = self.session.get(url, timeout=self.timeout)
            
            # Crossref returns 404 for DOIs that are properly formatted but don't exist
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

        except requests.exceptions.RequestException as e:
            logger.error(f"Network or protocol error fetching DOI metadata for '{clean_doi}': {e}")
            return None

    def _extract_metadata(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms raw Crossref JSON dict into a standard internal dictionary schema.
        
        Args:
            message (Dict[str, Any]): The 'message' node of a Crossref API response.

        Returns:
            Dict[str, Any]: A curated subset of metadata attributes.
        """
        metadata: Dict[str, Any] = {
            "doi": message.get("DOI"),
            "title": None,
            "authors": [],
            "publication_year": None,
            "venue": None,
            "url": message.get("URL")
        }

        # 1. Title Normalization
        titles = message.get("title", [])
        if titles and isinstance(titles, list):
            metadata["title"] = str(titles[0]).strip()

        # 2. Author Normalization
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
                elif "name" in author:  # Handle institutional authors
                    metadata["authors"].append(str(author.get("name")).strip())

        # 3. Publication Year Normalization
        # Evaluate date fields in order of highest reliability
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

        # 4. Venue / Container Title Normalization
        venues = message.get("container-title", [])
        if venues and isinstance(venues, list) and len(venues) > 0:
            metadata["venue"] = str(venues[0]).strip()

        return metadata
