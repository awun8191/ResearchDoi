import httpx
import logging
import re
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def is_pdf_url(url: str) -> bool:
    """Check if the URL points to a PDF file."""
    url_lower = url.lower()
    return url_lower.endswith(".pdf") or "application/pdf" in url_lower


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> Optional[str]:
    """
    Extracts text from PDF bytes using pymupdf4llm.
    Used by both URL download and file upload.
    """
    try:
        import fitz
        import pymupdf4llm

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        md_text = pymupdf4llm.to_markdown(doc)
        doc.close()

        if not md_text:
            logger.warning("[web_loader] No text extracted from PDF bytes")
            return None

        return str(md_text)
    except Exception as exc:
        logger.error(f"[web_loader] Exception extracting PDF text: {exc}")
        return None


async def load_pdf(url: str) -> Optional[str]:
    """
    Downloads and extracts text from a PDF URL using pymupdf4llm.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/pdf,text/html,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            if not resp.is_success:
                logger.error(
                    f"[web_loader] Failed to download PDF {url}: HTTP {resp.status_code}"
                )
                return None

            pdf_bytes = resp.content

            # Check if it's actually a PDF
            if len(pdf_bytes) < 5 or pdf_bytes[:5] != b"%PDF-":
                logger.warning(f"[web_loader] URL does not appear to be a PDF: {url}")
                return None

            return extract_text_from_pdf_bytes(pdf_bytes)

    except Exception as exc:
        logger.error(f"[web_loader] Exception extracting PDF {url}: {exc}")
        return None


async def load_web_page(url: str) -> Optional[str]:
    """
    Fetches the content from a URL and extracts the clean text.
    Handles both HTML pages and PDF documents.
    """
    # Check if it's a PDF URL
    if is_pdf_url(url):
        logger.info(f"[web_loader] Detected PDF URL, using PDF extraction: {url}")
        return await load_pdf(url)

    headers = {
        "User-Agent": "ResearchDoi (Scientific Research Assistant)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            if not resp.is_success:
                logger.error(f"[web_loader] Failed to fetch {url}: {resp.status_code}")
                return None

            # Check content-type header
            content_type = resp.headers.get("content-type", "").lower()
            if "application/pdf" in content_type:
                logger.info(
                    f"[web_loader] Content-type is PDF, using PDF extraction: {url}"
                )
                return await load_pdf(url)

            # Use BeautifulSoup to clean the HTML
            soup = BeautifulSoup(resp.content, "html.parser")

            # Remove scripts, styles, and navigation to reduce noise
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            # Extract text with a newline separator
            text = soup.get_text(separator="\n", strip=True)

            # Post-process: Filter out short lines (usually UI noise)
            lines = []
            for line in text.splitlines():
                line = line.strip()
                if len(line.split()) > 3:  # Basic heuristic for narrative text
                    lines.append(line)

            cleaned_text = "\n\n".join(lines)

            if not cleaned_text:
                logger.warning(f"[web_loader] No meaningful text extracted from {url}")
                return None

            return cleaned_text

    except Exception as exc:
        logger.error(f"[web_loader] Exception fetching {url}: {exc}")
        return None


if __name__ == "__main__":
    import asyncio

    asyncio.run(load_web_page("https://doi.org/10.18280/ijepm.100215"))
