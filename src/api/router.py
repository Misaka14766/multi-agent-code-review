"""Top-level API router — includes all sub-routers."""

from fastapi import APIRouter
from .routes.review import router as review_router
from .routes.webhook import router as webhook_router
from .routes.dashboard import router as dashboard_router

api_router = APIRouter()
api_router.include_router(review_router)
api_router.include_router(webhook_router)
api_router.include_router(dashboard_router)
