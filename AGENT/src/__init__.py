"""ResearchDoi agent package.

The package stays light on purpose. A module that needs one setting imports the
helpers here. The helpers do not load the ADK stack.
"""

import os


class MissingApiKeyError(RuntimeError):
    """Raised when the ResearchDoi API key is absent from the environment."""


def require_api_key() -> str:
    """Return the API key from the environment, or raise MissingApiKeyError.

    There is no default value. A silent default hides a broken deployment and
    sends an unusable key to the API.
    """

    api_key = os.environ.get("API_KEY", "").strip()
    if not api_key:
        raise MissingApiKeyError(
            "API_KEY is not set. Set API_KEY in the environment or in AGENT/.env "
            "before you start the agent. See AGENT/.env.example. "
            "The agent client has no default key and stops here."
        )
    return api_key
