from typing import AsyncGenerator
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.agents import LlmAgent, LoopAgent, BaseAgent, SequentialAgent
from google.adk.models import Gemini
from google.adk.tools import google_search, exit_loop, url_context
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Confirmed model name for research lookup tasks
MODEL_NAME = "gemini-2.5-flash-lite"

class InitResearchStateAgent(BaseAgent):
    """Initializes search plan if it doesn't exist."""
    name: str = "InitState"
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        if "accumulated_research" not in ctx.session.state:
            ctx.session.state["accumulated_research"] = "No research has been accumulated yet."
        if "evaluation_status" not in ctx.session.state:
            ctx.session.state["evaluation_status"] = {}
            
        for empty_event in []:
            yield empty_event

init_state_agent = InitResearchStateAgent()


evaluator_agent = LlmAgent(
    name="Evaluator",
    model=MODEL_NAME,
    instruction="""
    Review the current accumulated research:
    {accumulated_research}
    
    Against the search plan:
    {search_plan}
    
    Identify what is missing or needs deeper technical detail. 
    Generate 2-3 specific search queries to address the gaps.
    
    If the search plan is fulfilled or no significant gaps remain, use the exit_loop tool.
    """,
    tools=[exit_loop],
    output_key="evaluation_status"
)

# Search tool and Transfer tools cannot be mixed in the same agent on Vertex AI.
# We disable automatic transfers for these agents to allow built-in tools.
search_worker = LlmAgent(
    name="SearchWorker",
    model=MODEL_NAME,
    instruction="""
    Look at the pending search queries: {evaluation_status}
    Use the google_search tool to find high-quality technical results.
    Return the best URLs and snippets found.
    """,
    tools=[google_search],
    output_key="search_results",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

# A specialized URL content analyst.
url_reader = LlmAgent(
    name="UrlReader",
    model=MODEL_NAME,
    instruction="""
    Analyze the technical search results: {search_results}
    Use the url_context tool to read the most promising URLs.
    Extract technical data, methodologies, and citations.
    """,
    tools=[url_context],
    output_key="url_findings",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)

# This agent orchestrates the search and read steps.
deep_searcher = SequentialAgent(
    name="DeepSearcher",
    sub_agents=[search_worker, url_reader]
)


class MemoryAppenderAgent(BaseAgent):
    """Appends new findings to the accumulated research."""
    name: str = "MemoryAppender"
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        findings = ctx.session.state.get("url_findings", "No new findings.")
        current = ctx.session.state.get("accumulated_research", "")
        ctx.session.state["accumulated_research"] = current + "\n\n" + str(findings)
        
        for empty_event in []:
            yield empty_event

memory_manager = MemoryAppenderAgent()

# Add it to your loop so it runs AFTER the deep_searcher!
recursive_research_loop = LoopAgent(
    name="DeepResearchLoop",
    sub_agents=[evaluator_agent, deep_searcher, memory_manager],
    max_iterations=10 
)
