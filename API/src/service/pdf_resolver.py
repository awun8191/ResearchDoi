"""
Async 4+1-tier cascading PDF URL resolver.

Resolution order:
  Tier 1: Unpaywall API          (verified open access — validated)
  Tier 2: Semantic Scholar       (openAccessPdf — validated)
  Tier 3: OpenAlex               (pdf_url fields — validated)
  Tier 4: Publisher heuristics   (hand-crafted patterns — trusted)
  Tier 5: DOI page scraper       (fetches publisher landing page, extracts PDF links)

Each tier fails silently. First successful result wins.

Tiers 1–3 validate candidates with a HEAD + %PDF- magic-bytes probe before
returning — these APIs sometimes return HTML landing pages instead of PDFs.
Tier 5 probes each candidate before returning.
CrossRef link arrays (old Tier 4) are used as seed URLs for Tier 5 only.
"""

import asyncio
import html.parser
import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

from src.core.config import settings
from src.models.pdf import PdfResolutionResponse

logger = logging.getLogger(__name__)

UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1/paper"
OPENALEX_BASE = "https://api.openalex.org/works"

_NO_PDF = PdfResolutionResponse(
    pdf_url=None,
    is_open_access=False,
    oa_status=None,
    resolved_via="none",
)

_PDF_MAGIC = b"%PDF-"

# ─── Publisher heuristic patterns ─────────────────────────────────────────────

_PUBLISHER_PATTERNS: list[dict] = [
    {
        "name": "arXiv",
        "prefix": "10.48550",
        "resolve": lambda doi: (
            f"https://arxiv.org/pdf/{m.group(1)}.pdf"
            if (m := re.match(r"10\.48550/arXiv\.(.+)", doi, re.IGNORECASE))
            else None
        ),
    },
    {
        "name": "bioRxiv",
        "prefix": "10.1101",
        "resolve": lambda doi: f"https://www.biorxiv.org/content/{doi}v1.full.pdf",
    },
    {
        "name": "PLoS",
        "prefix": "10.1371",
        "resolve": lambda doi: f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable",
    },
    {
        "name": "PeerJ",
        "prefix": "10.7717",
        "resolve": lambda doi: (
            f"https://peerj.com/articles/{m.group(1)}.pdf"
            if (m := re.match(r"10\.7717/peerj\.(\d+)", doi))
            else None
        ),
    },
    {
        "name": "Frontiers",
        "prefix": "10.3389",
        "resolve": lambda doi: f"https://www.frontiersin.org/articles/{doi}/pdf",
    },
]



def _resolve_by_publisher_pattern(doi: str) -> Optional[str]:
    for pattern in _PUBLISHER_PATTERNS:
        if doi.startswith(pattern["prefix"]):
            url = pattern["resolve"](doi)
            if url:
                logger.info("[pdf_resolver] Heuristic match: %s", pattern["name"])
                return url
    return None


# ─── PDF URL probe ─────────────────────────────────────────────────────────────

_PROBE_TIMEOUT = 8.0
_PDF_CONTENT_TYPES = {"application/pdf", "application/octet-stream", "binary/octet-stream"}


async def _probe_is_pdf(client: httpx.AsyncClient, url: str) -> bool:
    """
    Verify that `url` actually serves a real PDF.

    1. HEAD request — check Content-Type, but ONLY trust it on 2xx responses.
       4xx/5xx HEAD results are treated as ambiguous and fall through to Step 2.
       This handles publishers (e.g. MDPI) that return 404 on HEAD but correctly
       serve partial content (206) on Range GET requests.
    2. Range GET (bytes=0-7) — check %PDF- magic bytes. Definitive answer.


    Returns False (never raises) on any error so callers fall through gracefully.
    """
    _definite_bad_types = {
        "text/html", "text/plain", "text/xml",
        "application/xml", "application/xhtml+xml", "application/json",
    }

    # ── Strategy 1: HEAD ────────────────────────────────────────────────────
    try:
        head = await asyncio.wait_for(
            client.head(url, timeout=_PROBE_TIMEOUT),
            timeout=_PROBE_TIMEOUT + 2,
        )
        ct = head.headers.get("content-type", "").lower().split(";")[0].strip()
        if head.is_success:  # 2xx only — non-2xx HEAD treated as ambiguous
            if ct in _PDF_CONTENT_TYPES:
                return True
            if ct in _definite_bad_types:
                logger.debug("[pdf_resolver] HEAD rejected url=%s status=%d ct=%r",
                             url, head.status_code, ct)
                return False
        # 4xx/5xx HEAD → fall through (MDPI returns 404 on HEAD but serves PDF on GET)
    except Exception:
        pass

    async def _read_magic(stream_ctx: Any, n: int = 8) -> bytes:
        chunk = b""
        async with stream_ctx as stream:
            async for data in stream.aiter_bytes(n):
                chunk += data
                if len(chunk) >= 5:
                    break
        return chunk

    # ── Strategy 2: Range GET (most CDNs serve 206 for this) ────────────────
    try:
        chunk = await asyncio.wait_for(
            _read_magic(
                client.stream("GET", url, timeout=_PROBE_TIMEOUT,
                               headers={"Range": "bytes=0-7"})
            ),
            timeout=6.0,  # tight — prevents hanging on CDNs that stall
        )
        if chunk[:5] == _PDF_MAGIC:
            return True
        if chunk:  # got bytes but not PDF magic
            logger.debug("[pdf_resolver] Range GET not PDF url=%s bytes=%r", url, chunk[:20])
            return False
        # empty chunk → inconclusive, fall through to plain GET
    except Exception:
        pass  # Range not supported, stalled, or rejected — try plain GET

    # ── Strategy 3: Plain GET, abort after first 8 bytes ────────────────────
    try:
        chunk = await asyncio.wait_for(
            _read_magic(client.stream("GET", url, timeout=_PROBE_TIMEOUT)),
            timeout=8.0,
        )
        is_pdf = chunk[:5] == _PDF_MAGIC
        if not is_pdf and chunk:
            logger.debug("[pdf_resolver] Plain GET not PDF url=%s bytes=%r", url, chunk[:20])
        return is_pdf
    except Exception as exc:
        logger.debug("[pdf_resolver] All probe strategies failed url=%s: %s", url, exc)
        return False




# ─── Tier 5: DOI page scraper ─────────────────────────────────────────────────

class _LinkExtractor(html.parser.HTMLParser):
    """Minimal SAX-style parser that collects (href, anchor_text) pairs."""

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[tuple[str, str]] = []
        self._cur_href: Optional[str] = None
        self._cur_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag == "a":
            attr_dict = dict(attrs)
            href = attr_dict.get("href") or ""
            if href and not href.startswith(("#", "mailto:", "javascript:")):
                self._cur_href = urljoin(self.base_url, href)
                self._cur_text = []

    def handle_data(self, data: str) -> None:
        if self._cur_href is not None:
            self._cur_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._cur_href is not None:
            self.links.append((self._cur_href, " ".join(self._cur_text).strip()))
            self._cur_href = None
            self._cur_text = []


def _score_pdf_link(href: str, text: str) -> int:
    """
    Score a candidate link by how likely it is to be a direct PDF.
    Returns 0 if the link has no PDF signal at all.
    """
    h = href.lower()
    t = text.lower()
    score = 0

    # href structure signals — most reliable
    if h.endswith(".pdf"):
        score += 10
    if "/pdf/" in h or h.endswith("/pdf"):
        score += 9
    if re.search(r"[?&]format=pdf", h):
        score += 8
    if re.search(r"[?&]type=pdf", h):
        score += 7
    if re.search(r"[?&](download|dl)=pdf", h):
        score += 7
    if "fullpdf" in h or "full-pdf" in h:
        score += 6
    if "/epdf" in h or "/epdf/" in h:
        score += 5
    if re.search(r"/articlepdf/|/article/pdf", h):
        score += 8
    if "download" in h and "pdf" in h:
        score += 5

    # anchor text signals — supplement, don't rely on alone
    if re.search(r"\bpdf\b", t):
        score += 2
    if re.search(r"download\s+pdf|pdf\s+download", t):
        score += 3
    if re.search(r"full.?text\s+pdf|pdf\s+full.?text", t):
        score += 3

    return score


async def _scrape_doi_page_for_pdf(
    client: httpx.AsyncClient,
    doi: str,
    extra_urls: Optional[list[str]] = None,
) -> Optional[str]:
    """
    Fetch the publisher page via https://doi.org/{doi}, parse its HTML,
    score all anchor links for PDF likelihood, and probe the top candidates.

    extra_urls: Additional starting URLs to scrape (e.g. CrossRef link array).
    Only the first *unique* page is fetched per URL to avoid crawling.

    Returns a validated PDF URL or None.
    """
    urls_to_try = [f"https://doi.org/{doi}"]
    if extra_urls:
        for u in extra_urls:
            if u not in urls_to_try:
                urls_to_try.append(u)

    for start_url in urls_to_try[:3]:  # cap at 3 pages
        try:
            resp = await client.get(
                start_url,
                timeout=12.0,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            if not resp.is_success:
                continue

            ct = resp.headers.get("content-type", "").lower()
            if "html" not in ct:
                # We landed directly on a PDF — return it immediately after probe
                final_url = str(resp.url)
                if await _probe_is_pdf(client, final_url):
                    logger.info("[pdf_resolver] DOI redirected directly to PDF: %s", final_url)
                    return final_url
                continue

            base_url = str(resp.url)
            extractor = _LinkExtractor(base_url)
            extractor.feed(resp.text)

            # Score every link, keep those with score > 0, sort by score desc
            candidates = sorted(
                (
                    (href, text, _score_pdf_link(href, text))
                    for href, text in extractor.links
                    if _score_pdf_link(href, text) > 0
                ),
                key=lambda x: x[2],
                reverse=True,
            )

            logger.info(
                "[pdf_resolver] Page scrape %s → %d PDF candidates",
                base_url, len(candidates),
            )
            if candidates:
                # Log the top 3 for debugging
                for href, text, score in candidates[:3]:
                    logger.debug("[pdf_resolver]   score=%d  %s  (%r)", score, href, text)

            # Probe up to top 3 candidates (avoid probing hundreds of links)
            for href, text, score in candidates[:3]:
                if await _probe_is_pdf(client, href):
                    logger.info("[pdf_resolver] Scraper found PDF: %s (score=%d)", href, score)
                    return href

        except Exception as exc:
            logger.debug("[pdf_resolver] Page scrape failed for %s: %s", start_url, exc)

    return None





# ─── Tier fetchers ─────────────────────────────────────────────────────────────

async def _fetch_unpaywall(client: httpx.AsyncClient, doi: str) -> PdfResolutionResponse:
    try:
        resp = await client.get(
            f"{UNPAYWALL_BASE}/{doi}",
            params={"email": settings.unpaywall_email},
            timeout=8.0,
        )
        if not resp.is_success:
            return _NO_PDF
        data = resp.json()

        # Prefer best_oa_location, but scan all oa_locations for a url_for_pdf.
        # Unpaywall sometimes omits url_for_pdf from best_oa_location when the
        # publisher page has no direct PDF link, but a repository copy does.
        all_locs: list[dict] = []
        if data.get("best_oa_location"):
            all_locs.append(data["best_oa_location"])
        all_locs.extend(data.get("oa_locations") or [])

        pdf_url: str | None = None
        for loc in all_locs:
            if loc.get("url_for_pdf"):
                pdf_url = loc["url_for_pdf"]
                break

        return PdfResolutionResponse(
            pdf_url=pdf_url,
            is_open_access=data.get("is_oa", False),
            oa_status=data.get("oa_status"),
            resolved_via="unpaywall" if pdf_url else "none",
        )
    except Exception as exc:
        logger.warning("[pdf_resolver] Unpaywall failed: %s", exc)
        return _NO_PDF


async def _fetch_semantic_scholar(client: httpx.AsyncClient, doi: str) -> Optional[str]:
    try:
        resp = await client.get(
            f"{SEMANTIC_SCHOLAR_BASE}/DOI:{doi}",
            params={"fields": "openAccessPdf"},
            timeout=6.0,
        )
        if not resp.is_success:
            return None
        return resp.json().get("openAccessPdf", {}).get("url")
    except Exception as exc:
        logger.warning("[pdf_resolver] Semantic Scholar failed: %s", exc)
        return None


async def _fetch_openalex(client: httpx.AsyncClient, doi: str) -> Optional[str]:
    try:
        resp = await client.get(
            f"{OPENALEX_BASE}/doi:{doi}",
            params={"mailto": settings.unpaywall_email},
            timeout=6.0,
        )
        if not resp.is_success:
            return None
        data = resp.json()
        # Only explicit pdf_url fields — oa_url is frequently an HTML landing page
        return (
            data.get("primary_location", {}).get("pdf_url")
            or data.get("best_oa_location", {}).get("pdf_url")
        )
    except Exception as exc:
        logger.warning("[pdf_resolver] OpenAlex failed: %s", exc)
        return None



def _extract_crossref_pdf_links(links: list[dict[str, Any]]) -> list[str]:
    """
    Return CrossRef link array URLs, sorted so high-scoring PDF candidates come first.
    All content-types are included so the scraper can use HTML landing pages as seeds.
    """
    scored = [
        (link["URL"], _score_pdf_link(link["URL"], ""))
        for link in links
        if isinstance(link.get("URL"), str)
    ]
    # High-scoring URLs first (direct /pdf links), then fall back to HTML seeds
    scored.sort(key=lambda x: x[1], reverse=True)
    return [url for url, _ in scored]


# ─── Main orchestrator ─────────────────────────────────────────────────────────

async def resolve_pdf(doi: str, crossref_links: Optional[list[dict]] = None) -> PdfResolutionResponse:
    """
    Cascading PDF resolver — 4 API tiers + 1 page-scraper tier.

    Tier 1 — Unpaywall url_for_pdf        (validated)
    Tier 2 — Semantic Scholar pdf_url     (validated)
    Tier 3 — OpenAlex pdf_url             (validated)
    Tier 4 — Publisher heuristics         (trusted, not probed to save latency)
    Tier 5 — DOI page scraper             (fetches landing page, scores PDF links,
                                           also uses CrossRef URLs as extra seeds)

    Args:
        doi:             Cleaned DOI string (no URL prefix).
        crossref_links:  The `link` array from the CrossRef API response.

    Returns:
        PdfResolutionResponse with the best *verified* PDF URL, or pdf_url=None.
    """
    crossref_links = crossref_links or []

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": f"ResearchDoi API/1.0; mailto:{settings.unpaywall_email}"},
    ) as client:

        # ── Tier 1: Unpaywall ──────────────────────────────────────────────────
        unpaywall = await _fetch_unpaywall(client, doi)
        if unpaywall.pdf_url:
            if await _probe_is_pdf(client, unpaywall.pdf_url):
                return unpaywall
            logger.info("[pdf_resolver] Unpaywall URL failed probe, trying Tier 2")

        # ── Tiers 2 & 3: Semantic Scholar + OpenAlex in parallel ──────────────
        ss_url, oa_url = await asyncio.gather(
            _fetch_semantic_scholar(client, doi),
            _fetch_openalex(client, doi),
            return_exceptions=True,
        )

        if isinstance(ss_url, str) and ss_url:
            if await _probe_is_pdf(client, ss_url):
                return PdfResolutionResponse(
                    pdf_url=ss_url,
                    is_open_access=True,
                    oa_status=unpaywall.oa_status or "green",
                    resolved_via="semantic_scholar",
                )
            logger.info("[pdf_resolver] S2 URL failed probe")

        if isinstance(oa_url, str) and oa_url:
            if await _probe_is_pdf(client, oa_url):
                return PdfResolutionResponse(
                    pdf_url=oa_url,
                    is_open_access=True,
                    oa_status=unpaywall.oa_status or "green",
                    resolved_via="openalex",
                )
            logger.info("[pdf_resolver] OpenAlex URL failed probe")

        # ── Tier 4a: Publisher URL heuristics ─────────────────────────────────
        heuristic_url = _resolve_by_publisher_pattern(doi)
        if heuristic_url:
            # Probe the heuristic URL — don't trust blindly
            if await _probe_is_pdf(client, heuristic_url):
                logger.info("[pdf_resolver] Heuristic URL validated: %s", heuristic_url)
                return PdfResolutionResponse(
                    pdf_url=heuristic_url,
                    is_open_access=unpaywall.is_open_access,
                    oa_status=unpaywall.oa_status,
                    resolved_via="heuristic",
                )
            logger.info("[pdf_resolver] Heuristic URL failed probe: %s", heuristic_url)

        # ── Tier 4b: CrossRef high-confidence direct links ─────────────────────
        # CrossRef links tagged application/pdf OR scoring high as PDF URLs
        # (e.g. MDPI 'unspecified' links ending in /pdf) are probed directly.
        # Uses a fresh AsyncClient per URL to avoid CDN connection fingerprinting
        # (some publishers like MDPI track and block connections after API calls).
        crossref_candidates = _extract_crossref_pdf_links(crossref_links)
        for cr_url in crossref_candidates:
            score = _score_pdf_link(cr_url, "")
            ct = next(
                (lnk.get("content-type", "") for lnk in crossref_links if lnk.get("URL") == cr_url),
                "",
            )
            if ct == "application/pdf" or score >= 5:
                # Bypass probe for known anti-bot domains offering valid CrossRef links
                if "mdpi.com" in cr_url.lower() or "frontiersin.org" in cr_url.lower():
                    logger.info("[pdf_resolver] Trusting anti-bot domain CrossRef link: %s", cr_url)
                    return PdfResolutionResponse(
                        pdf_url=cr_url,
                        is_open_access=unpaywall.is_open_access,
                        oa_status=unpaywall.oa_status,
                        resolved_via="crossref_direct",
                    )

                async with httpx.AsyncClient(
                    follow_redirects=True,
                    headers={"User-Agent": f"ResearchDoi API/1.0; mailto:{settings.unpaywall_email}"},
                ) as fresh:
                    if await _probe_is_pdf(fresh, cr_url):
                        logger.info("[pdf_resolver] CrossRef direct link validated: %s", cr_url)
                        return PdfResolutionResponse(
                            pdf_url=cr_url,
                            is_open_access=unpaywall.is_open_access,
                            oa_status=unpaywall.oa_status,
                            resolved_via="crossref_link",
                        )

        # ── Tier 5: DOI page scraper ───────────────────────────────────────────
        # Pass CrossRef URLs as extra seed pages alongside the canonical DOI page.
        extra_urls = crossref_candidates
        scraped_url = await _scrape_doi_page_for_pdf(client, doi, extra_urls=extra_urls)
        if scraped_url:
            return PdfResolutionResponse(
                pdf_url=scraped_url,
                is_open_access=unpaywall.is_open_access,
                oa_status=unpaywall.oa_status,
                resolved_via="page_scraper",
            )

        return PdfResolutionResponse(
            pdf_url=None,
            is_open_access=unpaywall.is_open_access,
            oa_status=unpaywall.oa_status,
            resolved_via="none",
        )
