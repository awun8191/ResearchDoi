"""Search agents — ArxivSearchAgent, SemanticScholarAgent, WebSearchAgent wrapped in SearchOrchestrator."""

from google.adk.agents import LlmAgent, ParallelAgent

from litellm_config import fast_llm
from tools.search_tools import (
    arxiv_search_tool,
    semantic_scholar_search_tool,
    web_search_tool,
)

# ── Arxiv Search Agent ───────────────────────────────────────────────────────

arxiv_search_agent = LlmAgent(
    name="ArxivSearchAgent",
    model=fast_llm,
    instruction="""You are an arXiv search specialist.

Your task:
1. Read the research plan from state['research_plan'].
2. Use the search queries in research_plan.search_queries to search arXiv.
3. For each query, call the arxiv_search tool with max_results=5.
4. Compile a deduplicated list of papers found.
5. Store the results in state['arxiv_results'].

Return a summary of how many papers were found.
""",
    tools=[arxiv_search_tool],
    output_key="arxiv_results",
)

# ── Semantic Scholar Search Agent ────────────────────────────────────────────

semantic_scholar_agent = LlmAgent(
    name="SemanticScholarAgent",
    model=fast_llm,
    instruction="""You are a Semantic Scholar search specialist.

Your task:
1. Read the research plan from state['research_plan'].
2. Use the search queries in research_plan.search_queries to search Semantic Scholar.
3. For each query, call the semantic_scholar_search tool with max_results=5.
4. Compile a deduplicated list of papers found.
5. Store the results in state['semantic_scholar_results'].

Return a summary of how many papers were found.
""",
    tools=[semantic_scholar_search_tool],
    output_key="semantic_scholar_results",
)

# ── Web Search Agent ─────────────────────────────────────────────────────────

web_search_agent = LlmAgent(
    name="WebSearchAgent",
    model=fast_llm,
    instruction="""You are a web search specialist for grey literature and additional papers.

Your task:
1. Read the research plan from state['research_plan'].
2. Use the search queries in research_plan.search_queries to search the web.
3. For each query, call the web_search tool with max_results=5.
4. Compile a deduplicated list of papers found from additional sources.
5. Store the results in state['web_results'].

Return a summary of how many papers were found.
""",
    tools=[web_search_tool],
    output_key="web_results",
)

# ── Search Orchestrator (ParallelAgent) ──────────────────────────────────────

search_orchestrator = ParallelAgent(
    name="SearchOrchestrator",
    sub_agents=[
        arxiv_search_agent,
        semantic_scholar_agent,
        web_search_agent,
    ],
)
