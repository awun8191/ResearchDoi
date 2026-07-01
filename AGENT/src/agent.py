from src.lookup.agents import init_state_agent, recursive_research_loop
from src.research.agents import (
    thesis_planner,
    create_paper_discovery_agent,
    create_thesis_director,
)
from src.research.pipeline import (
    create_research_pipeline,
    create_thesis_section_pipeline,
    FinalBibliographyAgent,
    ThesisFinalizerAgent,
)
from src.research.tools import mcp_exa_web_search_exa, mcp_exa_web_fetch_exa
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.agents import SequentialAgent, LlmAgent, BaseAgent
from google.adk.tools.transfer_to_agent_tool import TransferToAgentTool
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import re
from typing import AsyncGenerator, Optional
from src.config import primary_model, writing_model, init_session_state, create_status_event
from google.genai import types as genai_types

load_dotenv()

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
        # Initialize session state using centralized helper
        init_session_state(ctx.session.state)
        
        is_initialized = ctx.session.state.get("__initialized__", False)
        if not is_initialized:
            ctx.session.state["__initialized__"] = True
            yield create_status_event(self.name, "Session state initialized.")


global_init = GlobalInitAgent()

# ── 1. URL Context Analysis ──────────────────────────────────────────────────

url_analyst_worker = LlmAgent(
    name="UrlAnalystWorker",
    model=primary_model,
    input_schema=UrlAnalysisRequest,
    instruction="""
    You are a technical URL analyst. 
    Use the `mcp_exa_web_fetch_exa` tool to retrieve and analyze the content of the URL provided in the input or session state.
    After analysis, control returns to the Orchestrator.
    """,
    tools=[mcp_exa_web_fetch_exa],
    output_key="url_findings",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

url_analyst_returner = LlmAgent(
    name="UrlAnalystReturner",
    model=primary_model,
    instruction="""
    The analysis of the URL is complete.
    
    Review the findings in the session state and summarize them for the user. 
    If the findings indicate an error or are missing, explain that you couldn't extract data.
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
    model=primary_model,
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
    model=primary_model, writing_model=writing_model
)

# Ensure the first agent of the writing pipeline has the schema
# Chain: structured_writing_pipeline -> research_agent -> QueryExpansionAgent
research_agent = structured_writing_pipeline.sub_agents[0]
if isinstance(research_agent, SequentialAgent):
    query_expansion_agent = research_agent.sub_agents[0]
    if isinstance(query_expansion_agent, LlmAgent):
        query_expansion_agent.input_schema = WritingSectionRequest

writing_pipeline_returner = LlmAgent(
    name="WritingPipelineReturner",
    model=primary_model,
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
    model=primary_model, writing_model=writing_model
)

thesis_director = create_thesis_director(thesis_section_pipeline)

autonomous_thesis_pipeline = SequentialAgent(
    name="AutonomousThesisPipeline",
    sub_agents=[
        create_paper_discovery_agent(),
        thesis_planner,
        thesis_director,
        FinalBibliographyAgent(primary_model),
        ThesisFinalizerAgent(),
    ],
)

thesis_generator_returner = LlmAgent(
    name="ThesisGeneratorReturner",
    model=primary_model,
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

def _set_input_schema(agent: BaseAgent, schema) -> None:
    """Recursively set input_schema on the first LlmAgent in a SequentialAgent chain."""
    if isinstance(agent, LlmAgent):
        agent.input_schema = schema
    elif isinstance(agent, SequentialAgent) and agent.sub_agents:
        _set_input_schema(agent.sub_agents[0], schema)
    # If a LoopAgent or custom BaseAgent, skip (schema assignment doesn't apply)


# Set input schemas so TransferToAgentTool can extract arguments from the user's prompt
_set_input_schema(thesis_writing_agent, WritingSectionRequest)
_set_input_schema(autonomous_thesis_agent, ThesisFullPipelineRequest)
_set_input_schema(deep_research_agent, DeepResearchRequest)
_set_input_schema(url_analyst, UrlAnalysisRequest)


thesis_writing_agent.description = "Write a single thesis section based on project documents. Requires 'research_topic' and 'target_section'."
autonomous_thesis_agent.description = "Generate a full 5-chapter thesis with automated research and citations. Requires 'research_topic'."
deep_research_agent.description = (
    "Perform deep web research to gather new technical info. Requires 'research_topic'."
)
url_analyst.description = "Analyze or summarize a specific URL. Requires 'url'."

# Use a single TransferToAgentTool for all handoffs
transfer_tool = TransferToAgentTool(agent_names=[
    "thesis_writing_pipeline",
    "autonomous_thesis_generator",
    "autonomous_deep_research",
    "url_analyst"
])


# ── Explicit routing callback ───────────────────────────────────────────────
# Runs before the LLM, pattern-matches the user message and injects a
# function_call to transfer_to_agent — no token cost for unambiguous cases.


async def routing_callback(
    callback_context,  # CallbackContext
) -> Optional[genai_types.Content]:
    """Pre-LLM routing: match keywords in the user message and transfer directly."""
    ctx = callback_context
    user_content = ctx.user_content
    if not user_content or not user_content.parts:
        return None

    text = ""
    for part in user_content.parts:
        if part.text:
            text += part.text

    if not text:
        return None

    t = text.strip().lower()

    # Rule 1: URL present → URL analyst
    if re.search(r"https?://[^\s]+", text):
        return genai_types.Content(
            parts=[genai_types.Part.from_function_call(
                name="transfer_to_agent",
                args={"agent_name": "url_analyst"},
            )],
            role="assistant",
        )

    # Rule 2: Section writing keywords → thesis writing pipeline
    if re.search(
        r"write\s+(?:a\s+)?(?:thesis\s+)?(?:section|chapter|introduction"
        r"|methodology|results?|conclusion|literature review|abstract|discussion)",
        t,
    ):
        return genai_types.Content(
            parts=[genai_types.Part.from_function_call(
                name="transfer_to_agent",
                args={"agent_name": "thesis_writing_pipeline"},
            )],
            role="assistant",
        )

    # Rule 3: Full thesis keywords → thesis generator
    if re.search(
        r"(?:full|complete|entire|whole|generate|draft)\s+(?:thesis|paper|dissertation)"
        r"|5[\s-]?chapter|autonomous thesis",
        t,
    ):
        return genai_types.Content(
            parts=[genai_types.Part.from_function_call(
                name="transfer_to_agent",
                args={"agent_name": "autonomous_thesis_generator"},
            )],
            role="assistant",
        )

    # Rule 4: Research keywords → deep research
    if re.search(
        r"(?:find|search|look\s+up|discover|research|hunt)"
        r"\s+(?:papers?|research|articles?|publications?|literature|doi|arxiv|topic)",
        t,
    ):
        return genai_types.Content(
            parts=[genai_types.Part.from_function_call(
                name="transfer_to_agent",
                args={"agent_name": "autonomous_deep_research"},
            )],
            role="assistant",
        )

    # No match — let the LLM orchestrator handle it
    return None


orchestrator_agent = LlmAgent(
    name="the_Orchestrator",
    model=primary_model,
    before_agent_callback=[routing_callback],
    instruction="""
    You are "The Orchestrator" for Rast.

    Your task is to coordinate research and writing requests. 
    Use the `transfer_to_agent` tool to hand off control to the most appropriate specialized agent.

    AVAILABLE AGENTS FOR TRANSFER:
    - `autonomous_thesis_generator`: Use for generating a full 5-chapter thesis.
    - `thesis_writing_pipeline`: Use for writing a SINGLE specific section (e.g., 'Methodology').
    - `autonomous_deep_research`: Use for technical web research or finding new papers.
    - `url_analyst`: Use for analyzing or summarizing a provided URL.
    
    Before transferring, ensure you have the necessary information (like 'research_topic' or 'url') from the user.
    If the user just says hello, greet them and explain your capabilities.
    """,
    sub_agents=[
        thesis_writing_agent,
        autonomous_thesis_agent,
        deep_research_agent,
        url_analyst,
    ],
    tools=[transfer_tool],
)

# Entry Point
root_agent = SequentialAgent(
    name="ResearchAssistantApp", sub_agents=[global_init, orchestrator_agent]
)
