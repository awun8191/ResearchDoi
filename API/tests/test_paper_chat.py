"""
Tests for the paper chat service — resolution, extraction, and chat flow.
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.service import paper_chat


class TestPaperChatResolution:
    """Test the paper resolution logic with mocked external services."""

    @pytest.mark.asyncio
    async def test_resolve_via_arxiv(self):
        """Should resolve via ArXiv first, then return metadata."""
        mock_arxiv = AsyncMock(return_value={
            "doi": "2301.12345",
            "title": "ArXiv Paper Title",
            "authors": ["Author One", "Author Two"],
            "publication_year": 2023,
            "venue": "ArXiv",
            "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
        })

        with patch("src.service.paper_chat.ArxivLookup.fetch_metadata_async", mock_arxiv):
            result = await paper_chat._resolve_paper("2301.12345")

        assert result["doi"] == "2301.12345"
        assert result["title"] == "ArXiv Paper Title"
        assert "Author One" in result["authors"]

    @pytest.mark.asyncio
    async def test_falls_back_to_crossref_when_arxiv_fails(self):
        """Should fall back to CrossRef if ArXiv returns None."""
        mock_arxiv = AsyncMock(return_value=None)
        mock_crossref = AsyncMock(return_value={
            "doi": "10.1038/nature12345",
            "title": "Nature Paper",
            "authors": ["Author Three"],
            "publication_year": 2022,
            "venue": "Nature",
        })

        with (
            patch("src.service.paper_chat.ArxivLookup.fetch_metadata_async", mock_arxiv),
            patch("src.service.paper_chat.DoiLookup.fetch_metadata", mock_crossref),
        ):
            result = await paper_chat._resolve_paper("10.1038/nature12345")

        assert result["doi"] == "10.1038/nature12345"
        assert result["title"] == "Nature Paper"

    @pytest.mark.asyncio
    async def test_raises_on_no_resolution(self):
        """Should raise ValueError when no provider can resolve."""
        mock_arxiv = AsyncMock(return_value=None)
        mock_crossref = AsyncMock(return_value=None)

        with (
            patch("src.service.paper_chat.ArxivLookup.fetch_metadata_async", mock_arxiv),
            patch("src.service.paper_chat.DoiLookup.fetch_metadata", mock_crossref),
        ):
            with pytest.raises(ValueError, match="Could not resolve paper"):
                await paper_chat._resolve_paper("10.0/unknown")

    @pytest.mark.asyncio
    async def test_attempts_pdf_resolution_when_no_pdf_url_in_metadata(self):
        """Should call pdf_resolver when metadata has no pdf_url."""
        mock_arxiv = AsyncMock(return_value={
            "doi": "10.1234/test",
            "title": "Test Paper",
            "authors": [],
        })
        mock_pdf = AsyncMock(return_value=type('obj', (object,), {
            "pdf_url": "https://example.com/paper.pdf",
            "is_open_access": True,
        })())

        with (
            patch("src.service.paper_chat.ArxivLookup.fetch_metadata_async", mock_arxiv),
            patch("src.service.paper_chat.resolve_pdf", mock_pdf),
        ):
            result = await paper_chat._resolve_paper("10.1234/test")

        assert result["pdf_url"] == "https://example.com/paper.pdf"
        assert result.get("is_open_access") is True


class TestPaperChatTextExtraction:
    """Test the download and extraction helpers."""

    @pytest.mark.asyncio
    async def test_download_and_extract_returns_text(self):
        """Should return text from load_web_page."""
        mock_load = AsyncMock(return_value="This is the extracted paper text.")

        with patch("src.service.paper_chat.load_web_page", mock_load):
            text = await paper_chat._download_and_extract_text("https://arxiv.org/pdf/2301.12345.pdf")

        assert text == "This is the extracted paper text."

    @pytest.mark.asyncio
    async def test_raises_on_failed_extraction(self):
        """Should raise ValueError when text extraction returns nothing."""
        mock_load = AsyncMock(return_value=None)

        with patch("src.service.paper_chat.load_web_page", mock_load):
            with pytest.raises(ValueError, match="Could not extract text"):
                await paper_chat._download_and_extract_text("https://example.com/broken.pdf")

    @pytest.mark.asyncio
    async def test_truncates_overly_long_text(self):
        """Should truncate text that exceeds MAX_PAPER_CHARS."""
        long_text = "x" * (paper_chat.MAX_PAPER_CHARS + 1000)
        mock_load = AsyncMock(return_value=long_text)

        with patch("src.service.paper_chat.load_web_page", mock_load):
            text = await paper_chat._download_and_extract_text("https://example.com/long.pdf")

        assert len(text) <= paper_chat.MAX_PAPER_CHARS


class TestPaperChatFullFlow:
    """Integration-style tests for the full chat_about_paper flow."""

    @pytest.mark.asyncio
    async def test_full_flow_with_text(self):
        """Should resolve, extract, and return a response."""
        mock_arxiv = AsyncMock(return_value={
            "doi": "10.1234/test",
            "title": "Test Paper",
            "authors": ["Test Author"],
            "publication_year": 2024,
            "pdf_url": "https://arxiv.org/pdf/test.pdf",
        })
        mock_extract = AsyncMock(return_value="Full paper text here.")
        mock_openrouter = AsyncMock(return_value="This is a summary of the paper.")

        with (
            patch("src.service.paper_chat.ArxivLookup.fetch_metadata_async", mock_arxiv),
            patch("src.service.paper_chat._download_and_extract_text", mock_extract),
            patch("src.service.paper_chat._openrouter_chat", mock_openrouter),
        ):
            result = await paper_chat.chat_about_paper(
                paper_id="10.1234/test",
                user_message="Summarize this paper",
            )

        assert result["reply"] == "This is a summary of the paper."
        assert result["title"] == "Test Paper"
        assert result["authors"] == ["Test Author"]

    @pytest.mark.asyncio
    async def test_full_flow_without_pdf(self):
        """Should use abstract/metadata when PDF is not available."""
        mock_arxiv = AsyncMock(return_value={
            "doi": "10.1234/abstract-only",
            "title": "Abstract Only Paper",
            "authors": [],
            "publication_year": 2024,
            "abstract": "This is the abstract.",
        })
        mock_openrouter = AsyncMock(return_value="Response based on abstract.")

        with (
            patch("src.service.paper_chat.ArxivLookup.fetch_metadata_async", mock_arxiv),
            patch("src.service.paper_chat._openrouter_chat", mock_openrouter),
        ):
            result = await paper_chat.chat_about_paper(
                paper_id="10.1234/abstract-only",
                user_message="What is this about?",
            )

        assert result["reply"] == "Response based on abstract."
        assert result["title"] == "Abstract Only Paper"

    @pytest.mark.asyncio
    async def test_raises_on_unresolvable_paper(self):
        """Should propagate ValueError from _resolve_paper."""
        mock_arxiv = AsyncMock(return_value=None)
        mock_crossref = AsyncMock(return_value=None)

        with (
            patch("src.service.paper_chat.ArxivLookup.fetch_metadata_async", mock_arxiv),
            patch("src.service.paper_chat.DoiLookup.fetch_metadata", mock_crossref),
        ):
            with pytest.raises(ValueError, match="Could not resolve paper"):
                await paper_chat.chat_about_paper(
                    paper_id="totally/invalid",
                    user_message="hi",
                )


class TestOpenRouterChat:
    """Test the OpenRouter API call helper."""

    @pytest.mark.asyncio
    async def test_returns_text_from_response(self):
        """Should extract text from a mock OpenRouter response."""
        mock_response = {
            "choices": [
                {
                    "message": {"content": "Hello, I am an AI assistant."}
                }
            ]
        }

        async def mock_post(*args, **kwargs):
            class FakeResp:
                def raise_for_status(self):
                    pass
                def json(self):
                    return mock_response
            return FakeResp()

        with patch("httpx.AsyncClient.post", mock_post):
            result = await paper_chat._openrouter_chat(
                messages=[{"role": "user", "content": "Hi"}]
            )

        assert result == "Hello, I am an AI assistant."
