"""Top-level API router."""

from fastapi import APIRouter

from backend.api.documents import router as documents_router
from backend.api.health import router as health_router
from backend.api.relationships import router as relationships_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(documents_router)
api_router.include_router(relationships_router)
