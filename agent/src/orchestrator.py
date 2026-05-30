"""RAST Master Orchestrator — ties all ADK agents into a single research pipeline.

Architecture:
    RASTController (LlmAgent - Master)
    ├── ResearchPlanner (LlmAgent)
    ├── SearchOrchestrator (ParallelAgent)
    │   ├── ArxivSearchAgent (LlmAgent)
    │   ├── SemanticScholarAgent (LlmAgent)
    │   └── WebSearchAgent (LlmAgent)
    ├── PaperEvaluationLoop (LoopAgent)
    │   ├── PaperReaderPool (ParallelAgent, dynamic sub-agents)
    │   └── FindingsMerger (LlmAgent)
    └── SynthesisPipeline (SequentialAgent)
        ├── OutlineAgent (LlmAgent)
        ├── DraftAgent (LlmAgent)
        ├── CitationIntegrator (LlmAgent)
        └── QualityReviewAgent (LlmAgent)
"""

import logging

from google.adk.agents import LlmAgent

from openrouter_adapter import register_openrouter_models
from agents.planner import research_planner
from agents.searchers import search_orchestrator
from agents.evaluator import paper_evaluation_loop
from agents.synthesis import synthesis_pipeline
from openrouter_adapter import register_openrouter_models
from tools.state_tools import update_state_tool

logger = logging.getLogger(__name__)

# Register OpenRouter models with ADK's LLMRegistry
register_openrouter_models()

RAST_MASTER_INSTRUCTION = """You are RAST — the Research Assistant agent.

Your job is to conduct academic research for the user. You follow a structured pipeline:

1. **ResearchPlanner** — First, transfer to ResearchPlanner to create a structured research plan from the user's topic
2. **SearchOrchestrator** — Then transfer to SearchOrchestrator to find papers from arXiv, Semantic Scholar, and web sources
3. **PaperEvaluationLoop** — Then transfer to PaperEvaluationLoop to read papers, extract findings, and loop until research is comprehensive
4. **SynthesisPipeline** — Finally, transfer to SynthesisPipeline to write the output (report, chapter, paper, or thesis)

Monitor the research state via context.state to track progress. If errors occur, report them to the user and attempt recovery.
"""

rast_controller = LlmAgent(
    name="RASTController",
    model="openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    instruction=RAST_MASTER_INSTRUCTION,
    sub_agents=[
        research_planner,
        search_orchestrator,
        paper_evaluation_loop,
        synthesis_pipeline,
    ],
    tools=[update_state_tool],
)

__all__ = ["rast_controller"]
