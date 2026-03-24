from typing import AsyncGenerator, List, Dict, Any
from google.adk.agents import LlmAgent, BaseAgent, SequentialAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types
from pydantic import BaseModel, Field
from src.research.tools import semantic_scholar_search_tool, rag_ingestion_tool, serp_api_search_tool
from google.adk.tools import AgentTool, google_search
from google.adk.models.lite_llm import LiteLlm
import json
import os

# Helper for status events
def create_status_event(author: str, text: str) -> Event:
    return Event(
        author=author,
        content=types.Content(
            role="model",
            parts=[types.Part(text=text)]
        )
    )

# ── Phase 2: Granular Master Planning ────────────────────────────────────────

dynamic_planner = LlmAgent(
    name="ResearchPlanner",
    model="gemini-2.5-flash-lite",
    instruction="""
    Role: Lead Research Strategist.
    Task: Analyze the user's research topic and generate a strict 10-point academic research plan.
    
    Constraints:
    1. Output ONLY a numbered list. 
    2. Do NOT include any introductions, explanations, definitions, or conversational filler.
    3. Make each item highly specific and context-aware to the user's topic.

    Required Plan Structure:
    1. Background of Study: [Topic context]
    2. Problem Statement: [Specific relevant problem]
    3. History of the Problem
    4. Literature Review: [Key concepts and technologies]
    5. Objectives
    6. Scope of Study
    7. Limitations
    8. Methodology
    9. Potential Findings
    10. Conclusion
    """,
    output_key="search_plan" 
)

# Use a model that supports structured output well
plan_llm = LiteLlm(model="gemini-2.5-flash-lite")

class ThesisPlannerAgent(BaseAgent):
    """Generates a granular 5-chapter thesis plan as a JSON list."""
    name: str = "ThesisPlanner"
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        topic = ctx.session.state.get("research_topic") or ctx.session.state.get("request", "Autonomous Systems")
        yield create_status_event(self.name, f"Planning thesis for: '{topic}'...")
        
        # We create a temporary LlmAgent to do the heavy lifting
        # This is easier than manually constructing LlmRequest
        planner = LlmAgent(
            name="ThesisPlannerInternal",
            model="gemini-2.5-flash-lite",
            instruction=f"""
            Analyze the research topic "{topic}" and generate a granular 5-chapter thesis plan.
            Each chapter must be broken down into specific academic sections (at least 3-4 sections per chapter).
            
            Output format MUST be a valid JSON array of objects:
            [
              {{"chapter": "1", "section": "1.1 Introduction", "focus": "Broad context..."}},
              ...
            ]
            Return ONLY the JSON array.
            """,
            output_key="temp_plan_json"
        )
        
        # Run the internal agent
        async for event in planner.run_async(ctx):
            # Pass through events if they are text
            if event.content and any(p.text for p in event.content.parts):
                yield event
        
        # Extract and parse the result
        text = ctx.session.state.get("temp_plan_json", "[]").strip()
        
        # Clean markdown if needed
        if text.startswith("```json"):
            text = text[7:]
        if "```" in text:
            text = text.split("```")[0]
        text = text.strip()
        
        try:
            plan = json.loads(text)
            ctx.session.state["granular_plan"] = plan
            yield create_status_event(self.name, f"Generated plan with {len(plan)} sections.")
        except Exception as e:
            yield create_status_event(self.name, f"Error parsing plan: {e}. Raw: {text[:100]}")
            ctx.session.state["granular_plan"] = []

thesis_planner = ThesisPlannerAgent()

# ── Phase 1: Academic Discovery & Ingestion ──────────────────────────────────

class AcademicSearchWorker(BaseAgent):
    """Searches for papers using standard google_search with PDF filters."""
    name: str = "AcademicSearchWorker"
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        topic = ctx.session.state.get("research_topic") or ctx.session.state.get("request", "Autonomous Systems")
        query = f"{topic} research paper filetype:pdf"
        
        yield create_status_event(self.name, f"Executing discovery search: '{query}'...")
        
        try:
            # google_search is an instance of GoogleSearchTool.
            # We bypass the tool_context for internal call as we just want the results.
            results = await google_search.run_async(args={"query": query}, tool_context=None)
        except Exception as e:
            yield create_status_event(self.name, f"Search failed: {e}")
            results = []
        
        ctx.session.state["discovered_papers"] = results
        
        if results:
            yield create_status_event(self.name, f"Found {len(results)} potential research documents.")
        else:
            yield create_status_event(self.name, "No research documents found for this topic.")

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

        yield create_status_event(self.name, f"Ingesting {len(papers)} research segments into RAG...")

        ingested_count = 0
        for p in papers:
            if not isinstance(p, dict): continue
            snippet = p.get("snippet", "")
            title = p.get("title", "Untitled")
            link = p.get("link", "")
            
            if not snippet: continue
            
            result = await rag_ingestion_tool(
                text=f"TITLE: {title}\nSNIPPET: {snippet}\nLINK: {link}",
                project_id=project_id,
                uid=uid,
                metadata={"source": "google_search_pdf", "link": link}
            )
            if result.get("chunks_stored"):
                ingested_count += 1
        
        yield create_status_event(self.name, f"Successfully indexed {ingested_count} technical segments.")

def create_paper_discovery_agent() -> SequentialAgent:
    return SequentialAgent(
        name="PaperDiscoveryAgent",
        sub_agents=[
            AcademicSearchWorker(),
            IngestionWorker()
        ]
    )

paper_discovery_agent = create_paper_discovery_agent()

# ── Phase 3: Recursive Section Drafting ──────────────────────────────────────

class PlanPopperAgent(BaseAgent):
    """Pops the next section from the granular plan and sets it as the active task."""
    name: str = "PlanPopper"

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        plan = ctx.session.state.get("granular_plan", [])
        if not plan or not isinstance(plan, list):
            ctx.session.state["loop_exit_requested"] = True
            for empty_event in []: yield empty_event
            return

        current_section = plan.pop(0)
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

from google.adk.tools import exit_loop

def create_thesis_director(research_pipeline: SequentialAgent) -> LoopAgent:
    """Creates a LoopAgent that iterates over the granular plan."""
    exit_evaluator = LlmAgent(
        name="ExitEvaluator",
        model="gemini-2.5-flash-lite",
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
