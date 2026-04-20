import asyncio

from src.agent import structured_writing_pipeline
from src.research import pipeline


class _FakeSession:
    def __init__(self) -> None:
        self.state: dict = {}


class _FakeInvocationContext:
    def __init__(self) -> None:
        self.session = _FakeSession()
        self.user_id = "smoke-user"


async def _fake_semantic_scholar_search_tool(query: str, limit: int = 10):
    return [
        {
            "source_id": "10.1000/test-doi",
            "paper_id": "paper-1",
            "title": "Dummy Paper",
            "authors": ["Jane Doe", "John Smith"],
            "year": 2024,
            "doi": "10.1000/test-doi",
            "doi_url": "https://doi.org/10.1000/test-doi",
            "abstract": f"Abstract for {query}",
            "venue": "Journal of Testing",
            "citations": 5,
        }
    ]


async def _fake_research_retrieval_tool(
    query: str, project_id: str, uid: str, top_k: int = 20
):
    return [
        {
            "text": f"Corpus evidence about {query}",
            "doi": "10.1000/test-doi",
            "section": "Methodology",
            "score": 0.8,
            "title": "Dummy Paper",
            "authors": ["Jane Doe", "John Smith"],
            "year": 2024,
            "venue": "Journal of Testing",
        }
    ]


async def _drain(agent, ctx) -> None:
    async for _ in agent._run_async_impl(ctx):
        pass


async def main() -> None:
    if structured_writing_pipeline.name != "RastFullPipeline":
        raise RuntimeError("Research pipeline failed to initialize.")

    pipeline.semantic_scholar_search_tool = _fake_semantic_scholar_search_tool
    pipeline.research_retrieval_tool = _fake_research_retrieval_tool

    ctx = _FakeInvocationContext()
    ctx.session.state["project_id"] = "dummy-project"
    ctx.session.state["query_intent"] = {
        "research_topic": "dummy research topic",
        "expanded_queries": ["dummy research topic retrieval query"],
        "task_type": "literature review",
        "target_section": "Methods",
    }

    await _drain(pipeline.MultiQueryRetrievalAgent(), ctx)
    await _drain(pipeline.ContextAssemblyAgent(), ctx)

    ctx.session.state["draft_content"] = (
        "This is grounded in prior work [CIT: 10.1000/test-doi]."
    )
    await _drain(pipeline.CitationAgent(model=None), ctx)

    final_draft = ctx.session.state.get("final_draft", "")
    if "(Doe & Smith, 2024)" not in final_draft:
        raise RuntimeError("CitationAgent did not replace citation placeholders.")
    if "## References" not in final_draft:
        raise RuntimeError("CitationAgent did not append a references section.")

    print("Smoke test passed.")
    print(final_draft)


if __name__ == "__main__":
    asyncio.run(main())
