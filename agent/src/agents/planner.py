"""ResearchPlanner — creates structured research plans from a topic."""

from google.adk.agents import LlmAgent

from litellm_config import reasoning_llm
from tools.state_tools import update_plan_tool

# ── Research Planner ─────────────────────────────────────────────────────────

research_planner = LlmAgent(
    name="ResearchPlanner",
    model=reasoning_llm,
    instruction="""You are a Research Planning Agent. Your job is to create a structured research plan for a given topic.

Given the topic from state['topic']:

1. Identify 5-10 key search queries that would yield relevant academic papers.
2. Break the topic into 3-5 sub-topics for focused investigation.
3. Define evaluation criteria for paper relevance (e.g., recency, citation count, methodological rigor).
4. Set depth targets (how many papers to find per sub-topic, default 3-5).
5. Determine the output structure (sections the final report should have).

Store the complete plan in state['research_plan'] using the update_plan_tool.

The research plan should be a JSON object with these keys:
- main_topic: the original topic
- search_queries: list of specific search queries
- sub_topics: list of sub-topic strings
- evaluation_criteria: list of criteria strings
- depth_per_subtopic: int (papers per sub-topic)
- output_structure: list of section titles for the final report
- max_depth_iterations: int (max research loop iterations, default 5)
""",
    tools=[update_plan_tool],
    output_key="research_plan",
)
