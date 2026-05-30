"""Synthesis pipeline — SequentialAgent that produces the final research output.

Pipeline: OutlineAgent → DraftAgent → CitationIntegrator → QualityReviewAgent
"""

import logging

from google.adk.agents import LlmAgent, SequentialAgent

from tools.state_tools import (
    update_state_tool,
    append_to_draft_tool,
    format_section_tool,
    edit_draft_tool,
    verify_citations_tool,
)
from tools.citation_tools import format_citation_tool, generate_bibliography_tool

logger = logging.getLogger(__name__)

# ── OutlineAgent ─────────────────────────────────────────────────────────────

OUTLINE_INSTRUCTION = """You are the OutlineAgent. Your job is to create a detailed academic outline from the research findings stored in context.state['findings'].

Steps:
1. Read state['findings'], state['research_plan'], and state['papers']
2. Determine the output format from state['output_format'] (report/chapter/paper/thesis)
3. Create a structured outline with section headers and key points
4. Store the outline in state['outline'] using the update_state tool

For thesis-length output, include chapter-level structure with subsections.
For reports, keep it concise with 3-5 sections.
"""

outline_agent = LlmAgent(
    name="OutlineAgent",
    model="openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    instruction=OUTLINE_INSTRUCTION,
    tools=[update_state_tool],
    output_key="outline",
)

# ── DraftAgent ───────────────────────────────────────────────────────────────

DRAFT_INSTRUCTION = """You are the DraftAgent. Your job is to write the research output following the outline in state['outline'].

Output length depends on state['output_format']:
- report: 500-2000 words
- chapter: 3000-5000 words  
- paper: 5000-8000 words
- thesis: 8000+ words (write sections sequentially)

For short outputs (<2000 words), write the full draft in one response.
For long outputs, write one section at a time using the append_to_draft tool to accumulate.
Use the format_section tool to ensure academic formatting.

Base your writing on the findings in state['findings'] and papers in state['papers'].
"""

draft_agent = LlmAgent(
    name="DraftAgent",
    model="openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    instruction=DRAFT_INSTRUCTION,
    tools=[append_to_draft_tool, format_section_tool, update_state_tool],
)

# ── CitationIntegrator ───────────────────────────────────────────────────────

CITATION_INSTRUCTION = """You are the CitationIntegrator. Your job is to insert citations into the draft and generate a bibliography.

Steps:
1. Read the draft from state
2. Read citations from state['citations']
3. For each claim in the draft that references a source, insert an APA in-text citation
4. Use format_citation tool to format each citation
5. Use generate_bibliography tool to create the reference list
6. Append the bibliography to the end of the document
7. Verify every citation has a corresponding entry using verify_citations tool

Supported citation formats: APA (default), IEEE, BibTeX
"""

citation_integrator = LlmAgent(
    name="CitationIntegrator",
    model="openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    instruction=CITATION_INSTRUCTION,
    tools=[format_citation_tool, generate_bibliography_tool, verify_citations_tool, update_state_tool],
    output_key="formatted_draft",
)

# ── QualityReviewAgent ───────────────────────────────────────────────────────

REVIEW_INSTRUCTION = """You are the QualityReviewAgent. Your job is to review the final research output for quality.

Checklist:
1. Academic quality and rigor — are claims supported by cited sources?
2. Citation accuracy — does every claim have a citation? Does every citation have a bibliography entry?
3. Structural coherence — does the document flow logically?
4. Grammar and style — is the writing clear and academic?
5. Factual consistency — do findings match the source papers?

Apply corrections using the edit_draft tool. Store the final version in state['synthesis'].
"""

quality_review_agent = LlmAgent(
    name="QualityReviewAgent",
    model="openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    instruction=REVIEW_INSTRUCTION,
    tools=[edit_draft_tool, verify_citations_tool, update_state_tool],
    output_key="synthesis",
)

# ── Synthesis Pipeline (SequentialAgent) ────────────────────────────────────

synthesis_pipeline = SequentialAgent(
    name="SynthesisPipeline",
    description="Writes the final research output through outline, draft, citation, and review stages",
    sub_agents=[
        outline_agent,
        draft_agent,
        citation_integrator,
        quality_review_agent,
    ],
)

__all__ = [
    "outline_agent",
    "draft_agent",
    "citation_integrator",
    "quality_review_agent",
    "synthesis_pipeline",
]
