"""FastAPI application factory with lifespan management."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from config.settings import settings
from .router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: register agents and tools. Shutdown: clean up connections."""
    logger.info("Starting %s v%s (LLM: %s)", settings.APP_NAME, settings.APP_VERSION, settings.LLM_PROVIDER)
    from src.agents.factory import register_agents
    register_agents()
    logger.info("Agents registered")
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Multi-Agent Code Review & Auto-Fix System",
        lifespan=lifespan,
    )

    # CORS — allow dashboard dev from localhost
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(api_router)

    # Health check
    @app.get("/api/v1/health", tags=["health"])
    async def health_check():
        from src.agents.base import agent_registry
        agent_health = await agent_registry.health_check_all()
        return {
            "status": "healthy" if all(agent_health.values()) else "degraded",
            "version": settings.APP_VERSION,
            "llm_provider": settings.LLM_PROVIDER,
            "agents": agent_health,
        }

    # Static dashboard (if exists)
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists() and any(static_dir.iterdir()):
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
