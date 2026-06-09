"""Dependency injection for FastAPI routes."""

from functools import lru_cache
from config.settings import Settings, settings as _settings
from src.orchestrator.graph import ReviewOrchestrator


@lru_cache
def get_settings() -> Settings:
    return _settings


_orchestrator: ReviewOrchestrator | None = None


def get_orchestrator() -> ReviewOrchestrator:
    """Return the global orchestrator singleton, initialized on first call."""
    global _orchestrator
    if _orchestrator is None:
        from src.agents.factory import register_agents
        register_agents()
        _orchestrator = ReviewOrchestrator()
    return _orchestrator
