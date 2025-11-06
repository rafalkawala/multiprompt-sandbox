"""
API v1 router
"""
from fastapi import APIRouter
from app.api.v1.endpoints import agents, images

api_router = APIRouter()

api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
