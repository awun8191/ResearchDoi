"""LiteLLM model configuration — all models via OpenRouter.

Primary: Nemotron 3 120B (NVIDIA)
Fallback: Gemma 4 30B (Google)
Embedding: Qwen3 Embedding 8B (Qwen)
"""

import os
import logging

from google.adk.models.lite_llm import LiteLlm

logger = logging.getLogger(__name__)

# ── Model Strings ────────────────────────────────────────────────────────────

# Primary reasoning model — used for planning, evaluation, synthesis
REASONING_MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"

# Fallback model — used if primary is rate-limited (429)
FALLBACK_MODEL = "openrouter/google/gemma-4-31b-it:free"

# Fast model — used for search, formatting, citation tasks
FAST_MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"

# Embedding model — used for semantic operations
EMBEDDING_MODEL = "openrouter/qwen/qwen3-embedding-8b"

# ── LiteLlm Instances ───────────────────────────────────────────────────────

def create_reasoning_llm() -> LiteLlm:
    """Create the primary reasoning LLM instance (Nemotron 3 120B)."""
    return LiteLlm(model=REASONING_MODEL)


def create_fallback_llm() -> LiteLlm:
    """Create the fallback LLM instance (Gemma 4 30B)."""
    return LiteLlm(model=FALLBACK_MODEL)


def create_fast_llm() -> LiteLlm:
    """Create the fast LLM instance (Nemotron 3 120B for quick tasks)."""
    return LiteLlm(model=FAST_MODEL)


# ── Singleton Instances ─────────────────────────────────────────────────────

reasoning_llm: LiteLlm = create_reasoning_llm()
fallback_llm: LiteLlm = create_fallback_llm()
fast_llm: LiteLlm = create_fast_llm()


def get_llm(require_reasoning: bool = True) -> LiteLlm:
    """Return the appropriate LLM based on task type.

    Args:
        require_reasoning: If True, returns the primary Nemotron 3 model.
                          If False, returns the fast model.

    Returns:
        A LiteLlm instance.
    """
    return reasoning_llm if require_reasoning else fast_llm
