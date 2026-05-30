"""OpenRouter model registration for Google ADK via LiteLLM.

LiteLLM natively supports the openrouter/ provider prefix, which
auto-reads OPENROUTER_API_KEY and routes to the correct endpoint.
We keep the openrouter/ prefix as-is and let LiteLLM handle routing.
"""

import os
import logging

from google.adk.models.registry import LLMRegistry
from google.adk.models.lite_llm import LiteLlm

logger = logging.getLogger(__name__)


class OpenRouterLiteLlm(LiteLlm):
    """LiteLlm subclass routing all requests through OpenRouter.

    Model format: openrouter/<actual-model-id>
    e.g. openrouter/nvidia/nemotron-3-super-120b-a12b:free

    The openrouter/ prefix is kept as-is — LiteLLM natively supports it
    and reads OPENROUTER_API_KEY from the environment automatically.
    """

    @classmethod
    def supported_models(cls) -> list[str]:
        """Match all models with the openrouter/ prefix."""
        return [r"openrouter/.*"]

    def __init__(self, model: str, **kwargs):
        # Keep the openrouter/ prefix — LiteLLM handles it natively
        litellm_model = model

        # Set the OpenRouter headers for identification
        kwargs.setdefault("extra_headers", {
            "HTTP-Referer": "https://github.com/awun8191/RAST",
            "X-Title": "RAST Research Assistant",
        })

        # Call parent — LiteLLM reads OPENROUTER_API_KEY automatically
        super().__init__(model=litellm_model, **kwargs)


def register_openrouter_models():
    """Register OpenRouter models with ADK's LLMRegistry."""
    LLMRegistry.register(OpenRouterLiteLlm)
    logger.info("Registered OpenRouter models with LLMRegistry")
