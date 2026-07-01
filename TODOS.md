# TODOS

## ~~Frontend and E2E Testing~~ (DONE)
* ~~**What:** Add Vitest for React components and Playwright for E2E flows.~~
* ~~**Why:** We compromised on backend-only tests for the hackathon MVP, leaving the UI untested.~~
* ~~**Pros:** Prevents UI regressions in the complex dual-pane layout.~~
* ~~**Cons:** Slower iteration speed right now.~~
* ~~**Context:** The JSON Patch stream handling in React will be complex and prone to bugs.~~
* ~~**Depends on / blocked by:** Needs the core JSON Patch UI to be stable first.~~

## ~~Deterministic Citation Linking~~ (DONE)
* ~~**What:** Build a mechanism to deterministically link generated text to retrieved RAG sources.~~
* ~~**Why:** Standard RAG injects context into the prompt, but LLMs often hallucinate or misattribute citations in long-form generation.~~
* ~~**Pros:** Ensures academic integrity and builds user trust.~~
* ~~**Cons:** Requires complex prompt engineering and post-generation validation steps.~~
* ~~**Context:** The outside voice flagged this as a massive assumption for the MVP.~~
* ~~**Depends on / blocked by:** The core RAG pipeline (ArXiv/Exa) being operational.~~

## ~~Context Window Management~~ (DONE)
* ~~**What:** Implement context summarization or sliding windows for the active document state.~~
* ~~**Why:** The LLM needs the current draft to write cohesively, but feeding the entire document + chat history + RAG chunks will eventually blow past context limits.~~
* ~~**Pros:** Prevents the app from crashing on long research papers.~~
* ~~**Cons:** Increases complexity of the orchestrator state management.~~
* ~~**Context:** RAG solves knowledge retrieval, but not active document state size.~~
* ~~**Depends on / blocked by:** Hitting context limits in real usage.~~
