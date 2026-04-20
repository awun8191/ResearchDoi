from typing import AsyncGenerator
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.agents import LlmAgent, LoopAgent, BaseAgent, SequentialAgent
from google.adk.tools.exit_loop_tool import exit_loop
from src.research.tools import mcp_exa_web_search_exa, mcp_exa_web_fetch_exa
from dotenv import load_dotenv
from src.config import primary_model, writing_model, create_status_event

load_dotenv()

class InitResearchStateAgent(BaseAgent):
    """Initializes search plan if it doesn't exist."""
    name: str = "InitState"
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        if "accumulated_research" not in ctx.session.state:
            ctx.session.state["accumulated_research"] = "No research has been accumulated yet."
        if "evaluation_status" not in ctx.session.state:
            ctx.session.state["evaluation_status"] = {}
            
        yield create_status_event(self.name, "Research state initialized.")

init_state_agent = InitResearchStateAgent()


evaluator_agent = LlmAgent(
    name="Evaluator",
    model=primary_model,
    instruction="""
    Review the current accumulated research:
    {accumulated_research}
    
    Against the search plan:
    {search_plan}
    
    Identify what is missing or needs deeper technical detail. 
    Generate 2-3 specific search queries to address the gaps.
    
    If the search plan is fulfilled or no significant gaps remain, use the exit_loop tool.
    """,
    tools=[exit_loop, mcp_exa_web_search_exa, mcp_exa_web_fetch_exa],
    output_key="evaluation_status"
)

search_worker = LlmAgent(
    name="SearchWorker",
    model=primary_model,
    instruction="""
    Look at the pending search queries: {evaluation_status}
    Use the `mcp_exa_web_search_exa` tool to find high-quality technical results.
    Return the best URLs and snippets found.
    """,
    tools=[mcp_exa_web_search_exa],
    output_key="search_results"
)

url_reader = LlmAgent(
    name="UrlReader",
    model=primary_model,
    instruction="""
    Analyze the technical search results: {search_results}
    Use the `mcp_exa_web_fetch_exa` tool to read the most promising URLs.
    Extract technical data, methodologies, and citations.
    """,
    tools=[mcp_exa_web_fetch_exa],
    output_key="url_findings"
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
        
        yield create_status_event(self.name, "Appended new findings to accumulated research.")

memory_manager = MemoryAppenderAgent()

# Add it to your loop so it runs AFTER the deep_searcher!
recursive_research_loop = LoopAgent(
    name="DeepResearchLoop",
    sub_agents=[evaluator_agent, deep_searcher, memory_manager],
    max_iterations=10 
)
