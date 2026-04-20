import os
import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional
from google.adk.models.lite_llm import LiteLlm
from google.adk.events import Event
from google.genai import types

# ── Centralized Model Definition ─────────────────────────────────────────────

# Configuration and Constants
MOCK_LLM = os.getenv("MOCK_LLM", "false").lower() == "true"

class MockLiteLlm(LiteLlm):
    """
    A Mock LLM provider for the ADK to ensure tests pass without valid API keys.
    It simulates tool calls for TransferToAgentTool and standard text responses.
    """
    async def generate_content_async(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Any]] = None,
        **kwargs
    ) -> AsyncGenerator[Any, None]:
        # Simulate a small delay for realism
        await asyncio.sleep(0.1)
        
        # Simple Mock Tool Call Class for Transfer
        class MockToolCall:
            def __init__(self, name, arguments):
                self.id = "call_mock_123"
                self.type = "function"
                self.function = type('obj', (object,), {'name': name, 'arguments': arguments})()

        class MockChoice:
            def __init__(self, content="", tool_calls=None):
                self.message = type('obj', (object,), {
                    'content': content, 
                    'tool_calls': tool_calls,
                    'role': 'model'
                })()
                self.finish_reason = "STOP"

        class MockResponse:
            def __init__(self, choices):
                self.choices = choices
                self.partial = False
                # Mock an Enum-like object for finish_reason
                self.finish_reason = type('obj', (object,), {'value': 'STOP'})()
                self.content = choices[0].message.content if choices else ""
                self.usage_metadata = type('obj', (object,), {
                    'prompt_token_count': 10,
                    'candidates_token_count': 20,
                    'total_token_count': 30
                })()

        # Determine if we should perform a TransferToAgentTool call
        if tools:
            transfer_tool = next((t for t in tools if hasattr(t, 'name') and t.name.startswith("transfer_to_")), None)
            if transfer_tool:
                yield MockResponse([MockChoice(tool_calls=[MockToolCall(transfer_tool.name, '{"thought": "Mocking handoff to sub-agent for research."}')])])
                return

        # Default text response
        yield MockResponse([MockChoice(content="[MOCK RESPONSE] Gemma-4-31b-it: This is a simulated response to verify the ADK orchestration logic.")])

# Initialize the model
if MOCK_LLM:
    primary_model = MockLiteLlm(model="openrouter/google/gemma-4-31b-it:free")
    writing_model = MockLiteLlm(model="openrouter/google/gemma-4-31b-it:free")
else:
    primary_model = LiteLlm(model="openrouter/minimax/minimax-m2.5:free")
    writing_model = LiteLlm(model="openrouter/minimax/minimax-m2.5:free")

# ── Session State Helpers ────────────────────────────────────────────────────

def init_session_state(state: dict[str, Any]):
    """Initializes standard session state variables with default values."""
    defaults = {
        "accumulated_research": "No research has been accumulated yet.",
        "search_plan": "No search plan generated yet.",
        "evaluation_status": {},
        "retrieved_chunks": [],
        "discovered_papers": [],
        "review_feedback": "No feedback yet.",
        "draft_content": "",
        "final_draft": "",
        "formatted_context": "",
        "source_metadata": [],
        "master_thesis_document": "# THE PROJECT THESIS\n\n",
        "granular_plan": [],
        "research_topic": "Autonomous Systems",
        "target_section": "General",
        "url": "",
        "url_findings": "No URL findings yet.",
        "url_context": "No URL context retrieved yet.",
        "thesis_download_url": "",
    }
    for key, value in defaults.items():
        if key not in state:
            state[key] = value

# ── Event Emission Helpers ───────────────────────────────────────────────────

def create_status_event(author: str, text: str) -> Event:
    """Creates a meaningful status event with model-role content."""
    return Event(
        author=author,
        content=types.Content(
            role="model",
            parts=[types.Part(text=text)]
        )
    )

async def emit_status(author: str, text: str) -> AsyncGenerator[Event, None]:
    """Helper to yield a status event in an async generator."""
    yield create_status_event(author, text)
