# ResearchDoi

Academic research paper management platform with AI-powered research assistance. Search, retrieve, and generate structured thesis documents using a multi-agent orchestration pipeline.

## Status — Fully Operational

| Component | Status | Detail |
|---|---|---|
| Backend API | ✅ | 36 tests passing, FastAPI + Firestore |
| Frontend | ✅ | React + Vite, 0 lint errors, production build |
| AI Agent | ✅ | google-adk v1.25, oracle transfer architecture |

## Architecture

```
ResearchDoi/
├── API/          # FastAPI backend — DOI lookup, PDF resolution, RAG, chat
├── ResearchDoi/  # React frontend — project workspace, chat UI, paper views
├── AGENT/        # AI agent system — google-adk orchestration
├── docs/         # Documentation and specs
└── design-system/# Design assets
```

### Agent System Architecture

The AGENT uses Google ADK with a **three-layer orchestration** pattern:

1. **Orchestrator** (`the_Orchestrator`) — LlmAgent that routes tasks to specialized sub-agents via `TransferToAgentTool`
2. **Specialist agents** — Four SequentialAgents, each composed of worker + returner:
   - `autonomous_deep_research` — arxiv/Exa web research with recursive paper discovery
   - `url_analyst` — URL content extraction and summarization
   - `thesis_writing_pipeline` — Multi-stage thesis section writing with query expansion, retrieval, assembly, writing, citation, review
   - `autonomous_thesis_generator` — End-to-end 5-chapter thesis generation (discovery → planning → director loop → bibliography → finalizer)
3. **Pipeline internals** — Sub-agents for RAG ingestion, citation formatting, document assembly

## Prerequisites

- Python 3.11+
- Node.js 20+
- UV package manager (`pip install uv`)
- API keys in `.env` files:
  - OpenRouter (for LLM routing)
  - EXA (for web search)
  - Firebase service account (for Firestore)
  - Gemini API key (optional fallback)

## Quick Start

```bash
# Clone
git clone https://github.com/awun8191/ResearchDoi.git
cd ResearchDoi

# Setup API
cd API
cp .env.example .env  # Fill in keys
uv sync
uv run python -m pytest -q  # Verify: 36 passed

# Setup Frontend
cd ../ResearchDoi
npm install
npm run build         # Verify: production build ok
npm run lint          # Verify: 0 errors, 0 warnings

# Setup Agent
cd ../AGENT
cp .env.example .env  # Fill in keys
uv sync
uv run python smoke_test_pipeline.py  # Verify: pipeline mock test passes
```

## Development

```bash
# API — live reload
cd API && uv run uvicorn src.main:app --reload

# Frontend — dev server with HMR
cd ResearchDoi && npm run dev

# Agent — standalone ADK server
cd AGENT && uv run python src/main.py
```

## Components

### API
FastAPI service with endpoints for DOI resolution (`doi.org` / Crossref), PDF ingestion (arxiv, direct URL), RAG vector storage (Firestore), project management, and Gemini-based chat. Includes a mock LLM mode (`MOCK_LLM=true`) for testing without API keys.

### Frontend
React SPA with project workspace, chat interface, paper discovery, and thesis writing workflow. Built with Vite, Tailwind CSS, framer-motion, and the Google ADK web client.

### AGENT
Python agent system powered by `google-adk`. Uses `LiteLlm` for model routing through OpenRouter. Architectures:
- **Mock mode** (`MOCK_LLM=true`) — deterministic mock responses for integration testing
- **Live mode** — routes through OpenRouter to configured models

## License

Private — All rights reserved.
