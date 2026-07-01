import json
from typing import Any, AsyncGenerator
from pydantic import BaseModel

from google.adk.agents import LlmAgent, BaseAgent, SequentialAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.tools.exit_loop_tool import exit_loop
from google.genai import types
from src.research.tools import (
    rag_ingestion_tool,
    mcp_exa_web_search_exa,
    mcp_exa_web_fetch_exa,
    doi_lookup_tool,
    pdf_resolver_tool,
    arxiv_search_tool,
)
from src.config import primary_model, writing_model, create_status_event

# ── Phase 1: Academic Discovery & Ingestion ──────────────────────────────────

def create_academic_search_worker() -> LlmAgent:
    return LlmAgent(
        name="AcademicSearchWorker",
        model=primary_model,
        instruction="""
        Role: Academic Discovery Agent.
        Task: Search for the latest research papers and technical documents on the topic provided in the input or session state.
        
        Use the `arxiv_search_tool` to find the most relevant academic papers on Arxiv.
        Use the `mcp_exa_web_search_exa` tool to find high-quality PDF documents or academic pages across the web.
        If you find a DOI, use `doi_lookup_tool` to get metadata.
        Use `pdf_resolver_tool` if you need to find a direct PDF link for a DOI.
        
        Return a list of discovered papers with their titles, links, and snippets.
        """,
        tools=[arxiv_search_tool, mcp_exa_web_search_exa, mcp_exa_web_fetch_exa, doi_lookup_tool, pdf_resolver_tool],
        output_key="discovered_papers"
    )

class IngestionWorker(BaseAgent):
    """Ingests discovered paper snippets/content into the project's RAG store."""
    name: str = "IngestionWorker"

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        papers = ctx.session.state.get("discovered_papers", [])
        project_id = ctx.session.state.get("project_id", "default")
        uid = ctx.user_id

        if not papers or not isinstance(papers, list):
            yield create_status_event(self.name, "No metadata found to ingest.")
            return

        yield create_status_event(self.name, f"Ingesting research segments into RAG...")

        ingested_count = 0
        for p in papers:
            if not isinstance(p, dict):
                continue
            snippet = p.get("snippet", p.get("text", p.get("summary", "")))
            title = p.get("title", "Untitled")
            link = p.get("link", p.get("url", p.get("pdf_url", "")))

            if not snippet:
                continue

            result = await rag_ingestion_tool(
                text=f"TITLE: {title}\nSNIPPET: {snippet}\nLINK: {link}",
                project_id=project_id,
                uid=uid,
                metadata={"source": "academic_discovery", "link": link}
            )
            if result.get("chunks_stored"):
                ingested_count += 1
        
        yield create_status_event(self.name, f"Successfully indexed {ingested_count} technical segments.")

def create_paper_discovery_agent() -> SequentialAgent:
    return SequentialAgent(
        name="PaperDiscoveryAgent",
        sub_agents=[
            create_academic_search_worker(),
            IngestionWorker()
        ]
    )

paper_discovery_agent = create_paper_discovery_agent()

# ── Phase 2: Thesis Planning ────────────────────────────────────────────────

class ThesisPlan(BaseModel):
    chapter: int
    section: str
    focus: str

class ThesisPlanList(BaseModel):
    plan: list[ThesisPlan]

thesis_planner = LlmAgent(
    name="ThesisPlanner",
    model=primary_model,
    instruction="""
    You are a Thesis Planning Agent.
    Your task is to take a research topic provided in the input or session state and generate a granular 5-chapter thesis plan.
    
    The plan MUST be a list of sections to be written, in order.
    Each section should be a dictionary with:
    - chapter: (int)
    - section: (str)
    - focus: (str)
    
    Ensure the plan is comprehensive and follows standard academic structures.
    """,
    output_schema=ThesisPlanList,
    output_key="granular_plan"
)

# ── Phase 3: Recursive Section Drafting ──────────────────────────────────────

class PlanPopperAgent(BaseAgent):
    """Pops the next section from the granular plan and sets it as the active task."""
    name: str = "PlanPopper"

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        raw_plan = ctx.session.state.get("granular_plan", [])
        
        if hasattr(raw_plan, "plan"):
            plan = raw_plan.plan
        elif isinstance(raw_plan, dict) and "plan" in raw_plan:
            plan = raw_plan["plan"]
        elif isinstance(raw_plan, list):
            plan = raw_plan
        else:
            plan = []

        if not plan:
            ctx.session.state["loop_exit_requested"] = True
            yield create_status_event(self.name, "No more sections in plan. Requesting loop exit.")
            return

        current_section = plan.pop(0)
        if hasattr(current_section, "model_dump"):
            current_section = current_section.model_dump()
        
        ctx.session.state["granular_plan"] = plan 
        ctx.session.state["current_task"] = current_section

        ctx.session.state["query_intent"] = {
            "research_topic": ctx.session.state.get("research_topic", "Thesis"),
            "target_section": current_section.get("section"),
            "task_type": f"Writing Chapter {current_section.get('chapter')}: {current_section.get('section')}",
            "focus": current_section.get("focus")
        }

        yield create_status_event(self.name, f"Next Task: {current_section.get('section')} ({current_section.get('focus')})")

class ThesisAppenderAgent(BaseAgent):
    """Appends the finished section to the master document."""
    name: str = "ThesisAppender"

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        final_draft = ctx.session.state.get("final_draft", "")
        master_doc = ctx.session.state.get("master_thesis_document", "# THE PROJECT THESIS\n\n")

        current_task = ctx.session.state.get("current_task", {})
        section_title = current_task.get("section", "New Section")

        master_doc += f"\n\n## {section_title}\n\n" + final_draft
        ctx.session.state["master_thesis_document"] = master_doc

        yield create_status_event(self.name, f"Appended {section_title} to master document.")

def create_thesis_director(research_pipeline: SequentialAgent) -> LoopAgent:
    """Creates a LoopAgent that iterates over the granular plan."""
    exit_evaluator = LlmAgent(
        name="ExitEvaluator",
        model=primary_model,
        instruction="""
        Check if 'granular_plan' is empty or 'loop_exit_requested' is true.
        If yes, use the 'exit_loop' tool.
        """,
        tools=[exit_loop]
    )

    return LoopAgent(
        name="ThesisDirectorAgent",
        sub_agents=[
            PlanPopperAgent(),
            exit_evaluator,
            research_pipeline,
            ThesisAppenderAgent()
        ],
        max_iterations=25 
    )
