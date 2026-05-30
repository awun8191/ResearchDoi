"""RAST state schemas and data models."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CitationEntry:
    """A single citation entry with multiple format support."""
    key: str
    authors: list[str]
    title: str
    year: str = ""
    journal: str = ""
    doi: str = ""
    url: str = ""
    bibtex: str = ""
    apa: str = ""
    ieee: str = ""


@dataclass
class Paper:
    """A research paper discovered during search."""
    id: str
    title: str
    authors: list[str]
    abstract: str = ""
    published: str = ""
    pdf_link: str = ""
    source: str = ""  # "arxiv", "semantic_scholar", "web"
    findings: list[str] = field(default_factory=list)


@dataclass
class ResearchState:
    """Full session state schema for the RAST research agent."""
    topic: str = ""
    research_plan: dict[str, Any] = field(default_factory=dict)
    papers: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    citations: dict[str, dict[str, Any]] = field(default_factory=dict)
    current_depth: int = 0
    max_depth: int = 5
    completeness_score: float = 0.0
    output_format: str = "report"
    synthesis: str = ""
    outline: str = ""
    formatted_draft: str = ""
    arxiv_results: list[dict[str, Any]] = field(default_factory=list)
    semantic_scholar_results: list[dict[str, Any]] = field(default_factory=list)
    web_results: list[dict[str, Any]] = field(default_factory=list)
    error_log: list[str] = field(default_factory=list)


def default_research_state() -> dict[str, Any]:
    """Return a default research state dict for ADK session state."""
    return {
        "topic": "",
        "research_plan": {},
        "papers": [],
        "findings": [],
        "citations": {},
        "current_depth": 0,
        "max_depth": 5,
        "completeness_score": 0.0,
        "output_format": "report",
        "synthesis": "",
        "outline": "",
        "formatted_draft": "",
        "arxiv_results": [],
        "semantic_scholar_results": [],
        "web_results": [],
        "error_log": [],
    }
