"""Citation management tools — formatting, bibliography generation, insertion."""

import re
import logging
from typing import Any

from google.adk.tools import FunctionTool

from models import CitationEntry

logger = logging.getLogger(__name__)

# ── Format Helpers ───────────────────────────────────────────────────────────


def _parse_author_last(full_name: str) -> str:
    """Extract last name from a full author name."""
    name = full_name.strip()
    if not name:
        return "Unknown"
    if "," in name:
        return name.split(",")[0].strip()
    parts = name.split()
    return parts[-1] if parts else name


def _get_initials(full_name: str) -> str:
    """Get initials from a full author name."""
    name = full_name.strip()
    if not name:
        return ""
    if "," in name:
        # Last, First Middle
        parts = name.split(",")
        given = parts[-1].strip() if len(parts) > 1 else ""
        return " ".join(f"{p[0]}." for p in given.split() if p and p[0].isalpha())
    parts = name.split()
    # First Middle Last — skip last
    return " ".join(f"{p[0]}." for p in parts[:-1] if p and p[0].isalpha())


def _format_author_apa(authors: list[str]) -> str:
    """Format authors in APA 7 style."""
    if not authors:
        return "Unknown"
    formatted: list[str] = []
    for author in authors[:20]:
        last = _parse_author_last(author)
        initials = _get_initials(author)
        formatted.append(f"{last}, {initials}".strip().strip(","))
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"


def _format_author_ieee(authors: list[str]) -> str:
    """Format authors in IEEE style."""
    if not authors:
        return "Unknown"
    formatted: list[str] = []
    for author in authors[:6]:
        initials = _get_initials(author)
        last = _parse_author_last(author)
        formatted.append(f"{initials} {last}".strip())
    if len(authors) > 6:
        return ", ".join(formatted) + ", et al."
    if len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    return ", ".join(formatted)


def _make_key(authors: list[str], year: str, title: str) -> str:
    """Generate a citation key from authors, year, and title."""
    first_author = _parse_author_last(authors[0]) if authors else "Unknown"
    year_clean = re.sub(r"[^0-9]", "", year)[:4] if year else "n.d."
    title_short = ""
    if title:
        words = title.split()
        if len(words) >= 3:
            title_short = words[0][:5].lower()
        elif words:
            title_short = words[0][:5].lower()
    key = f"{first_author.lower()}{year_clean}{title_short}"
    return re.sub(r"[^a-z0-9]", "", key)


# ── Core Functions ───────────────────────────────────────────────────────────


def format_citation(
    entry: dict[str, Any],
    fmt: str = "apa",
) -> dict[str, str]:
    """Format a single citation entry in the requested format.

    Args:
        entry: Dict with keys: key, authors, title, year, journal, doi, url.
        fmt: Output format — "apa", "ieee", "bibtex", or "all" (default "apa").

    Returns:
        Dict with 'formatted' key containing the citation string,
        plus individual format keys if fmt='all'.
    """
    authors = entry.get("authors", [])
    title = entry.get("title", "Untitled")
    year = entry.get("year", "n.d.")
    journal = entry.get("journal", "")
    doi = entry.get("doi", "")
    url = entry.get("url", "")
    citation_key = entry.get("key", _make_key(authors, year, title))

    results: dict[str, str] = {}

    # APA 7
    author_str = _format_author_apa(authors)
    apa = f"{author_str} ({year}). {title}."
    if journal:
        apa += f" *{journal}*."
    if doi:
        apa += f" https://doi.org/{doi}"
    elif url:
        apa += f" {url}"
    results["apa"] = apa

    # IEEE
    ieee_author_str = _format_author_ieee(authors)
    ieee = f"{ieee_author_str}, \"{title},\""
    if journal:
        ieee += f" *{journal}*,"
    ieee += f" {year}."
    if doi:
        ieee += f" doi: {doi}."
    results["ieee"] = ieee

    # BibTeX
    bibtex_parts: list[str] = []
    bibtex_parts.append(f"@article{{{citation_key},")
    bibtex_parts.append(f"  author = {{{' and '.join(authors[:20])}}}, " if authors else "")
    bibtex_parts.append(f"  title = {{{title}}},")
    bibtex_parts.append(f"  year = {{{year}}},")
    if journal:
        bibtex_parts.append(f"  journal = {{{journal}}},")
    if doi:
        bibtex_parts.append(f"  doi = {{{doi}}},")
    if url:
        bibtex_parts.append(f"  url = {{{url}}},")
    bibtex_parts.append("}")
    results["bibtex"] = "\n".join(bibtex_parts)

    if fmt == "all":
        result = {"formatted": results.get("apa", ""), "key": citation_key, **results}
    elif fmt == "ieee":
        result = {"formatted": results.get("ieee", ""), "key": citation_key}
    elif fmt == "bibtex":
        result = {"formatted": results.get("bibtex", ""), "key": citation_key}
    else:
        result = {"formatted": results.get("apa", ""), "key": citation_key}

    result["format"] = fmt
    return result


format_citation_tool = FunctionTool(func=format_citation,
)


def generate_bibliography(
    citations: list[dict[str, Any]],
    fmt: str = "apa",
) -> dict[str, Any]:
    """Generate a full bibliography from a list of citation entries.

    Args:
        citations: List of citation entry dicts. Each must have at minimum
                  'authors', 'title', and 'year' keys.
        fmt: Output format — "apa", "ieee", or "bibtex" (default "apa").

    Returns:
        Dict with 'bibliography' (formatted string), 'count' (number of entries),
        and 'format' keys.
    """
    if not citations:
        return {"bibliography": "No citations.", "count": 0, "format": fmt}

    # Sort by first author's last name, then year
    sorted_citations = sorted(
        citations,
        key=lambda c: (
            _parse_author_last((c.get("authors") or ["Unknown"])[0]).lower(),
            str(c.get("year", "")),
        ),
    )

    entries: list[str] = []
    for entry in sorted_citations:
        formatted = format_citation(entry, fmt=fmt)
        entries.append(formatted.get("formatted", ""))

    bibliography = "\n\n".join(entries)

    return {
        "bibliography": bibliography,
        "count": len(entries),
        "format": fmt,
    }


generate_bibliography_tool = FunctionTool(func=generate_bibliography,
)


def insert_citations(
    draft: str,
    citations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Insert citation markers in a draft text.

    Replaces patterns like [CIT: key] with formatted in-text citations.
    Also builds a reference list at the end of the document.

    Args:
        draft: Draft text with [CIT: key] markers.
        citations: List of citation entry dicts.

    Returns:
        Dict with 'text' (updated draft) and 'references' (list of used refs).
    """
    if not draft:
        return {"text": "", "references": [], "reference_count": 0}

    # Build lookup by key
    citation_map: dict[str, dict[str, Any]] = {}
    for c in citations:
        key = c.get("key", "")
        if key:
            citation_map[key] = c

    used_keys: list[str] = []
    used_in_order: list[str] = []

    def replace_cit(match: re.Match) -> str:
        raw = match.group(1)
        keys = [k.strip() for k in re.split(r"[;,]", raw) if k.strip()]
        formatted_cits: list[str] = []
        for k in keys:
            entry = citation_map.get(k)
            if entry:
                if k not in used_keys:
                    used_keys.append(k)
                    used_in_order.append(k)
                authors = entry.get("authors", [])
                year = entry.get("year", "n.d.")
                if not authors:
                    formatted_cits.append(f"({year})")
                elif len(authors) == 1:
                    last = _parse_author_last(authors[0])
                    formatted_cits.append(f"({last}, {year})")
                elif len(authors) == 2:
                    first = _parse_author_last(authors[0])
                    second = _parse_author_last(authors[1])
                    formatted_cits.append(f"({first} & {second}, {year})")
                else:
                    first = _parse_author_last(authors[0])
                    formatted_cits.append(f"({first} et al., {year})")
            else:
                formatted_cits.append(f"({k})")
        return "; ".join(formatted_cits)

    updated = re.sub(r"\[CIT:\s*([^\]]+)\]", replace_cit, draft)

    # Build reference list
    references: list[str] = []
    for k in used_in_order:
        entry = citation_map.get(k, {})
        formatted = format_citation(entry, fmt="apa")
        references.append(formatted.get("formatted", k))

    # Append references if not already present
    if references and "## References" not in updated:
        updated += "\n\n## References\n\n" + "\n\n".join(references)

    return {
        "text": updated,
        "references": references,
        "reference_count": len(references),
    }


insert_citations_tool = FunctionTool(func=insert_citations,
)

# ── All Citation Tools ───────────────────────────────────────────────────────

ALL_CITATION_TOOLS: list[FunctionTool] = [
    format_citation_tool,
    generate_bibliography_tool,
    insert_citations_tool,
]
