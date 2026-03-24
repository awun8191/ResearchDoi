from typing import AsyncGenerator, Optional, List
from pydantic import BaseModel, Field
from google.genai import types
from google.adk.agents import LlmAgent, BaseAgent, SequentialAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.models import Gemini
from google.adk.tools import exit_loop
from .tools import research_retrieval_tool, save_research_document

# ── Models & Schemas ─────────────────────────────────────────────────────────

class QueryIntent(BaseModel):
    """Schema for the Research Agent's Query Expansion stage."""
    research_topic: str = Field(..., description="The original topic")
    expanded_queries: List[str] = Field(..., description="Multiple semantic queries to improve retrieval coverage")
    task_type: str = Field("thesis section writing", description="Type of task (e.g. 'literature review', 'methodology writing')")
    target_section: Optional[str] = Field(None, description="Targeted thesis section")

# ── Helpers ──────────────────────────────────────────────────────────────────

def create_status_event(author: str, text: str) -> Event:
    """Helper to create a valid ADK Event with text content."""
    return Event(
        author=author,
        content=types.Content(
            role="model",
            parts=[types.Part(text=text)]
        )
    )

# ── 1. Research Agent: Step 1 (Query Expansion) ──────────────────────────────

def create_query_expansion_agent(model: Gemini) -> LlmAgent:
    return LlmAgent(
        name="QueryExpansionAgent",
        model=model,
        instruction="""
        You are the expansion module of a Research Agent.
        Your task is to take a research topic and expand it into 3 distinct, highly technical semantic queries.
        
        If the task is a 'literature review', ensure queries cover:
        1. Historical development/context.
        2. Current state-of-the-art methodologies.
        3. Known research gaps or challenges.
        
        Ensure the queries are optimized for vector similarity search in academic papers.
        """,
        output_schema=QueryIntent,
        output_key="query_intent"
    )

# ── 1. Research Agent: Step 2 & 3 (Vector Retrieval) ─────────────────────────

class MultiQueryRetrievalAgent(BaseAgent):
    """Performs retrieval for each expanded query and aggregates results."""
    name: str = "RetrievalAgent"
    
    async def _run_live_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in self._run_async_impl(ctx):
            yield event

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        intent = ctx.session.state.get("query_intent")
        if not intent:
            yield create_status_event(self.name, "Error: Query intent not found.")
            return

        research_topic = intent.get("research_topic", "Unknown Topic")
        expanded_queries = intent.get("expanded_queries", [research_topic])
        
        project_id = ctx.session.state.get("project_id", "default")
        user_id = ctx.user_id
        
        all_chunks = []
        seen_texts = set()

        for query in expanded_queries:
            yield create_status_event(self.name, f"Retrieving literature for: '{query}'...")
            # Use research_retrieval_tool which returns rich dicts
            chunks = await research_retrieval_tool(
                query=query,
                project_id=project_id,
                uid=user_id,
                top_k=10
            )
            for chunk in chunks:
                # Deduplicate based on text
                if chunk["text"] not in seen_texts:
                    all_chunks.append(chunk)
                    seen_texts.add(chunk["text"])
        
        ctx.session.state["retrieved_chunks"] = all_chunks
        yield create_status_event(self.name, f"Aggregated {len(all_chunks)} unique technical segments.")

# ── 1. Research Agent: Step 4 & 5 (Ranking & Assembly) ───────────────────────

class ContextAssemblyAgent(BaseAgent):
    """Ranks chunks based on similarity, diversity, and section importance."""
    name: str = "ContextAssembly"
    
    async def _run_live_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in self._run_async_impl(ctx):
            yield event

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        chunks = ctx.session.state.get("retrieved_chunks", [])
        if not chunks:
            ctx.session.state["formatted_context"] = "No relevant literature found."
            return

        priority_map = {
            "introduction": 5, "background": 4, "related work": 5,
            "methodology": 3, "method": 3, "results": 2,
            "discussion": 4, "conclusion": 1, "general": 0, "references": -1
        }

        def rank_score(chunk):
            score = chunk.get("score", 0)
            # Try to get section from chunk directly or from its metadata
            section = chunk.get("section", "general").lower()
            boost = priority_map.get(section, 0) * 0.1
            return score + boost

        ranked_chunks = sorted(chunks, key=rank_score, reverse=True)
        top_chunks = ranked_chunks[:20]

        # Group by Paper for structured context
        papers = {}
        for c in top_chunks:
            doi = c.get("doi", "Unknown")
            if doi not in papers:
                papers[doi] = []
            papers[doi].append(c)

        context_text = "### RESEARCH CONTEXT (Grounded in literature)\n\n"
        for doi, p_chunks in papers.items():
            # If the tool returned richer metadata, we'd use it here.
            # Currently it returns text, doi, section, score.
            context_text += f"SOURCE: [DOI: {doi}]\n"
            for c in p_chunks:
                sec = c.get('section', 'General')
                context_text += f"SECTION: {sec}\nCONTENT: {c.get('text')}\n"
            context_text += "\n"

        ctx.session.state["formatted_context"] = context_text
        ctx.session.state["source_metadata"] = list(papers.keys())
        
        for empty_event in []: yield empty_event

# ── 2. Writing Agent ─────────────────────────────────────────────────────────

def create_writing_agent(model: Gemini) -> LlmAgent:
    return LlmAgent(
        name="WritingAgent",
        model=model,
        instruction="""
        You are an academic research assistant writing a university thesis.
        
        TASK: Write a {query_intent[task_type]} for the section '{query_intent[target_section]}' regarding {query_intent[research_topic]}.
        
        CONTEXT:
        {formatted_context}
        
        ACADEMIC STANDARDS:
        1. THEMATIC SYNTHESIS: Do not just list what each paper says. Group findings by theme (e.g. 'Detection Techniques', 'Impact Analysis').
        2. COMPARATIVE ANALYSIS: Compare methodologies across different papers. Identify which methods are more efficient or common.
        3. CRITICAL EVALUATION: Identify research gaps or limitations mentioned in the literature.
        4. GROUNDING: Every technical claim MUST refer to a DOI from the CONTEXT.
        5. CITATION STYLE: Use placeholder format [Author, Year] (e.g. [Smith, 2020]). If authors are unknown, use [DOI].
        6. TONE: Formal academic Markdown.
        
        If the context is insufficient to write a high-quality section, state: "ERROR: Insufficient literature context."
        """,
        output_key="draft_content"
    )

# ── 3. Citation Agent ────────────────────────────────────────────────────────

class CitationAgent(LlmAgent):
    """Replaces placeholders with formatted citations and builds bibliography."""
    def __init__(self, model: Gemini):
        super().__init__(
            name="CitationAgent",
            model=model,
            instruction="""
            You are an academic citation agent.
            
            INPUT DRAFT:
            {draft_content}
            
            SOURCE METADATA:
            {formatted_context}
            
            TASK:
            1. Replace all placeholders like [Author, Year] or [DOI] with proper APA formatted citations.
            2. Build a full "References" section at the end in APA style.
            3. For each reference, include the DOI link.
            
            Ensure the transition from placeholders to final citations is seamless and maintains Markdown formatting.
            """,
            output_key="final_draft"
        )

# ── 4. Reviewer Agent ────────────────────────────────────────────────────────

class ReviewerAgent(LlmAgent):
    """Final quality check specialized for Literature Reviews."""
    def __init__(self, model: Gemini):
        super().__init__(
            name="ReviewerAgent",
            model=model,
            instruction="""
            Review this academic section for university-level quality.
            
            DRAFT:
            {final_draft}
            
            CRITICAL REVIEW CHECKLIST:
            - SYNTHESIS: Does it group by theme? Or is it a sequence of summaries? (Theme-based synthesis is required).
            - GROUNDING: Are technical claims cited?
            - DEPTH: Is the technical detail sufficient for a thesis?
            
            If it meets standards, use 'exit_loop'. 
            Otherwise, provide specific instructions for the WritingAgent to fix the issues.
            """,
            tools=[exit_loop],
            output_key="review_feedback"
        )

# ── 5. Document Assembly Agent ───────────────────────────────────────────────

class DocumentAssemblyAgent(BaseAgent):
    """Saves the final Markdown to project storage."""
    name: str = "DocumentAssembly"
    
    async def _run_live_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in self._run_async_impl(ctx):
            yield event

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        final_text = ctx.session.state.get("final_draft", "")
        intent = ctx.session.state.get("query_intent", {})
        project_id = ctx.session.state.get("project_id", "default")
        user_id = ctx.user_id
        
        if not final_text:
            return

        yield create_status_event(self.name, "Literature Review complete. Finalizing document...")
        
        target_section = intent.get("target_section", "literature_review")
        filename = f"{target_section.replace(' ', '_').lower()}.md"
        
        save_result = await save_research_document(
            filename=filename,
            content=final_text,
            project_id=project_id,
            uid=user_id
        )
        
        if save_result.get("status") == "success":
            yield create_status_event(self.name, f"Thesis section saved to storage: {save_result.get('document_url')}")
        else:
            yield create_status_event(self.name, f"Warning: Could not save to storage: {save_result.get('message')}")
            
        ctx.session.state["final_report"] = final_text

# ── Pipeline Factory ────────────────────────────────────────────────────────

def create_research_pipeline(model: Gemini, writing_model: Gemini) -> SequentialAgent:
    # 1. Research Agent (Expansion, Retrieval, Ranking, Assembly)
    research_agent = SequentialAgent(
        name="ResearchAgent",
        sub_agents=[
            create_query_expansion_agent(model),
            MultiQueryRetrievalAgent(),
            ContextAssemblyAgent()
        ]
    )
    
    # 2. Writing & 3. Citation & Review (Iterative)
    writing_stage = LoopAgent(
        name="WritingAndCitationStage",
        sub_agents=[
            create_writing_agent(writing_model),
            CitationAgent(model),
            ReviewerAgent(model)
        ],
        max_iterations=2
    )
    
    return SequentialAgent(
        name="RastFullPipeline",
        sub_agents=[
            research_agent,
            writing_stage,
            DocumentAssemblyAgent()
        ]
    )

def create_thesis_section_pipeline(model: Gemini, writing_model: Gemini) -> SequentialAgent:
    """
    Specialized pipeline for writing a single thesis section.
    Bypasses QueryExpansion if query_intent is already set.
    """
    # Just the retrieval and writing parts
    return SequentialAgent(
        name="ThesisSectionPipeline",
        sub_agents=[
            # We assume query_intent is already populated by PlanPopperAgent
            MultiQueryRetrievalAgent(),
            ContextAssemblyAgent(),
            LoopAgent(
                name="SectionWritingLoop",
                sub_agents=[
                    create_writing_agent(writing_model),
                    CitationAgent(model),
                    ReviewerAgent(model)
                ],
                max_iterations=2
            )
        ]
    )

class FinalBibliographyAgent(LlmAgent):
    """Phase 4: Extracts citations and generates a bibliography for the entire thesis."""
    def __init__(self, model: Gemini):
        super().__init__(
            name="BibliographyAgent",
            model=model,
            instruction="""
            You are the Final Bibliography Agent.
            
            MASTER THESIS:
            {master_thesis_document}
            
            TASK:
            1. Scan the entire document for APA citations.
            2. Extract all unique DOIs or sources mentioned.
            3. Generate a comprehensive "REFERENCES" section in perfect APA style.
            4. If metadata is missing for a DOI, use your internal knowledge to provide a best-effort citation.
            
            Output ONLY the References section.
            """,
            output_key="final_bibliography"
        )

class ThesisFinalizerAgent(BaseAgent):
    """Combines master document with bibliography and saves to storage."""
    name: str = "ThesisFinalizer"
    
    async def _run_live_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in self._run_async_impl(ctx):
            yield event

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        master_doc = ctx.session.state.get("master_thesis_document", "")
        bibliography = ctx.session.state.get("final_bibliography", "")
        project_id = ctx.session.state.get("project_id", "default")
        user_id = ctx.user_id
        
        full_thesis = master_doc + "\n\n# REFERENCES\n\n" + bibliography
        
        yield create_status_event(self.name, "Finalizing Full Thesis Document...")
        
        filename = "master_thesis.md"
        save_result = await save_research_document(
            filename=filename,
            content=full_thesis,
            project_id=project_id,
            uid=user_id
        )
        
        if save_result.get("status") == "success":
            yield create_status_event(self.name, f"FULL THESIS SAVED: {save_result.get('document_url')}")
            ctx.session.state["thesis_download_url"] = save_result.get("document_url")
        else:
            yield create_status_event(self.name, f"Error saving full thesis: {save_result.get('message')}")
            
        for empty_event in []: yield empty_event
