# RAST Research Agent — ADK Orchestration Spec

**Date:** 2026-05-26
**Status:** Approved (user brief was comprehensive)
**Context:** Greenfield architecture design for an autonomous academic research assistant using Google ADK v2.1.0

---

## 1. System Overview

RAST is an autonomous academic research assistant agent. It takes a research topic, plans a structured approach, searches multiple academic sources, reads and evaluates papers, loops until comprehensive, synthesizes findings, and produces structured academic outputs with proper citations.

### Core Requirements

| # | Capability | Description |
|---|-----------|-------------|
| 1 | **Research Planning** | Decompose a research question into search strategies, key concepts, evaluation criteria |
| 2 | **Paper Search** | Query arXiv, Semantic Scholar, and web sources for relevant papers |
| 3 | **Paper Reading & Evaluation** | Read paper content (abstract, full text), evaluate relevance, extract structured findings |
| 4 | **Research Loop** | Iteratively search, read, and evaluate until research depth is sufficient |
| 5 | **Synthesis & Writing** | Synthesize findings into academic outputs (abstracts to full chapters) |
| 6 | **Citation Management** | Track, format, and insert citations (BibTeX, APA, IEEE) |
| 7 | **Skills Integration** | Map existing Hermes skills to ADK agent components |

### Non-Negotiable Constraints

- **Must use Google ADK v2.1.0** as the orchestration framework
- **Must use LiteLLM** as the model backend (via ADK's native `LiteLlm` support)
- Agents must be stateless in design; state stored in ADK Session state dict
- Must support output lengths from short reports (~500 words) to thesis chapters (~8000+ words)

---

## 2. ADK Framework Mapping

### Available Agent Types (ADK v2.1.0)

| Agent Type | ADK Class | Purpose | Used For |
|-----------|-----------|---------|----------|
| **LlmAgent** | `LlmAgent` | Single LLM-powered agent with tools | Planning, Search, Evaluation, Writing, Citation agents |
| **SequentialAgent** | `SequentialAgent` | Runs sub-agents in sequence, passes output forward | Synthesis pipeline (outline → draft → format) |
| **ParallelAgent** | `ParallelAgent` | Runs sub-agents concurrently, collects all outputs | Multi-source paper search, parallel paper reading |
| **LoopAgent** | `LoopAgent` | Repeats sub-agents until condition met or max iterations | Research depth loop |
| **BranchAgent** | Not available in v2.1.0 | — | Use `before_agent_callback` or code-level branching instead |

### LiteLLM Model Integration

ADK v2.1.0 has **native LiteLLM support** via `LiteLlm`. Models with prefixes matching `openai/*`, `anthropic/*`, `deepseek/*`, `ollama/*`, `azure/*`, `groq/*`, `bedrock/*`, `mistral/*`, `cohere/*`, `together_ai/*`, etc. are automatically routed through LiteLLM.

**Integration:**
```python
from google.adk.agents import LlmAgent

# Simply set model to a LiteLLM-recognized prefix:
planner_agent = LlmAgent(
    name="ResearchPlanner",
    model="openai/gpt-4o",           # Routed via LiteLLM
    instruction="Plan research...",
    tools=[...]
)
```

**OpenRouter Support via LiteLLM:**
```python
# Set environment variables:
# OPENROUTER_API_KEY=sk-or-...
# The model string would be:
model = "openrouter/openai/gpt-4o"  # or the specific OpenRouter model ID
```

### State Management

ADK Session state is a `dict[str, Any]` available via `Context.state`. Research state schema:

```python
research_state = {
    "topic": str,
    "research_plan": dict,           # structured plan from planning step
    "papers": [],                    # list of Paper objects
    "findings": [],                  # extracted findings
    "citations": {},                  # citation_key -> CitationEntry
    "current_depth": 0,              # iteration counter
    "max_depth": 5,                  # max iterations
    "completeness_score": 0.0,       # how comprehensive (0.0-1.0)
    "output_format": str,            # "report" | "chapter" | "paper" | "thesis"
    "synthesis": str,                # final written output
    "error_log": [],                  # errors encountered
}
```

---

## 3. Architecture Design

### High-Level Flow

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  RAST Master Agent (LlmAgent)                                    │
│  • Receives user request                                         │
│  • Delegates to sub-agents via transfer                           │
│  • Manages overall state                                         │
└─────────────────────────────────────────────────────────────────┘
    │
    ├── [1] ResearchPlanner (LlmAgent)
    │       • Decomposes topic → search queries, concepts, depth
    │       • Output: structured research plan stored in session state
    │
    ├── [2] SearchOrchestrator (ParallelAgent)
    │       ├── ArxivSearchAgent (LlmAgent + arXiv API tool)
    │       ├── SemanticScholarAgent (LlmAgent + Semantic Scholar tool)
    │       └── WebSearchAgent (LlmAgent + web search tool)
    │       • Returns merged, deduplicated paper list
    │
    ├── [3] PaperEvaluationLoop (LoopAgent)
    │       └── Each iteration:
    │           ├── PaperReaderPool (ParallelAgent)
    │           │   └── PaperReaderAgent instances (one per paper)
    │           ├── FindingsMerger (LlmAgent) - consolidates findings
    │           └── DepthChecker (callback) - evaluates completeness
    │       • Runs up to max_depth iterations
    │       • Exit: completeness >= threshold OR max iterations
    │
    └── [4] SynthesisPipeline (SequentialAgent)
            ├── OutlineAgent (LlmAgent) - creates document structure
            ├── DraftAgent (LlmAgent) - writes each section
            ├── CitationIntegrator (LlmAgent) - inserts citations
            └── QualityReviewAgent (LlmAgent) - final review pass
```

### Detailed Component Specifications

#### 3.1 Master Agent (RASTController)

```python
from google.adk.agents import LlmAgent

master_agent = LlmAgent(
    name="RASTController",
    model="openrouter/anthropic/claude-sonnet-4",  # Strong reasoning
    instruction="""You are the RAST research agent controller.
Your job is to understand the user's research request and delegate
to specialized sub-agents.

Flow:
1. First, transfer to ResearchPlanner to create a research plan
2. Then to SearchOrchestrator to find papers
3. Then to PaperEvaluationLoop to read and evaluate
4. Finally to SynthesisPipeline to write the output

Monitor state via context.state and report progress to the user.
""",
    sub_agents=[research_planner, search_orchestrator,
                paper_evaluation_loop, synthesis_pipeline],
    tools=[progress_reporter_tool]
)
```

**Key Design Decision:** The Master Agent uses an `LlmAgent` rather than `SequentialAgent` because:
- It needs to reason about which sub-agent to call next
- It can handle errors gracefully (retry, skip, fallback)
- It can interact with the user mid-flow if needed
- The LLM decision-making adds flexibility for edge cases

#### 3.2 ResearchPlanner (LlmAgent)

```python
research_planner = LlmAgent(
    name="ResearchPlanner",
    model="openrouter/anthropic/claude-sonnet-4",
    instruction="""You plan academic research. Given a topic:
1. Identify 5-10 key search queries
2. Break the topic into 3-5 sub-topics
3. Define evaluation criteria for paper relevance
4. Set depth targets (how many papers per sub-topic)
5. Determine output structure (sections)

Store the plan in state['research_plan'].
Use the update_plan_tool to write to state.""",
    tools=[update_plan_tool, search_term_generator_tool],
    output_key="research_plan"  # Auto-stores to state['research_plan']
)
```

**Why separate planning agent?** Research planning is a distinct cognitive task. A dedicated agent with focused instructions produces more structured plans than having planning as a tool call. The `output_key` mechanism auto-stores the result in session state.

#### 3.3 SearchOrchestrator (ParallelAgent)

```python
search_orchestrator = ParallelAgent(
    name="SearchOrchestrator",
    description="Searches multiple academic sources in parallel",
    sub_agents=[arxiv_agent, semantic_scholar_agent, web_search_agent]
)

arxiv_agent = LlmAgent(
    name="ArxivSearchAgent",
    model="openrouter/openai/gpt-4o-mini",  # Fast, cheap for search
    instruction="Search arXiv for papers matching the queries in state['research_plan'].",
    tools=[arxiv_search_tool],
    output_key="arxiv_results"
)

semantic_scholar_agent = LlmAgent(
    name="SemanticScholarAgent",
    model="openrouter/openai/gpt-4o-mini",
    instruction="Search Semantic Scholar for papers matching the research plan queries.",
    tools=[semantic_scholar_search_tool],
    output_key="semantic_scholar_results"
)

web_search_agent = LlmAgent(
    name="WebSearchAgent",
    model="openrouter/openai/gpt-4o-mini",
    instruction="Search the web for additional papers, preprints, and grey literature.",
    tools=[web_search_tool],
    output_key="web_results"
)
```

**Why ParallelAgent?** Three independent search sources — no dependency between them. Parallel execution reduces wall-clock time. Each agent is lightweight (cheap model, focused task) and writes to its own `output_key`.

**Why separate agents vs. tools on a single agent?**
- Each search source has different API semantics and rate limits
- Isolation prevents one failing search from affecting others
- ParallelAgent handles concurrent execution natively
- Easier to add/remove sources independently

#### 3.4 PaperEvaluationLoop (LoopAgent)

```python
paper_evaluation_loop = LoopAgent(
    name="PaperEvaluationLoop",
    description="Iteratively reads papers and evaluates research depth",
    sub_agents=[paper_reader_pool, findings_merger],
    max_iterations=5  # configurable depth cap
)
```

**Why LoopAgent?** The research process is inherently iterative — search results lead to more reading, which reveals gaps that need more searching. The `max_iterations` cap prevents infinite loops.

**Exit condition:** Evaluated via a `before_agent_callback` or `after_agent_callback` that checks:
```python
async def check_research_depth(ctx: Context):
    state = ctx.state
    completeness = state.get("completeness_score", 0.0)
    if completeness >= 0.85:
        return Content(role="model", parts=[TextPart("RESEARCH_COMPLETE")])
    return None  # continue looping
```

**PaperReaderPool:**

```python
# Dynamically created per iteration — reads papers in parallel
paper_reader_pool = ParallelAgent(
    name="PaperReaderPool",
    description="Reads multiple papers in parallel",
    # sub_agents created dynamically per iteration
)
```

**Dynamic sub-agent creation pattern (key architecture decision):**
```python
def create_paper_readers(papers: list) -> list[LlmAgent]:
    readers = []
    for paper in papers:
        reader = LlmAgent(
            name=f"PaperReader_{paper['id']}",
            model="openrouter/anthropic/claude-sonnet-4",
            instruction=f"Read and evaluate paper: {paper['title']}\n{paper['abstract']}",
            tools=[read_paper_tool(paper), extract_findings_tool],
            output_key=f"paper_findings_{paper['id']}"
        )
        readers.append(reader)
    return readers
```

**Dynamic sub-agents:** This is a critical pattern. Instead of pre-registering N paper reader agents (wasteful and fragile), we create them dynamically per iteration based on the number of papers returned. ADK supports this via `sub_agents` assignment at runtime.

**FindingsMerger:**

```python
findings_merger = LlmAgent(
    name="FindingsMerger",
    model="openrouter/anthropic/claude-sonnet-4",
    instruction="""Consolidate findings from all paper readers.
1. Merge overlapping findings
2. Identify key themes
3. Calculate completeness score (0.0-1.0)
4. Update state['findings'], state['completeness_score']
5. Identify remaining gaps for next iteration""",
    tools=[update_state_tool, identify_gaps_tool]
)
```

#### 3.5 SynthesisPipeline (SequentialAgent)

```python
synthesis_pipeline = SequentialAgent(
    name="SynthesisPipeline",
    description="Writes the final research output",
    sub_agents=[outline_agent, draft_agent,
                citation_integrator, quality_review_agent]
)
```

**Why SequentialAgent?** Writing is inherently sequential — you need an outline before a draft, citations before formatting, review after writing. Each stage depends on the previous.

**OutlineAgent:**
```python
outline_agent = LlmAgent(
    name="OutlineAgent",
    model="openrouter/anthropic/claude-sonnet-4",
    instruction="""Create a detailed academic outline from the research findings.
Match the outline structure to the requested output format
(report, chapter, paper, thesis).
Include section headers and key points per section.
Store in state['outline'].""",
    tools=[update_state_tool],
    output_key="outline"
)
```

**DraftAgent (handles variable-length output):**
```python
draft_agent = LlmAgent(
    name="DraftAgent",
    model="openrouter/anthropic/claude-sonnet-4",
    instruction="""Write the research output following the outline.
Output length depends on state['output_format']:
- report: 500-2000 words
- chapter: 3000-5000 words
- paper: 5000-8000 words
- thesis: 8000+ words (sections written sequentially)

For long outputs, write one section at a time and
accumulate via the append_to_draft tool.""",
    tools=[append_to_draft_tool, format_section_tool]
)
```

**Long-output strategy:** For thesis-length outputs, the DraftAgent uses an `append_to_draft_tool` that progressively builds the document in session state, section by section. This avoids exceeding token limits in a single LLM call.

**CitationIntegrator:**
```python
citation_integrator = LlmAgent(
    name="CitationIntegrator",
    model="openrouter/openai/gpt-4o-mini",  # Cheap formatting
    instruction="""Insert citations from state['citations'] into the draft.
Convert all citations to the requested format.
Verify every citation has a corresponding entry in the bibliography.""",
    tools=[format_citation_tool, generate_bibliography_tool],
    output_key="formatted_draft"
)
```

**QualityReviewAgent:**
```python
quality_review_agent = LlmAgent(
    name="QualityReviewAgent",
    model="openrouter/anthropic/claude-sonnet-4",
    instruction="""Review the research output for:
1. Academic quality and rigor
2. Citation accuracy and completeness
3. Structural coherence
4. Grammar and style
5. Factual consistency with source papers

Apply corrections and store final output in state['synthesis'].""",
    tools=[edit_draft_tool, verify_citations_tool],
    output_key="synthesis"
)
```

---

## 4. Tool Inventory

### Core Tools

| Tool Name | Purpose | Used By |
|-----------|---------|---------|
| `arxiv_search` | Query arXiv API by search terms, categories, author | ArxivSearchAgent |
| `semantic_scholar_search` | Query Semantic Scholar API | SemanticScholarAgent |
| `web_search` | General web search for papers/grey literature | WebSearchAgent |
| `read_paper` | Fetch and read paper full text (PDF parsing, HTML) | PaperReader agents |
| `extract_findings` | Extract structured findings from paper content | PaperReader agents |
| `update_plan` | Write/update the research plan in session state | ResearchPlanner |
| `search_term_generator` | Generate optimal search terms from a topic | ResearchPlanner |
| `update_state` | Generic state update tool | All merging/writing agents |
| `identify_gaps` | Identify remaining research gaps from findings | FindingsMerger |
| `append_to_draft` | Accumulate draft content section by section | DraftAgent |
| `format_section` | Format a section per academic style guide | DraftAgent |
| `format_citation` | Format a single citation (BibTeX, APA, IEEE) | CitationIntegrator |
| `generate_bibliography` | Generate full bibliography from citation list | CitationIntegrator |
| `edit_draft` | Apply corrections to the working draft | QualityReviewAgent |
| `verify_citations` | Verify all citations have bibliography entries | QualityReviewAgent |
| `progress_reporter` | Report progress to user | RASTController |

### Tool Implementation Strategy

Tools should be implemented as Python callables decorated with `@tool` or as `FunctionTool` instances:

```python
from google.adk.tools import FunctionTool

def arxiv_search(query: str, max_results: int = 10) -> list[dict]:
    \"\"\"Search arXiv API for papers matching query.\"\"\"
    import urllib.request
    import xml.etree.ElementTree as ET
    import urllib.parse

    url = f"http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(query)}&max_results={max_results}"
    response = urllib.request.urlopen(url)
    # Parse Atom XML response
    # Return list of paper dicts with id, title, authors, abstract, published, pdf_link
    ...

arxiv_search_tool = FunctionTool(
    func=arxiv_search,
    name="arxiv_search",
    description="Search arXiv for academic papers matching the query"
)
```

---

## 5. Skills-to-Agent Mapping

| Hermes Skill | ADK Component | Role |
|-------------|---------------|------|
| `arxiv` | ArxivSearchAgent (tool) | Search arXiv API for papers |
| `paper-lookup` | SemanticScholarAgent (tool) | Search Semantic Scholar |
| `literature-review` | PaperEvaluationLoop + FindingsMerger | Structured review process |
| `research-lookup` | WebSearchAgent (tool) | Grey literature and web sources |
| `k-dense-collection` | Domain skill execution layer | After Stage 4 for data gathering |
| `brainstorming` | ResearchPlanner | Planning methodology |
| `consciousness-council` | Not in agent — evaluation methodology | Could be used for peer review |
| `multi-brain-debate` | Not in agent — evaluation methodology | Alternative synthesis approach |
| `deep-thinker-ai` | QualityReviewAgent | Final quality review |

---

## 6. LiteLLM Configuration

```python
# config/litellm_config.py
import os

# LiteLLM uses environment variables for API keys
# ADK LiteLlm auto-detects these

class ModelConfig:
    REASONING_MODEL = "openrouter/anthropic/claude-sonnet-4"  # Planning, evaluation, writing
    FAST_MODEL = "openrouter/openai/gpt-4o-mini"              # Search, formatting, review
    CHEAP_MODEL = "openrouter/meta-llama/llama-3.1-70b"       # Bulk processing fallback

# Required environment variables:
# OPENROUTER_API_KEY=<your-key>
# Or for direct providers:
# OPENAI_API_KEY=<key>
# ANTHROPIC_API_KEY=<key>
```

**Model Selection Strategy:**

| Agent | Model | Rationale |
|-------|-------|-----------|
| RASTController | Claude Sonnet 4 | Strong reasoning, good at orchestration decisions |
| ResearchPlanner | Claude Sonnet 4 | Planning requires deep understanding |
| ArxivSearchAgent | GPT-4o-mini | Cheap, sufficient for API calls + summary |
| SemanticScholarAgent | GPT-4o-mini | Same — simple query + parse response |
| WebSearchAgent | GPT-4o-mini | Same |
| PaperReader agents | Claude Sonnet 4 | Reading comprehension is critical |
| FindingsMerger | Claude Sonnet 4 | Synthesis requires reasoning |
| OutlineAgent | Claude Sonnet 4 | Structure requires understanding |
| DraftAgent | Claude Sonnet 4 | Quality writing needs strong model |
| CitationIntegrator | GPT-4o-mini | Formatting is mechanical |
| QualityReviewAgent | Claude Sonnet 4 | Review requires critical thinking |

---

## 7. Testing Strategy

### Unit Tests

| Test | What it validates |
|------|-------------------|
| `test_arxiv_search_tool` | Tool returns correct paper format |
| `test_semantic_scholar_search_tool` | Tool returns correct paper format |
| `test_state_schema` | State schema validates correctly |
| `test_citation_formats` | BibTeX, APA, IEEE format correctly |
| `test_plan_validation` | Research plan schema validation |

### Integration Tests

| Test | What it validates |
|------|-------------------|
| `test_research_flow` | Full flow: plan → search → evaluate for a simple topic |
| `test_parallel_search` | ParallelAgent correctly runs all three searchers |
| `test_loop_exit_condition` | LoopAgent stops at max_iterations |
| `test_sequential_synthesis` | Output passes through all synthesis stages |
| `test_dynamic_paper_readers` | Dynamic sub_agents are created and run |

### End-to-End Tests

| Test | What it validates |
|------|-------------------|
| `test_short_report` | "Write a 500-word report on transformer architectures" |
| `test_long_chapter` | "Write a chapter on reinforcement learning for robotics" |
| `test_complex_topic` | Multi-subject topic that requires deep research |
| `test_edge_bad_topic` | Vague or impossible topic — graceful handling |
| `test_citation_accuracy` | All citations in output match bibliography |

---

## 8. Implementation Order

### Phase 1: Foundation (Week 1)
1. Set up project structure, venv, dependencies
2. Implement state schema and validation
3. Implement core tools (arxiv_search, semantic_scholar_search, read_paper)
4. Create and test ResearchPlanner agent
5. Create and test SearchOrchestrator with ParallelAgent

### Phase 2: Core Loop (Week 2)
6. Implement PaperReader agent with dynamic sub-agent creation
7. Implement FindingsMerger and completeness scoring
8. Implement PaperEvaluationLoop with LoopAgent
9. Add gap identification and re-search
10. Test end-to-end research loop

### Phase 3: Writing (Week 3)
11. Implement OutlineAgent and DraftAgent
12. Implement long-output strategy (append_to_draft tool)
13. Implement citation management (all three formats)
14. Implement QualityReviewAgent
15. Test synthesis pipeline end-to-end

### Phase 4: Polish (Week 4)
16. Add progress reporting and user interaction
17. Error handling and retry logic
18. Rate limiting for search APIs
19. Token tracking and cost estimation
20. Documentation and usage examples

---

## 9. Open Questions

1. **Dynamic sub-agent lifecycle:** How does ADK handle adding sub_agents at runtime? Are they persisted across loop iterations, or re-created each time?

2. **Token limits for paper reading:** What's the max context window for paper readers? Strategy for papers exceeding context (chunking, selective reading)?

3. **ParallelAgent with dynamic sub_agents:** Can ParallelAgent accept a list that changes each iteration, or does it need a fixed set?

4. **Callback-based exit from LoopAgent:** Is `before_agent_callback` the right mechanism, or should we use a custom condition function?

5. **Session state persistence:** In-memory vs. persistent (Firestore/Redis) for production use?

---

## 10. Key Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Controller agent type | LlmAgent (not SequentialAgent) | Needs reasoning for dynamic delegation, error handling |
| Search pattern | ParallelAgent of three dedicated agents | Isolation, independent rate limits, easy to extend |
| Paper reading | Dynamic sub-agents created per iteration | Scales to N papers without pre-registration waste |
| Research loop | LoopAgent with max_iterations cap | Natural fit for iterative deepening |
| Writing pipeline | SequentialAgent (4 stages) | Linear dependency chain, clean separation of concerns |
| State storage | ADK Session state dict | Available to all agents, no external DB needed |
| Model backend | LiteLLM via ADK native support | No custom integration code needed |
| Citation management | Dedicated LlmAgent + formatting tools | Separates concerns from writing |
| Long output strategy | Append-to-draft tool, section-by-section | Avoids context overflow |
