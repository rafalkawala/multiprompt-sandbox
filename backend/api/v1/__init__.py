"""
API v1 router
"""
from fastapi import APIRouter
# Temporarily disable agents endpoint due to import issues
# from api.v1 import agents, images
from api.v1 import images

api_router = APIRouter()

# api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
