import os
import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional
from google.adk.models.lite_llm import LiteLlm
from google.adk.models import LlmRequest, LlmResponse
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
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        # Simulate a small delay for realism
        await asyncio.sleep(0.01)
        
        # If we have too many turns in history, exit any loops
        if len(llm_request.contents) > 10:
             if llm_request.tools_dict and "exit_loop" in llm_request.tools_dict:
                 part = types.Part(function_call=types.FunctionCall(name="exit_loop", args={}))
                 yield LlmResponse(content=types.Content(role="model", parts=[part]), finish_reason="STOP", partial=False)
                 return
             else:
                 yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="[MOCK EXIT] Terminating long conversation.")]), finish_reason="STOP", partial=False)
                 return

        # Determine if we should perform a TransferToAgentTool call
        if llm_request.tools_dict:
            # Handle TransferToAgentTool
            transfer_tool_name = next((name for name in llm_request.tools_dict.keys() if "transfer_to_" in name), None)
            if transfer_tool_name:
                # Only transfer if it's the first turn or we haven't transferred yet
                if len(llm_request.contents) < 5:
                    target = "autonomous_deep_research"
                    if "url" in str(llm_request.contents).lower():
                        target = "url_analyst"
                    
                    part = types.Part(
                        function_call=types.FunctionCall(
                            name=transfer_tool_name, 
                            args={"agent_name": target}
                        )
                    )
                    yield LlmResponse(
                        content=types.Content(role="model", parts=[part]),
                        finish_reason="STOP",
                        partial=False
                    )
                    return

            # Handle other tools like arxiv_search_tool, etc.
            # But only if we haven't been looping too much
            tool_name = list(llm_request.tools_dict.keys())[0]
            if tool_name != "exit_loop":
                part = types.Part(
                    function_call=types.FunctionCall(
                        name=tool_name,
                        args={"query": "quantum computing"}
                    )
                )
                yield LlmResponse(
                    content=types.Content(role="model", parts=[part]),
                    finish_reason="STOP",
                    partial=False
                )
                return

        # Default text response
        yield LlmResponse(
            content=types.Content(
                role="model", 
                parts=[types.Part(text="[MOCK RESPONSE] This is a simulated response to verify the ADK orchestration logic.")]
            ),
            finish_reason="STOP",
            partial=False
        )

# Initialize the model
if MOCK_LLM:
    primary_model = MockLiteLlm(model="openrouter/google/gemma-4-31b-it:free")
    writing_model = MockLiteLlm(model="openrouter/google/gemma-4-31b-it:free")
else:
    primary_model = LiteLlm(model="openrouter/cohere/north-mini-code:free")
    writing_model = LiteLlm(model="openrouter/cohere/north-mini-code:free")

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
        "research_topic": "",
        "target_section": "",
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
