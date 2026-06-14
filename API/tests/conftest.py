"""
Pytest conftest — shared fixtures for RAST API tests.
"""

import pytest


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Apply test-safe settings for all tests — no real API keys needed."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("UNPAYWALL_EMAIL", "test@example.com")

    # Reload settings after env patching
    from src.core.config import settings
    settings.openrouter_api_key = "sk-or-test-key"
    settings.api_key = "test-api-key"
    settings.unpaywall_email = "test@example.com"
