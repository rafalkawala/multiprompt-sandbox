"""
API v1 router
"""
from fastapi import APIRouter
# Temporarily disable agents endpoint due to import issues
# from api.v1 import agents, images
from api.v1 import images, auth, users, projects, datasets, annotations, model_configs, evaluations

api_router = APIRouter()

# api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(datasets.router, prefix="/projects", tags=["datasets"])
api_router.include_router(annotations.router, prefix="", tags=["annotations"])
api_router.include_router(model_configs.router, prefix="/model-configs", tags=["model-configs"])
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
