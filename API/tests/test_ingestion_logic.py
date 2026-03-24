import pytest
from src.service.ingestion import _segment_into_sections

def test_segment_into_sections_basic():
    md_text = """# Introduction
This is the intro.

## Methodology
We did some things.

### Data Collection
Specifically this data.

# Results
Found 42.

# Conclusion
Final thoughts.
"""
    sections = _segment_into_sections(md_text)
    
    # Expected categories: introduction, methodology, methodology (for Data Collection), results, conclusion
    # Note: _segment_into_sections maps headers to categories.
    
    section_names = [s["section"] for s in sections]
    
    assert "introduction" in section_names
    assert "methodology" in section_names
    assert "results" in section_names
    assert "conclusion" in section_names
    
    # Check content of intro
    intro = next(s for s in sections if s["section"] == "introduction")
    assert "This is the intro." in intro["text"]

def test_segment_into_sections_no_headers():
    md_text = "Just some random text without headers."
    sections = _segment_into_sections(md_text)
    
    assert len(sections) == 1
    assert sections[0]["section"] == "general"
    assert sections[0]["text"] == md_text

def test_segment_into_sections_varied_headers():
    md_text = """# 1. Background and Related Work
Some background here.

# 4. Experimental Results
The results are clear.
"""
    sections = _segment_into_sections(md_text)
    section_names = [s["section"] for s in sections]
    
    assert "background" in section_names or "related work" in section_names
    assert "results" in section_names
