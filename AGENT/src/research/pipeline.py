import json
import re
from typing import Any, AsyncGenerator, Dict, List, Mapping, Optional
from pydantic import BaseModel, Field
from google.genai import types
from google.adk.agents import LlmAgent, BaseAgent, SequentialAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.models import Gemini
from google.adk.tools.exit_loop_tool import exit_loop
from src.research.tools import _normalize_doi, research_retrieval_tool, save_research_document, semantic_scholar_search_tool
from src.config import primary_model, writing_model, create_status_event

# ── Models & Schemas ─────────────────────────────────────────────────────────

class QueryIntent(BaseModel):
    """Schema for the Research Agent's Query Expansion stage."""
    research_topic: str = Field(..., description="The original topic")
    expanded_queries: List[str] = Field(..., description="Multiple semantic queries to improve retrieval coverage")
    task_type: str = Field("thesis section writing", description="Type of task (e.g. 'literature review', 'methodology writing')")
    target_section: Optional[str] = Field(None, description="Targeted thesis section")

# ── Helpers ──────────────────────────────────────────────────────────────────

def _fallback_source_id(title: Any, chunk_text: Any) -> str:
    seed = title or (str(chunk_text or "")[:80])
    slug = re.sub(r"[^a-z0-9]+", "-", str(seed).lower()).strip("-")
    return f"source:{slug[:48]}" if slug else "source:unknown"


def _coerce_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _ensure_source_metadata(source: Dict[str, Any]) -> Dict[str, Any]:
    doi = _normalize_doi(source.get("doi"))
    source_id = source.get("source_id") or doi or _fallback_source_id(source.get("title"), source.get("abstract"))
    return {
        "source_id": source_id,
        "title": source.get("title") or "Untitled source",
        "authors": [a for a in (source.get("authors") or []) if a],
        "year": source.get("year"),
        "venue": source.get("venue"),
        "doi": doi,
        "doi_url": source.get("doi_url") or (f"https://doi.org/{doi}" if doi else None),
        "abstract": source.get("abstract"),
        "paper_id": source.get("paper_id"),
        "citations": source.get("citations"),
        "matched_queries": list(dict.fromkeys(source.get("matched_queries") or [])),
    }


def _merge_source_metadata(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    for key in ("title", "year", "venue", "doi", "doi_url", "abstract", "paper_id", "citations"):
        if not merged.get(key) and incoming.get(key):
            merged[key] = incoming[key]

    merged["authors"] = list(
        dict.fromkeys((merged.get("authors") or []) + (incoming.get("authors") or []))
    )
    merged["matched_queries"] = list(
        dict.fromkeys((merged.get("matched_queries") or []) + (incoming.get("matched_queries") or []))
    )
    return merged


def _format_authors_inline(authors: List[str]) -> str:
    return ", ".join(authors) if authors else "Unknown authors"


def _format_source_catalog(source_metadata: List[Dict[str, Any]]) -> str:
    return json.dumps(source_metadata, indent=2, ensure_ascii=True)


def _parse_author_name(full_name: str) -> tuple[str, List[str]]:
    cleaned = (full_name or "").strip()
    if not cleaned:
        return "Unknown", []

    if "," in cleaned:
        last, given = [part.strip() for part in cleaned.split(",", 1)]
        initials = [f"{part[0]}." for part in given.split() if part and part[0].isalpha()]
        return last or "Unknown", initials

    parts = cleaned.split()
    if len(parts) == 1:
        return parts[0], []

    return parts[-1], [f"{part[0]}." for part in parts[:-1] if part and part[0].isalpha()]


def _format_reference_authors(authors: List[str]) -> str:
    if not authors:
        return "Unknown"

    formatted = []
    for author in authors[:20]:
        last, initials = _parse_author_name(author)
        initials_text = " ".join(initials)
        formatted.append(f"{last}, {initials_text}".strip().rstrip(","))

    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"


def _format_in_text_citation(source: Dict[str, Any]) -> str:
    authors = source.get("authors") or []
    year = source.get("year") or "n.d."

    if not authors:
        lead = source.get("title") or source.get("doi") or source.get("source_id") or "Unknown"
        return f"({lead}, {year})"
    if len(authors) == 1:
        lead = _parse_author_name(authors[0])[0]
        return f"({lead}, {year})"
    if len(authors) == 2:
        first = _parse_author_name(authors[0])[0]
        second = _parse_author_name(authors[1])[0]
        return f"({first} & {second}, {year})"

    lead = _parse_author_name(authors[0])[0]
    return f"({lead} et al., {year})"


def _format_reference_entry(source: Dict[str, Any]) -> str:
    authors = _format_reference_authors(source.get("authors") or [])
    year = source.get("year") or "n.d."
    title = (source.get("title") or "Untitled source").strip().rstrip(".")
    venue = (source.get("venue") or "").strip()
    doi_url = source.get("doi_url")

    reference = f"{authors} ({year}). {title}."
    if venue:
        reference += f" *{venue}*."
    if doi_url:
        reference += f" {doi_url}"
    return reference.strip()


def _build_source_aliases(source: Dict[str, Any]) -> List[str]:
    aliases: List[str] = []
    source_id = str(source.get("source_id") or "").strip().lower()
    if source_id:
        aliases.append(source_id)

    doi = _normalize_doi(source.get("doi"))
    if doi:
        aliases.extend([doi.lower(), f"doi:{doi.lower()}"])

    authors = source.get("authors") or []
    year = str(source.get("year") or "n.d.").strip()
    if authors:
        first = _parse_author_name(authors[0])[0].lower()
        aliases.append(f"{first}|{year}")
        aliases.append(f"{first} et al.|{year}")
        if len(authors) >= 2:
            second = _parse_author_name(authors[1])[0].lower()
            aliases.append(f"{first} & {second}|{year}")
            aliases.append(f"{first} and {second}|{year}")

    return list(dict.fromkeys(alias for alias in aliases if alias))


def _replace_citation_placeholders(draft: str, metadata_by_id: Dict[str, Dict[str, Any]]) -> tuple[str, List[str]]:
    cited_source_ids: List[str] = []

    def replacement(match: re.Match[str]) -> str:
        raw_ids = match.group(1)
        ids = [part.strip() for part in re.split(r"[;,]", raw_ids) if part.strip()]
        citations = []

        for candidate in ids:
            normalized_candidate = _normalize_doi(candidate) or candidate
            source = metadata_by_id.get(candidate) or metadata_by_id.get(normalized_candidate)
            if not source:
                citations.append(f"({candidate})")
                continue

            source_id = source["source_id"]
            if source_id not in cited_source_ids:
                cited_source_ids.append(source_id)
            citations.append(_format_in_text_citation(source))

        return "; ".join(citations) if citations else match.group(0)

    updated = re.sub(r"\[CIT:\s*([^\]]+)\]", replacement, draft)
    return updated, cited_source_ids


def _replace_legacy_citation_placeholders(
    draft: str,
    alias_map: Dict[str, Dict[str, Any]],
    cited_source_ids: List[str],
) -> str:
    def register(source: Dict[str, Any]) -> str:
        source_id = source["source_id"]
        if source_id not in cited_source_ids:
            cited_source_ids.append(source_id)
        return _format_in_text_citation(source)

    def replace_doi(match: re.Match[str]) -> str:
        raw_doi = (match.group(1) or match.group(2) or "").strip()
        doi = _normalize_doi(raw_doi)
        if not doi:
            return match.group(0)
        source = alias_map.get(doi.lower()) or alias_map.get(f"doi:{doi.lower()}")
        return register(source) if source else match.group(0)

    def replace_author_year(match: re.Match[str]) -> str:
        author_text = match.group(1).strip().lower()
        year = match.group(2).strip()
        source = alias_map.get(f"{author_text}|{year}")
        return register(source) if source else match.group(0)

    draft = re.sub(r"\[DOI:\s*([^\]]+)\]|\[([^\[\]]*10\.\d{4,9}/[^\[\]]+)\]", replace_doi, draft)
    draft = re.sub(
        r"\[([^\[\],]+(?:\s*(?:&|and)\s*[^\[\],]+)?(?:\s+et al\.)?),\s*(\d{4}|n\.d\.)\]",
        replace_author_year,
        draft,
    )
    return draft

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
        intent = _coerce_mapping(ctx.session.state.get("query_intent"))
        if not intent:
            yield create_status_event(self.name, "Error: Query intent not found.")
            return

        research_topic = intent.get("research_topic", "Unknown Topic")
        expanded_queries = intent.get("expanded_queries", [research_topic])
        
        project_id = ctx.session.state.get("project_id", "default")
        user_id = ctx.user_id
        
        all_chunks = []
        seen_texts = set()
        source_metadata_by_id: Dict[str, Dict[str, Any]] = {}
        source_id_by_doi: Dict[str, str] = {}

        for query in expanded_queries:
            yield create_status_event(self.name, f"Retrieving literature for: '{query}'...")

            semantic_results = await semantic_scholar_search_tool(query=query, limit=8)
            for paper in semantic_results:
                source = _ensure_source_metadata({**paper, "matched_queries": [query]})
                source_id = source["source_id"]
                existing = source_metadata_by_id.get(source_id)
                source_metadata_by_id[source_id] = (
                    _merge_source_metadata(existing, source) if existing else source
                )

                if source.get("doi"):
                    source_id_by_doi[source["doi"]] = source_id

                abstract_text = (source.get("abstract") or "").strip()
                if abstract_text and abstract_text not in seen_texts:
                    all_chunks.append(
                        {
                            "text": abstract_text,
                            "doi": source.get("doi") or "Unknown",
                            "section": "Abstract",
                            "score": float(source.get("citations") or 0) / 1000.0,
                            "source_id": source_id,
                            "title": source.get("title"),
                            "authors": source.get("authors"),
                            "year": source.get("year"),
                            "venue": source.get("venue"),
                            "origin": "semantic_scholar",
                        }
                    )
                    seen_texts.add(abstract_text)

            chunks = await research_retrieval_tool(
                query=query,
                project_id=project_id,
                uid=user_id,
                top_k=10
            )
            for chunk in chunks:
                chunk_text = chunk.get("text", "")
                if chunk_text in seen_texts:
                    continue

                normalized_doi = _normalize_doi(chunk.get("doi"))
                source_id = source_id_by_doi.get(normalized_doi) if normalized_doi else None

                if not source_id:
                    source_id = normalized_doi or _fallback_source_id(chunk.get("title"), chunk_text)
                    if source_id not in source_metadata_by_id:
                        source_metadata_by_id[source_id] = _ensure_source_metadata(
                            {
                                "source_id": source_id,
                                "title": chunk.get("title") or "Corpus source",
                                "authors": chunk.get("authors") or [],
                                "year": chunk.get("year"),
                                "venue": chunk.get("venue"),
                                "doi": normalized_doi,
                                "matched_queries": [query],
                            }
                        )
                else:
                    source_metadata_by_id[source_id] = _merge_source_metadata(
                        source_metadata_by_id[source_id],
                        {"matched_queries": [query]},
                    )

                enriched_chunk = {
                    **chunk,
                    "doi": normalized_doi or chunk.get("doi", "Unknown"),
                    "source_id": source_id,
                    "origin": "session_memory",
                }
                source = source_metadata_by_id.get(source_id, {})
                for field in ("title", "authors", "year", "venue"):
                    if source.get(field) and not enriched_chunk.get(field):
                        enriched_chunk[field] = source[field]

                all_chunks.append(enriched_chunk)
                seen_texts.add(chunk_text)

        ctx.session.state["retrieved_chunks"] = all_chunks
        ctx.session.state["source_metadata"] = list(source_metadata_by_id.values())
        yield create_status_event(
            self.name,
            f"Aggregated {len(all_chunks)} literature segments across {len(source_metadata_by_id)} sources."
        )

# ── 1. Research Agent: Step 4 & 5 (Ranking & Assembly) ───────────────────────

class ContextAssemblyAgent(BaseAgent):
    """Ranks chunks based on similarity, diversity, and section importance."""
    name: str = "ContextAssembly"
    
    async def _run_live_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in self._run_async_impl(ctx):
            yield event

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        chunks = ctx.session.state.get("retrieved_chunks", [])
        source_metadata = ctx.session.state.get("source_metadata", [])
        if not chunks:
            ctx.session.state["formatted_context"] = "No relevant literature found."
            ctx.session.state["source_metadata"] = source_metadata
            ctx.session.state["source_catalog"] = _format_source_catalog(source_metadata)
            yield create_status_event(self.name, "No literature chunks to assemble.")
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

        source_metadata_map = {
            source["source_id"]: _ensure_source_metadata(source)
            for source in source_metadata
            if source.get("source_id")
        }

        # Group by paper/source for structured context
        papers: Dict[str, List[Dict[str, Any]]] = {}
        for c in top_chunks:
            source_id = c.get("source_id") or _normalize_doi(c.get("doi")) or _fallback_source_id(c.get("title"), c.get("text"))
            if source_id not in papers:
                papers[source_id] = []
            papers[source_id].append(c)

            if source_id not in source_metadata_map:
                source_metadata_map[source_id] = _ensure_source_metadata(
                    {
                        "source_id": source_id,
                        "title": c.get("title"),
                        "authors": c.get("authors") or [],
                        "year": c.get("year"),
                        "venue": c.get("venue"),
                        "doi": c.get("doi"),
                    }
                )

        context_text = "### RESEARCH CONTEXT (Grounded in literature)\n\n"
        ordered_source_metadata: List[Dict[str, Any]] = []
        for source_id, p_chunks in papers.items():
            source = source_metadata_map[source_id]
            ordered_source_metadata.append(source)
            context_text += f"SOURCE_ID: {source_id}\n"
            context_text += f"TITLE: {source.get('title')}\n"
            context_text += f"AUTHORS: {_format_authors_inline(source.get('authors') or [])}\n"
            context_text += f"YEAR: {source.get('year') or 'Unknown'}\n"
            context_text += f"VENUE: {source.get('venue') or 'Unknown'}\n"
            context_text += f"DOI: {source.get('doi') or 'Unknown'}\n"
            context_text += f"USE_CITATION_TAG: [CIT: {source_id}]\n"
            for c in p_chunks:
                sec = c.get('section', 'General')
                context_text += f"SECTION: {sec}\nCONTENT: {c.get('text')}\n"
            context_text += "\n"

        ctx.session.state["formatted_context"] = context_text
        ctx.session.state["source_metadata"] = ordered_source_metadata
        ctx.session.state["source_catalog"] = _format_source_catalog(ordered_source_metadata)

        yield create_status_event(self.name, f"Assembled context from {len(ordered_source_metadata)} primary sources.")

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

        SOURCE CATALOG:
        {source_catalog}
        
        ACADEMIC STANDARDS:
        1. THEMATIC SYNTHESIS: Do not just list what each paper says. Group findings by theme (e.g. 'Detection Techniques', 'Impact Analysis').
        2. COMPARATIVE ANALYSIS: Compare methodologies across different papers. Identify which methods are more efficient or common.
        3. CRITICAL EVALUATION: Identify research gaps or limitations mentioned in the literature.
        4. GROUNDING: Every technical claim MUST cite one or more SOURCE_ID values from the CONTEXT.
        5. CITATION STYLE: Use citation placeholders in the exact format [CIT: SOURCE_ID]. For multiple sources, use [CIT: SOURCE_ID_1; SOURCE_ID_2].
        6. VALIDITY: Only cite SOURCE_ID values that appear in the SOURCE CATALOG. Do not invent sources.
        7. OUTPUT: Do not add a References section. The citation pipeline will generate it.
        8. TONE: Formal academic Markdown.
        
        If the context is insufficient to write a high-quality section, state: "ERROR: Insufficient literature context."
        """,
        output_key="draft_content"
    )

# ── 3. Citation Agent ────────────────────────────────────────────────────────

class CitationAgent(BaseAgent):
    """Replaces [CIT: SOURCE_ID] placeholders with APA 7 citations and builds references."""
    name: str = "CitationAgent"
    model: Optional[Gemini] = None

    def __init__(self, model: Optional[Gemini] = None):
        super().__init__(name="CitationAgent")
        self.model = model

    async def _run_live_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        async for event in self._run_async_impl(ctx):
            yield event

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        draft = ctx.session.state.get("draft_content", "") or ""
        source_metadata = ctx.session.state.get("source_metadata", []) or []

        if not draft.strip():
            ctx.session.state["final_draft"] = draft
            yield create_status_event(self.name, "No draft content found for citation formatting.")
            return

        metadata_by_id: Dict[str, Dict[str, Any]] = {}
        alias_map: Dict[str, Dict[str, Any]] = {}
        for source in source_metadata:
            normalized = _ensure_source_metadata(source)
            metadata_by_id[normalized["source_id"]] = normalized
            if normalized.get("doi"):
                metadata_by_id[normalized["doi"]] = normalized
            for alias in _build_source_aliases(normalized):
                alias_map[alias] = normalized

        cleaned_draft = re.sub(r"\n## References\s*$.*", "", draft, flags=re.IGNORECASE | re.DOTALL).rstrip()
        cited_draft, cited_source_ids = _replace_citation_placeholders(cleaned_draft, metadata_by_id)
        cited_draft = _replace_legacy_citation_placeholders(cited_draft, alias_map, cited_source_ids)

        reference_entries = []
        for source_id in cited_source_ids:
            source = metadata_by_id.get(source_id)
            if source:
                reference_entries.append((source, _format_reference_entry(source)))

        reference_entries.sort(
            key=lambda item: (
                _parse_author_name((item[0].get("authors") or ["Unknown"])[0])[0].lower(),
                str(item[0].get("year") or "n.d."),
                (item[0].get("title") or "").lower(),
            )
        )

        if reference_entries:
            references = "\n".join(entry for _, entry in reference_entries)
            final_draft = f"{cited_draft}\n\n## References\n\n{references}"
        else:
            final_draft = cited_draft

        ctx.session.state["final_draft"] = final_draft
        yield create_status_event(
            self.name,
            f"Formatted {len(cited_source_ids)} source citations into APA 7 references."
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
        intent = _coerce_mapping(ctx.session.state.get("query_intent"))
        project_id = ctx.session.state.get("project_id", "default")
        user_id = ctx.user_id
        
        if not final_text:
            yield create_status_event(self.name, "No final text to save.")
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
        
        yield create_status_event(self.name, "Thesis finalization process complete.")
