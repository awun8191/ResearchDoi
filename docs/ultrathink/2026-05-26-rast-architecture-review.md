# RAST Architecture Review — UltraThink Pipeline

**Date:** 2026-05-26
**Reviewer:** Architecture Reviewer (UltraThink Cognitive Pipeline)
**Target:** Research Assistant (RAST) — agent + API architecture

---

## TL;DR

RAST has a solid foundation but suffers from **dual-codebase friction**: AGENT and API have separate configs, duplicate services, and communicate over HTTP when they should share memory. The Google ADK dependency is the biggest risk — it was designed for Gemini-native workflows and the LiteLlm bridge to OpenRouter is fragile, especially with free-tier models. **Recommendation:** Unify into a single repo with shared core, replace ADK with a lightweight orchestration layer using native OpenRouter calls, and prioritize Appwrite migration + ChromaDB over Firestore. Free models work but need careful token budgeting and caching.

---

## Stage 1: Brainstorming — Codebase Exploration

### Current Architecture Map

```
ResearchDoi (monorepo at ~/.hermes/projects/ResearchDoi/)
├── API/                          # FastAPI backend
│   ├── main.py                   # Entry point, Firebase init, 8 routers
│   ├── src/core/
│   │   ├── config.py             # Settings: chat_model, embedding_model, OpenRouter keys
│   │   └── dependencies.py       # Auth (X-Api-Key + dev mock user)
│   ├── src/service/
│   │   ├── gemini.py             # OpenRouter chat + RAG tool calling + Firestore history
│   │   ├── rag.py                # ChromaDB-backed vector store (migrated from numpy)
│   │   ├── pdf_resolver.py       # 5-tier cascading PDF resolver
│   │   ├── doi_lookup.py         # CrossRef metadata service
│   │   ├── arxiv_lookup.py       # ArXiv search/metadata
│   │   ├── ingestion.py          # Section-aware PDF chunking & embedding
│   │   ├── projects.py           # Project CRUD (Firestore)
│   │   ├── web_loader.py         # Web page text extraction
│   │   ├── storage.py            # Firebase Storage operations
│   │   └── paper_chat.py         # Paper-specific chat
│   ├── src/routers/
│   │   ├── doi.py                # GET /api/doi/{doi}, /api/doi/search
│   │   ├── pdf.py                # GET /api/pdf/resolve
│   │   ├── chat.py               # POST /api/chat/message, /api/chat/agent/message
│   │   ├── rag.py                # POST /api/rag/ingest, /api/rag/search
│   │   ├── projects.py           # CRUD /api/projects
│   │   ├── storage.py            # Upload/download /api/storage
│   │   ├── history.py            # GET /api/history
│   │   └── paper_chat.py         # Paper-specific endpoints
│   └── tests/
│
├── AGENT/                        # Google ADK-based autonomous research agent
│   ├── src/agent.py              # Root agent: orchestrator + 4 sub-agents
│   ├── src/config.py             # LiteLlm with OpenRouter models (minimax/m2.5:free)
│   ├── src/research/
│   │   ├── agents.py             # PaperDiscovery, ThesisPlanner, ThesisDirector
│   │   ├── pipeline.py           # Full research pipeline: query expansion → retrieval → writing → citation → review
│   │   └── tools.py              # Exa API, ArXiv, DOI, PDF, RAG, storage tools
│   ├── src/lookup/
│   │   └── agents.py             # InitState, Evaluator, SearchWorker, recursive research loop
│   └── src/service/
│       ├── doi_lookup.py         # WRAPPER: calls API's /api/doi/{doi} endpoint
│       └── pdf_resolver.py       # WRAPPER: calls API's /api/pdf/resolve endpoint
│
└── ResearchDoi/                  # Vite + React 19 frontend
    └── src/
        ├── services/api.js
        ├── services/rag.js
        ├── services/agent.js
        └── services/gemini.js
```

### Key Data Flow

```
User → Frontend → API/chat/message → OpenRouter (Gemma 4 31B) → RAG tool call → ChromaDB → Response
User → Frontend → API/chat/agent/message → AGENT (via HTTP proxy) → ADK Orchestrator → Sub-agent → Exa/ArXiv → RAG → Response
```

### Critical Findings

| Area | Current State | Risk Level |
|------|--------------|------------|
| **Dual Codebase** | AGENT and API are separate dirs but AGENT is an HTTP client of API | High — tight coupling, duplicated service wrappers |
| **Model Config Split** | API uses `google/gemma-4-31b-it`; AGENT uses `minimax/minimax-m2.5:free` via LiteLlm | Medium — inconsistency, harder to tune |
| **Google ADK** | LiteLlm bridges to OpenRouter but ADK was designed for Gemini SDK | High — fragile, undocumented edge cases, no streaming guarantees with free models |
| **Firestore** | Chat history, projects, user data all in Firestore (migrating to Appwrite) | Medium — blocks deployment until migration complete |
| **ChromaDB** | Working well, persistent, per-collection scoping | Low — works, but consider Cloudflare Vectorize for prod |
| **Auth** | X-Api-Key header + dev mock user | Medium — functional but no real user isolation |
| **PDF Pipeline** | 5-tier cascade with probe, heuristic, scraper | Low — robust, well-tested |
| **Free Models** | Llama 3 120B (primary), Gemma 4 30B (secondary) on OpenRouter free tier | Medium — rate limits, context window constraints, no SLA |
| **AGENT Service Wrappers** | Agent/src/service/ has standalone wrappers that duplicate API service logic | Medium — maintanence burden, out of sync risk |
| **RAG Tooling** | AGENT's `research_retrieval_tool` calls API's `/api/rag/search` over HTTP | Medium — unnecessary network hop in same process |

---

## Stage 2: Consciousness Council

### Council Members Selected

**Problem:** How should RAST be architected given free models, OpenRouter, Appwrite migration, and the current dual-codebase reality?

---

**🎭 The Architect**
**Position:** Unify into a single codebase with shared core services.
**Reasoning:** Two codebases with HTTP-stitched communication creates an N+1 architecture problem. AGENT should import API's services directly, not wrap them with HTTP calls. The monorepo already exists — use proper package structure with a `shared/` core module. ADK should be replaced with a lightweight orchestration layer since it adds unnecessary abstraction for what is fundamentally sequential agent workflows.
**Key Risk They See:** Tight coupling today prevents independent scaling of the agent pipeline vs API endpoints.
**Surprising Insight:** The ADK's LiteLlm integration is not officially supported — when OpenRouter changes their API or free tier models change, the ADK bridge will break silently. You're already on minimax/m2.5 which is a third-party model through a third-party proxy.

---

**🎭 The Minimalist**
**Position:** Strip ADK entirely. Use direct OpenRouter calls + asyncio.
**Reasoning:** The ADK adds ~40 dependencies and a complex event system for what is essentially: search → fetch → write → save. Each of these is a direct function call or HTTP request. The AGENT's `SequentialAgent` and `LoopAgent` patterns can be replaced with 50 lines of asyncio code. Less code = fewer bugs = faster iteration with free models that change frequently.
**Key Risk They See:** LiteLlm + ADK is the biggest single point of failure. If Google deprecates the LiteLlm path, the entire agent stops working.
**Surprising Insight:** The AGENT's `tools.py` already has standalone async functions (exa_search, arxiv_search, etc.) — the ADK wrapping adds no value, it just makes debugging harder.

---

**🎭 The Pragmatist**
**Position:** Keep ADK but wrap it with a fallback. Focus on what blocks deployment.
**Reasoning:** Rewriting the orchestration layer is a distraction. GCP suspension blocks deployment, not the ADK. Priority order: (1) Complete Appwrite migration so you can deploy anywhere, (2) Add a simple fallback mode that calls OpenRouter directly when ADK fails, (3) Profile token usage to stay within free tier limits. The minimal viable improvement is completing the migration so you can deploy on a $5 VPS.
**Key Risk They See:** Obsessing over the "perfect" architecture while GCP suspension means zero users can access the system.
**Surprising Insight:** You could deploy the API-only (no ADK agent) today on any cheap VPS — the agent features are nice but not MVP-blocking. Ship the API, then iterate the agent.

---

**🎭 The Empiricist**
**Position:** Measure before refactoring. Profile model latency, cost, and failure modes.
**Reasoning:** You have no telemetry on: token consumption per research session, OpenRouter failure rates for free models, LiteLlm error frequency, Firestore read/write costs. All architecture decisions should be data-driven. Instrument the API and AGENT with structured logging + metrics, run a benchmark suite, then decide what to refactor.
**Key Risk They See:** Architectural decisions made without data will optimize for the wrong thing. You might spend weeks replacing ADK when the real bottleneck is model latency (free tier queueing).
**Surprising Insight:** The free tier models from OpenRouter have significant queue times during peak hours (5-30s for first token). A proper streaming UX would hide most of this latency, but the ADK doesn't support streaming back through the current proxy architecture.

---

**🎭 The Outsider**
**Position:** Why use a vector store at all for a research assistant with free models?
**Reasoning:** Free models have a context window of 8K-32K tokens. A single paper is typically 3K-6K tokens. You could include 3-5 full papers in context without needing RAG at all. The ChromaDB + embedding pipeline adds complexity and cost (even Qwen3 Embedding 8B costs on OpenRouter). For a research assistant reading papers, full-context prompting may outperform RAG for most queries.
**Key Risk They See:** Your RAG pipeline costs money (embeddings) and adds latency, but may not meaningfully improve answers over sending the full text as context.
**Surprising Insight:** Llama 3 120B has a 128K context window. You can fit an entire literature review's worth of source papers in a single prompt. The RAG system may be premature optimization.

---

### ⚖️ Council Synthesis

**Points of Convergence:**
1. The dual-codebase HTTP-coupling is technical debt, not a feature. AGENT calling API endpoints from the same process is wasteful.
2. Appwrite migration is the #1 blocker for deployment, regardless of architecture choices.
3. The free model tier is viable but needs instrumentation for token budgeting and failure handling.
4. ADK is the riskiest dependency, but replacing it is not the most urgent task.

**Core Tension:**
- **Architect + Minimalist:** Strip ADK, unify codebase, rebuild orchestration layer
- **Pragmatist + Empiricist:** Complete Appwrite migration first, add instrumentation, then refactor based on data
- **Outsider:** Question whether RAG is even needed given model context windows

**The Blind Spot:**
No one addressed **deployment cost**. The current stack (ChromaDB, Firestore/Appwrite, FastAPI, ADK) requires minimum ~4GB RAM. Free models need reliable internet. If deploying on a cheap VPS ($5-10/mo), the memory budget is tight. ChromaDB alone can consume 500MB-1GB for moderate collections. This constrains where the system can run.

**Recommended Path:**
1. **Immediate (1-2 weeks):** Complete Appwrite migration. This is the deployment gate.
2. **Short-term (2-4 weeks):** Add instrumentation (structured logging + token counters). Profile model behavior with free tier.
3. **Medium-term (1-2 months):** Unify AGENT services into API. Replace ADK with direct OpenRouter calls + lightweight asyncio orchestration. Add optional full-context mode as alternative to RAG.
4. **Low priority:** VPS deployment with Docker compose. ChromaDB + Appwrite + FastAPI + Nginx.

**Confidence Level:** Medium

**One Question to Sit With:**
"If ADK stopped working tomorrow, could your users still do research? What's the minimum path to 'yes'?"

---

## Stage 3: Multi-Brain Debate

### Round 1 — Opening Positions

**Instance A — Creative:**
Replace the entire two-codebase architecture with a unified "research core" that serves both API and agent roles. Use a single FastAPI app that exposes endpoints and also has an internal agent scheduler. The agent becomes a background task queue — user submits a research request, gets a task ID, polls for completion. This eliminates HTTP churn between components and allows proper caching. Use SQLite for job queue (zero-dependency), ChromaDB for vectors, Appwrite for blob storage. The frontend becomes a thin client that calls one API.

**Instance B — Pragmatic:**
Don't touch the architecture. Complete the Appwrite migration, add retry logic for OpenRouter free tier rate limits, and deploy on Railway or Render with Docker. The system works today for a single user. The ADK vs no-ADK debate is premature when there are zero users. Focus on: (1) Firestore → Appwrite migration, (2) Docker health checks + auto-restart for OpenRouter 503s, (3) Simple token usage dashboard. Ship first, optimize later.

**Instance C — Comprehensive:**
Neither extreme. Keep the current structure but systematically de-risk each component. Create a compatibility layer around ADK (so you can swap it without code changes). Move AGENT services to import API services directly instead of HTTP calls. Add a circuit breaker for OpenRouter calls. Instrument every service with latency + error metrics. Create a single `docker-compose.yml` that runs the whole stack. The migration is the priority, but do it in a way that if ADK breaks, you have a fallback path.

### Round 2 — Challenges

**A challenges B:**
"B's approach ignores that the dual-codebase issue will compound with every new feature. Every new endpoint needs an AGENT service wrapper. Every new AGENT tool needs an API endpoint. This scales as O(n²) maintenance."

**B challenges C:**
"C's compatibility layer is the worst of both worlds — you're maintaining an abstraction for a dependency you plan to replace. That's YAGNI. Either commit to ADK or replace it. A half-abstraction is more code to delete later."

**C challenges A:**
"A's background task queue sounds elegant but adds significant complexity: job persistence, status polling, cancellation, error reporting. For a single-user prototype, synchronous request-response is simpler and debuggable. Don't optimize for scale you don't have yet."

**Rebuttals:**
- **A responds:** "The HTTP coupling already exists and it's already a problem. I'm proposing replacing it with a simpler pattern, not a more complex one. An in-process function call is simpler than an HTTP round-trip."
- **B responds:** "Fair point on O(n²), but you're proposing a rewrite that doesn't ship anything. Ship the migration, measure, then refactor with data."
- **C responds:** "A half-abstraction IS better than a locked-in one because it creates the option to migrate. The cost of the abstraction layer is 2 days of work. The cost of a full ADK lock-in is weeks of rewrites when it breaks."

### ⚖️ VERDICT

**Winner:** **Instance C (Comprehensive)** with elements from A and B incorporated.

**Incorporated:**
- From A: Direct service imports between AGENT and API instead of HTTP wrappers (low-hanging fruit, eliminates unnecessary coupling immediately)
- From B: Priority sequencing — Appwrite migration FIRST, architecture changes SECOND
- From C: Systematic de-risking — fallback-compatible ADK layer, instrument before refactor

**Eliminated:**
- Full background task queue architecture (A) — too complex for current scale
- "Ship and ignore architecture" (B) — maintenance debt compounds too fast
- Full ADK removal without migration path (both A and B extremes)

---

## Stage 4: Deep Thinker Review

### 🔍 ULTRA FINAL REVIEW

**Consistency Check:**
- The Council recommended: complete Appwrite migration → instrument → unify services → evaluate ADK replacement
- The Debate verdict refined: import services directly (low-hanging fruit), add ADK compatibility layer, sequence migration before refactoring
- No contradictions between stages — the pipeline converged on a sequenced approach

**Actionability:**
High. Every recommendation maps to specific files and changes:

1. **Appwrite migration** — Replace Firestore calls in `API/src/service/gemini.py`, `API/src/routers/doi.py`, `API/src/routers/projects.py`, `API/src/routers/rag.py` with Appwrite SDK calls. The `firebase-legacy/` directory confirms this is in progress.
2. **Direct service imports** — In `AGENT/src/tools.py`, replace:
   - `research_retrieval_tool` → direct import of `API.src.service.rag.rag_service.search()`
   - `doi_lookup_tool` → direct import of `API.src.service.doi_lookup.DoiLookup.fetch_metadata()`
   - `pdf_resolver_tool` → direct import of `API.src.service.pdf_resolver.resolve_pdf()`
   This eliminates HTTP wrappers in `AGENT/src/service/doi_lookup.py` and `AGENT/src/service/pdf_resolver.py`.
3. **ADK fallback layer** — Create `AGENT/src/adk_adapter.py` that catches ADK errors and falls back to direct OpenRouter calls. This is a ~200-line safety net.
4. **Instrumentation** — Add `prometheus-fastapi-instrumentator` or structured logging with request IDs to API and AGENT. Track: model latency, token count, error rate, RAG query time.

**Key Weaknesses:**
- **No deployment cost analysis.** The recommended stack (FastAPI + ChromaDB + Appwrite + optional ADK) needs at least 2GB RAM. Appwrite itself is memory-heavy (Node.js runtime). Consider using Supabase or a lighter backend to keep deployment costs under $10/mo.
- **No model fallback strategy for OpenRouter free tier.** Free models have no SLA. If Gemma 4 30B is rate-limited, the entire chat feature fails. Add model fallback chains: primary → secondary → local model (e.g., Llama.cpp).
- **The full-context alternative to RAG (Outsider's point) wasn't fully addressed.** For power users, a "full context mode" that sends 3-5 papers directly to Llama 3 120B's 128K context window could bypass RAG entirely for many queries.
- **Google ADK's `session.db` files** were found in the stale repos (`/tmp/rast-agent/src/.adk/session.db`). These SQLite files persist between runs but are not cleaned up. The AGENT's `src/manager/__init__.py` and `src/manager/.adk/session.db` suggest ADK session management is active but untracked.

**Recommended Next Step:**
1. **Today:** Unify the two `doi_lookup.py` and `pdf_resolver.py` service files by having AGENT import from API directly (removes 120 lines of HTTP wrapper code, eliminates a failure point).
2. **This week:** Complete Appwrite migration for chat history (`src/service/gemini.py` — `_save_turn`, `_load_history`, `_chat_collection` functions). This is the deployment gate.
3. **Next week:** Add `AGENT/src/adk_adapter.py` — try ADK first, catch `LiteLlm`/`InvocationContext` errors, fall back to raw `httpx` → OpenRouter.
4. **Within 2 weeks:** Deploy API-only stack (without ADK agent) on a $7/mo VPS or Railway to validate the deployment pipeline works.
5. **Longer-term:** Profile model usage, decide on ADK replacement, consider full-context mode as RAG alternative.

**Questions for the user:**
- Are you leaning toward keeping ADK or replacing it? This affects the priority of the compatibility layer.
- What's your deployment budget? Appwrite vs lighter alternatives like Supabase or plain PostgreSQL?
- How many concurrent users do you expect? This determines whether the synchronous request-response model is sufficient.

---

## Consolidated Recommendations

### 1. Immediate Fixes (No Brainer, <1 Day)

| File | Change | Impact |
|------|--------|--------|
| `AGENT/src/tools.py` lines 155-167 | Import `DoiLookup` from API services instead of HTTP call | -50ms latency, removes HTTP failure mode |
| `AGENT/src/tools.py` lines 162-167 | Import `resolve_pdf` from API services instead of HTTP call | Same as above |
| `AGENT/src/tools.py` lines 185-213 | Import `rag_service` from API services for direct ChromaDB access | Eliminates network hop for RAG queries |

### 2. Short-Term (This Week — Appwrite Migration)

Complete these migration touchpoints:
- `src/service/gemini.py` — `_save_turn()`, `_load_history()`, `_chat_collection()` all use Firestore
- `src/routers/doi.py` line 69-80 — saves lookup history to Firestore
- `src/service/projects.py` — Project CRUD uses Firestore
- `src/routers/rag.py` line 150-167 — `ingest_project_sources` reads from Firestore directly

### 3. Medium-Term (1-2 Weeks — Deployment Ready)

- Create `AGENT/src/adk_adapter.py` for ADK fallback
- Add OpenRouter model fallback chain in `API/src/core/config.py`
- Docker compose with: API + ChromaDB + Appwrite (or lighter alternative)
- Health check endpoints for each service

### 4. Long-Term (1-2 Months — Architecture Optimization)

- Evaluate ADK replacement: direct OpenRouter calls + asyncio loop vs ADK event system
- Consider full-context mode (bypass RAG with large context window)
- Add optional Cloudflare Vectorize for production vector store
- Implement token usage tracking and budgeting for free tier

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| LiteLlm/ADK breaks with OpenRouter API change | Medium | High (agent stops working) | ADK fallback layer, model rotation plan |
| Appwrite migration incomplete | High | High (can't deploy anywhere) | Dedicated migration sprint, no new features until done |
| Free model rate limits during peak hours | Medium | Medium (users get 503s) | Queueing, retry with backoff, model fallback chain |
| ChromaDB memory usage on small VPS | Medium | Medium (OOM kills) | Limit collection size, batch cleanup, add swap |
| Firestore costs without Appwrite migration | Low (no users) | High (scales with usage) | Complete migration before public launch |
| Dual config drift (API vs AGENT models) | Medium | Medium (inconsistent behavior) | Single config file, validate both use same model ID |

---

**Feedback prompt:** How was this UltraThink session? Too deep? Too shallow? Missing something I should have caught?
