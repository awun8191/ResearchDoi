"""
Tests for DOI lookup service — parsing logic and async HTTP resolution.
"""

import pytest

from src.service.doi_lookup import DoiLookup


class TestDoiParsing:
    """Pure logic tests — no network calls needed."""

    def setup_method(self):
        self.service = DoiLookup()

    def test_parses_bare_doi(self):
        result = self.service._parse_doi("10.1038/nature12345")
        assert result == "10.1038/nature12345"

    def test_parses_doi_url(self):
        result = self.service._parse_doi("https://doi.org/10.1038/nature12345")
        assert result == "10.1038/nature12345"

    def test_parses_doi_org_http(self):
        result = self.service._parse_doi("http://doi.org/10.1234/abc123")
        assert result == "10.1234/abc123"

    def test_parses_dx_doi_url(self):
        result = self.service._parse_doi("https://dx.doi.org/10.1234/5678")
        assert result == "10.1234/5678"

    def test_parses_doi_prefix(self):
        result = self.service._parse_doi("doi:10.1000/xyz789")
        assert result == "10.1000/xyz789"

    def test_parses_info_doi(self):
        result = self.service._parse_doi("info:doi/10.1007/s00425-019-03123-5")
        assert result == "10.1007/s00425-019-03123-5"

    def test_parses_url_encoded_doi(self):
        result = self.service._parse_doi("https://doi.org/10.1007%2Fs00425-019-03123-5")
        assert result == "10.1007/s00425-019-03123-5"

    def test_rejects_non_doi(self):
        with pytest.raises(ValueError, match="should typically begin with '10.'"):
            self.service._parse_doi("not-a-doi")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="non-empty string"):
            self.service._parse_doi("")

    def test_rejects_none(self):
        with pytest.raises(ValueError, match="non-empty string"):
            self.service._parse_doi(None)  # type: ignore


class TestDoiMetadataExtraction:
    """Test the metadata extraction from raw CrossRef API responses."""

    def setup_method(self):
        self.service = DoiLookup()

    def test_extracts_minimal_metadata(self):
        raw = {
            "DOI": "10.1234/test",
            "URL": "https://doi.org/10.1234/test",
        }
        result = self.service._extract_metadata(raw)
        assert result["doi"] == "10.1234/test"
        assert result["title"] is None
        assert result["authors"] == []
        assert result["publication_year"] is None
        assert result["venue"] is None
        assert result["url"] == "https://doi.org/10.1234/test"

    def test_extracts_full_metadata(self):
        raw = {
            "DOI": "10.1234/full",
            "title": ["A Full Research Paper Title"],
            "author": [
                {"given": "John", "family": "Smith"},
                {"given": "Jane", "family": "Doe"},
            ],
            "published-print": {"date-parts": [[2023, 6, 15]]},
            "container-title": ["Journal of Important Research"],
            "URL": "https://doi.org/10.1234/full",
        }
        result = self.service._extract_metadata(raw)
        assert result["doi"] == "10.1234/full"
        assert result["title"] == "A Full Research Paper Title"
        assert result["authors"] == ["John Smith", "Jane Doe"]
        assert result["publication_year"] == 2023
        assert result["venue"] == "Journal of Important Research"
        assert result["url"] == "https://doi.org/10.1234/full"

    def test_handles_institutional_author(self):
        raw = {
            "DOI": "10.1234/inst",
            "title": ["A Big Science Paper"],
            "author": [{"name": "The Large Hadron Collider Collaboration"}],
            "issued": {"date-parts": [[2024]]},
        }
        result = self.service._extract_metadata(raw)
        assert result["authors"] == ["The Large Hadron Collider Collaboration"]
        assert result["publication_year"] == 2024

    def test_falls_through_date_fields(self):
        """Should try published-print, published-online, issued, then created."""
        raw = {
            "DOI": "10.1234/dates",
            "created": {"date-parts": [[2020, 1, 1]]},
        }
        result = self.service._extract_metadata(raw)
        assert result["publication_year"] == 2020

    def test_handles_missing_authors_gracefully(self):
        raw = {
            "DOI": "10.1234/noauth",
            "published-online": {"date-parts": [[2022]]},
        }
        result = self.service._extract_metadata(raw)
        assert result["authors"] == []


class TestDoiLookupErrors:
    """Test that the fetch_metadata method handles HTTP errors gracefully."""

    @pytest.mark.asyncio
    async def test_returns_none_on_bad_doi(self):
        service = DoiLookup()
        result = await service.fetch_metadata("not-a-valid-doi")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_input(self):
        service = DoiLookup()
        result = await service.fetch_metadata("")
        assert result is None
