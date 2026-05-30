"""Tests for RAST agent data models and citation tools."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models import CitationEntry, Paper, ResearchState
from tools.citation_tools import format_citation_tool, generate_bibliography_tool


class TestModels:
    """Test data model schemas."""

    def test_citation_entry_defaults(self):
        entry = CitationEntry(key="test2024", authors=["Test, A."], title="Test Paper")
        assert entry.key == "test2024"
        assert entry.year == ""
        assert entry.doi == ""

    def test_citation_entry_full(self):
        entry = CitationEntry(
            key="smith2024",
            authors=["Smith, J.", "Doe, J."],
            title="A Study on AI",
            year="2024",
            journal="Journal of AI Research",
            doi="10.1234/ai.2024",
        )
        assert entry.year == "2024"
        assert entry.journal == "Journal of AI Research"

    def test_paper_defaults(self):
        paper = Paper(id="1234", title="Test", authors=["Author"], abstract="Abstract")
        assert paper.source == ""
        assert paper.findings == []

    def test_research_state_defaults(self):
        state = ResearchState(topic="Test Topic")
        assert state.topic == "Test Topic"
        assert state.current_depth == 0
        assert state.max_depth == 5
        assert state.completeness_score == 0.0


class TestCitationTools:
    """Test citation formatting tools — functions expect dicts, fmt= keyword."""

    def _make_entry(self, **kw):
        return {
            "key": kw.get("key", "test"),
            "authors": kw.get("authors", ["Test, A."]),
            "title": kw.get("title", "Test Paper"),
            "year": kw.get("year", "2024"),
            "journal": kw.get("journal", ""),
            "doi": kw.get("doi", ""),
            "url": kw.get("url", ""),
        }

    def test_format_citation_apa(self):
        entry = self._make_entry(
            key="test2024",
            authors=["Smith, J.", "Doe, J."],
            title="A Study on AI",
            year="2024",
            journal="Journal of AI Research",
        )
        result = format_citation_tool.func(entry, fmt="apa")
        assert "Smith" in result.get("formatted", "")

    def test_format_citation_bibtex(self):
        entry = self._make_entry(
            key="test2024",
            authors=["Smith, J.", "Doe, J."],
            title="A Study on AI",
            year="2024",
        )
        result = format_citation_tool.func(entry, fmt="bibtex")
        assert "@" in result.get("formatted", "")

    def test_generate_bibliography(self):
        entries = [
            {"key": "a", "authors": ["Author, A."], "title": "Paper A", "year": "2020"},
            {"key": "b", "authors": ["Author, B."], "title": "Paper B", "year": "2021"},
        ]
        result = generate_bibliography_tool.func(entries, fmt="apa")
        assert "Paper A" in result.get("bibliography", "")
        assert result.get("count", 0) == 2

    def test_append_to_draft(self):
        from tools.state_tools import append_to_draft_tool

        result = append_to_draft_tool.func(
            current_draft="# Existing\n\nText.",
            new_content="New section content.",
            section_header="## New Section",
        )
        assert "New Section" in result.get("draft", "")
        assert result.get("appended_length", 0) > 0

    def test_format_citation_all_formats(self):
        entry = self._make_entry(fmt="all")
        result = format_citation_tool.func(entry, fmt="all")
        assert "formatted" in result


class TestStateTools:
    """Test state management tools."""

    def test_update_state(self):
        from tools.state_tools import update_state_tool

        state = {"topic": "AI", "depth": 0}
        result = update_state_tool.func(state, updates={"depth": 1})
        assert result["depth"] == 1

    def test_identify_gaps(self):
        from tools.state_tools import identify_gaps_tool

        findings = [{"topic": "Transformers", "covered": True}]
        plan = {"sub_topics": ["Transformers", "Attention"], "depth": 3}
        result = identify_gaps_tool.func(findings, plan)
        assert "gaps" in result
        assert "completeness_score" not in result or isinstance(result.get("completeness_score"), float)
