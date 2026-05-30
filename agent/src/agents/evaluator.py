"""Paper evaluation — PaperReaderPool, FindingsMerger, and PaperEvaluationLoop."""

from typing import Any

from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent
from google.adk.tools import FunctionTool

from litellm_config import reasoning_llm, fast_llm
from tools.search_tools import read_paper_tool, extract_findings_tool
from tools.state_tools import update_state_tool, identify_gaps_tool

# ── Helper to create dynamic paper reader agents ─────────────────────────────


def create_paper_reader_agent(paper: dict[str, Any]) -> LlmAgent:
    """Create a PaperReader agent for a single paper.

    Args:
        paper: Dict with id, title, authors, abstract, pdf_link keys.

    Returns:
        An LlmAgent configured to read and evaluate this paper.
    """
    paper_id = paper.get("id", "unknown")
    paper_title = paper.get("title", "Untitled")
    paper_abstract = paper.get("abstract", "")
    paper_pdf_link = paper.get("pdf_link", "")

    return LlmAgent(
        name=f"PaperReader_{paper_id}",
        model=reasoning_llm,
        instruction=f"""You are evaluating a research paper for relevance to the current research.

Paper ID: {paper_id}
Title: {paper_title}
Abstract: {paper_abstract}
PDF Link: {paper_pdf_link}

Your task:
1. Read the abstract thoroughly. If the PDF link is available and accessible, use read_paper to fetch the full text.
2. Use extract_findings to extract structured findings from the paper content.
3. Evaluate the paper's relevance to the research topic (stored in state['topic']).
4. Assign a relevance score from 0.0 (irrelevant) to 1.0 (highly relevant).
5. Store findings using the update_state tool with key 'findings' (updates will be merged).

Return a JSON summary with:
- paper_id
- relevance_score
- key_findings (list of strings)
- methodology_notes (string)
- recommended_for_synthesis (bool)
""",
        tools=[read_paper_tool, extract_findings_tool, update_state_tool],
        output_key=f"paper_findings_{paper_id}",
    )


# ── Paper Reader Pool (ParallelAgent with dynamic sub-agents) ────────────────

# Note: PaperReaderPool is created dynamically per iteration in the loop.
# The static instance below serves as a template; in the orchestrator,
# paper_reader_pool.sub_agents is set to dynamically created reader agents.
paper_reader_pool = ParallelAgent(
    name="PaperReaderPool",
)

# ── Findings Merger ──────────────────────────────────────────────────────────

findings_merger = LlmAgent(
    name="FindingsMerger",
    model=reasoning_llm,
    instruction="""You are a Findings Merger. Your job is to consolidate findings from all paper readers.

1. Read all paper findings from state — look for keys matching 'paper_findings_*'.
2. Merge overlapping findings — similar findings from different papers should be combined.
3. Identify key themes and patterns across the papers.
4. Calculate a completeness score (0.0-1.0) based on:
   - How many sub-topics from the research plan are covered
   - How many papers were found vs. the target depth
   - How many high-quality findings were extracted
5. Update state['findings'] with the consolidated findings.
6. Update state['completeness_score'] with the calculated score.
7. Use the identify_gaps tool to find remaining gaps.
8. Store identified gaps in state for the next iteration.

The completeness score should consider:
- 0.0-0.3: Early stage, many gaps remain
- 0.3-0.6: Moderate coverage, some gaps
- 0.6-0.85: Good coverage, minor gaps
- 0.85-1.0: Comprehensive, ready for synthesis

Return a JSON summary with:
- completeness_score
- themes_identified (list)
- gaps_remaining (list)
- papers_evaluated (int)
- ready_for_synthesis (bool)
""",
    tools=[update_state_tool, identify_gaps_tool],
    output_key="findings_summary",
)

# ── Paper Evaluation Loop (LoopAgent) ────────────────────────────────────────

paper_evaluation_loop = LoopAgent(
    name="PaperEvaluationLoop",
    sub_agents=[
        paper_reader_pool,
        findings_merger,
    ],
    max_iterations=5,
)
