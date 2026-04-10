"""Shared dependencies for API routes."""

from __future__ import annotations

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential

from src.config import settings

_client: AIProjectClient | None = None


def get_project_client() -> AIProjectClient:
    """Lazy-init the Foundry project client."""
    global _client
    if _client is None:
        _client = AIProjectClient(
            endpoint=settings.project_endpoint,
            credential=DefaultAzureCredential(),
        )
    return _client
