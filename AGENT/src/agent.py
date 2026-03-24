from .lookup.agents import init_state_agent, recursive_research_loop
from .research.agents import (
    thesis_planner,
    create_paper_discovery_agent,
    create_thesis_director,
)
from .research.pipeline import (
    create_research_pipeline,
    create_thesis_section_pipeline,
    FinalBibliographyAgent,
    ThesisFinalizerAgent,
)
from .rag_tools import (
    rag_query,
    list_corpora,
    get_corpus_info,
    add_document_to_corpus, create_corpus,
)
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.agents import SequentialAgent, LlmAgent, BaseAgent
from google.adk.models import Gemini
from google.adk.tools import AgentTool, url_context
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import AsyncGenerator

load_dotenv()

# Model Definitions
GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
GEMINI_3_1_FLASH_LITE = "gemini-3.1-flash-lite-preview"

# Default model for orchestration and minor tasks (us-central1)
gemini_model = Gemini(model=GEMINI_2_5_FLASH_LITE)

# High-performance model for synthesis and writing (global endpoint for preview access)
gemini_writing_model = Gemini(
    model=GEMINI_3_1_FLASH_LITE, base_url="https://aiplatform.googleapis.com"
)

# ── Schemas for AgentTools ───────────────────────────────────────────────────


class ThesisFullPipelineRequest(BaseModel):
    research_topic: str = Field(
        ...,
        description="The main topic for the autonomous 5-chapter thesis generation.",
    )


class WritingSectionRequest(BaseModel):
    research_topic: str = Field(..., description="The main research topic.")
    target_section: str = Field(
        ...,
        description="The specific thesis section to write (e.g. 'Introduction', 'Literature Review').",
    )


class DeepResearchRequest(BaseModel):
    research_topic: str = Field(
        ..., description="The technical topic to perform deep web research on."
    )


class UrlAnalysisRequest(BaseModel):
    url: str = Field(..., description="The specific URL to analyze or summarize.")


class GlobalInitAgent(BaseAgent):
    """Ensures all required session state variables exist before any LlmAgent runs."""

    name: str = "GlobalInitializer"

    async def _run_live_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        async for event in self._run_async_impl(ctx):
            yield event

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Required for instructions formatting
        if "accumulated_research" not in ctx.session.state:
            ctx.session.state["accumulated_research"] = (
                "No research has been accumulated yet."
            )
        if "search_plan" not in ctx.session.state:
            ctx.session.state["search_plan"] = "No search plan generated yet."
        if "evaluation_status" not in ctx.session.state:
            ctx.session.state["evaluation_status"] = {}
        if "retrieved_chunks" not in ctx.session.state:
            ctx.session.state["retrieved_chunks"] = []
        if "discovered_papers" not in ctx.session.state:
            ctx.session.state["discovered_papers"] = []

        # Variables for the Writing/Citation/Review pipeline
        if "review_feedback" not in ctx.session.state:
            ctx.session.state["review_feedback"] = "No feedback yet."
        if "draft_content" not in ctx.session.state:
            ctx.session.state["draft_content"] = ""
        if "final_draft" not in ctx.session.state:
            ctx.session.state["final_draft"] = ""
        if "formatted_context" not in ctx.session.state:
            ctx.session.state["formatted_context"] = ""
        if "source_metadata" not in ctx.session.state:
            ctx.session.state["source_metadata"] = []

        # Variables for the Autonomous Thesis Pipeline
        if "master_thesis_document" not in ctx.session.state:
            ctx.session.state["master_thesis_document"] = "# THE PROJECT THESIS\n\n"
        if "granular_plan" not in ctx.session.state:
            ctx.session.state["granular_plan"] = []
        if "research_topic" not in ctx.session.state:
            # Try to infer topic from session state if available
            ctx.session.state["research_topic"] = "Autonomous Systems"
        if "target_section" not in ctx.session.state:
            ctx.session.state["target_section"] = "General"
        if "url" not in ctx.session.state:
            ctx.session.state["url"] = ""
        if "url_findings" not in ctx.session.state:
            ctx.session.state["url_findings"] = "No URL findings yet."
        if "url_context" not in ctx.session.state:
            ctx.session.state["url_context"] = "No URL context retrieved yet."
        if "thesis_download_url" not in ctx.session.state:
            ctx.session.state["thesis_download_url"] = ""

        for empty_event in []:
            yield empty_event


global_init = GlobalInitAgent()

# ── 1. URL Context Analysis ──────────────────────────────────────────────────

url_analyst_worker = LlmAgent(
    name="UrlAnalystWorker",
    model=gemini_model,
    input_schema=UrlAnalysisRequest,
    instruction="""
    You are a technical URL analyst. 
    Use the `url_context` tool to retrieve and analyze the content of the URL provided: {url}.
    After analysis, control returns to the Orchestrator.
    """,
    tools=[url_context],
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

url_analyst_returner = LlmAgent(
    name="UrlAnalystReturner",
    model=gemini_model,
    instruction="""
    The analysis of the URL is complete.
    
    URL FINDINGS:
    {url_findings}
    
    Summarize these findings for the user. If the findings are empty or indicate an error, explain that you couldn't extract data.
    """,
)

url_analyst = SequentialAgent(
    name="UrlAnalyst", sub_agents=[url_analyst_worker, url_analyst_returner]
)

# ── 2. Deep Web Research ─────────────────────────────────────────────────────

# Standard google_search with PDF filtering
deep_research_pipeline = SequentialAgent(
    name="DeepWebResearch",
    sub_agents=[
        create_paper_discovery_agent(),
        init_state_agent,
        recursive_research_loop,
    ],
)

# Returner now actually summarizes findings from state
deep_research_returner = LlmAgent(
    name="DeepResearchReturner",
    model=gemini_model,
    instruction="""
    The research cycle is complete.
    
    Review the discovered papers and metadata: {discovered_papers}
    And the accumulated research: {accumulated_research}
    
    Provide a comprehensive technical summary of the findings to the user. 
    Include links to the PDF documents identified and key methodologies.
    """,
)

deep_research_agent = SequentialAgent(
    name="AutonomousDeepResearch",
    sub_agents=[deep_research_pipeline, deep_research_returner],
)

# ── 3. Structured Thesis Writing ─────────────────────────────────────────────


structured_writing_pipeline = create_research_pipeline(
    model=gemini_model, writing_model=gemini_writing_model
)

# Ensure the first agent of the writing pipeline has the schema
# Chain: structured_writing_pipeline -> research_agent -> QueryExpansionAgent
structured_writing_pipeline.sub_agents[0].sub_agents[
    0
].input_schema = WritingSectionRequest

writing_pipeline_returner = LlmAgent(
    name="WritingPipelineReturner",
    model=gemini_model,
    instruction="""
    The thesis section has been generated and saved.
    
    Section content: {draft_content}
    Final report: {final_draft}
    
    Summarize the generated section for the user and confirm it has been saved to their project storage.
    """,
)

thesis_writing_agent = SequentialAgent(
    name="ThesisWritingPipeline",
    sub_agents=[structured_writing_pipeline, writing_pipeline_returner],
)

# ── 4. Autonomous Thesis Generator (Phases 1-4) ──────────────────────────────

thesis_section_pipeline = create_thesis_section_pipeline(
    model=gemini_model, writing_model=gemini_writing_model
)

thesis_director = create_thesis_director(thesis_section_pipeline)

autonomous_thesis_pipeline = SequentialAgent(
    name="AutonomousThesisPipeline",
    sub_agents=[
        create_paper_discovery_agent(),
        thesis_planner,
        thesis_director,
        FinalBibliographyAgent(gemini_model),
        ThesisFinalizerAgent(),
    ],
)

thesis_generator_returner = LlmAgent(
    name="ThesisGeneratorReturner",
    model=gemini_model,
    instruction="""
    The full autonomous thesis generation process is complete.
    
    Download URL: {thesis_download_url}
    Granular Plan: {granular_plan}
    
    Present the final results to the user, including the download link and a brief overview of the chapters generated.
    """,
)

autonomous_thesis_agent = SequentialAgent(
    name="AutonomousThesisGenerator",
    sub_agents=[autonomous_thesis_pipeline, thesis_generator_returner],
)

# ── Orchestrator ─────────────────────────────────────────────────────────────


# Explicitly rename the tool objects to be used as tools
thesis_writing_agent.name = "thesis_writing_pipeline"
autonomous_thesis_agent.name = "autonomous_thesis_generator"
deep_research_agent.name = "autonomous_deep_research"
url_analyst.name = "url_analyst"

thesis_writing_agent.description = "Write a single thesis section based on project documents. Requires 'research_topic' and 'target_section'."
autonomous_thesis_agent.description = "Generate a full 5-chapter thesis with automated research and citations. Requires 'research_topic'."
deep_research_agent.description = (
    "Perform deep web research to gather new technical info. Requires 'research_topic'."
)
url_analyst.description = "Analyze or summarize a specific URL. Requires 'url'."

# Wrap sub-agents as tools
thesis_writing_tool = AgentTool(agent=thesis_writing_agent)
autonomous_thesis_tool = AgentTool(agent=autonomous_thesis_agent)
deep_research_tool = AgentTool(agent=deep_research_agent)
url_analyst_tool = AgentTool(agent=url_analyst)

orchestrator_agent = LlmAgent(
    name="the_Orchestrator",
    model=gemini_model,
    instruction="""
    You are "The Orchestrator" for Rast.

    HARD RULE: You MUST call the specialized tools below to handle research and writing tasks. 
    You DO NOT have a tool named `transfer_to_agent`.
    You MUST NOT attempt to use `transfer_to_agent`.
    Instead, invoke the tool names below DIRECTLY using the provided JSON structure.

    AVAILALBLE TOOLS:
    - `autonomous_thesis_generator`: Call this for "generate a full thesis", "write 5 chapters", etc. 
      Input Schema: {"research_topic": "..."}
    - `thesis_writing_pipeline`: Call this for writing a SINGLE specific section (like 'Methodology'). 
      Input Schema: {"research_topic": "...", "target_section": "..."}
    - `autonomous_deep_research`: Call this for technical web research or finding new papers. 
      Input Schema: {"research_topic": "..."}
    - `url_analyst`: Call this for analyzing a provided URL. 
      Input Schema: {"url": "..."}
    
    KNOWLEDGE BASE TOOLS:
    - `rag_query`: Query the knowledge base (RAG corpus) for relevant information. 
      Use this when the user asks about documents, papers, or content that may be in your knowledge base.
      Input Schema: {"query": "...", "corpus_id": "..."}
    - `list_rag_corpora`: List all available knowledge bases.
    - `get_corpus_info`: Get information about a specific knowledge base.
      Input Schema: {"corpus_id": "..."}
    - `add_document_to_corpus`: Add a document to the knowledge base.
      Input Schema: {"gcs_uri": "gs://bucket/document.pdf", "display_name": "...", "corpus_id": "..."}
      
    CRITICAL: If the user provides a System Context indicating a specific `corpus_id`, you MUST use that exact `corpus_id` whenever calling `rag_query`, `get_corpus_info`, or `add_document_to_corpus`.

    If the user just says hello, greet them. For any substantive request, use the tools.
    """,
    tools=[
        autonomous_thesis_tool,
        thesis_writing_tool,
        deep_research_tool,
        url_analyst_tool,
        rag_query,
        list_corpora,
        get_corpus_info,
        add_document_to_corpus,
        create_corpus,
    ],
)

# Entry Point
root_agent = SequentialAgent(
    name="ResearchAssistantApp", sub_agents=[global_init, orchestrator_agent]
)
