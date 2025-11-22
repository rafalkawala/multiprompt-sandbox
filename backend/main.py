"""
Main FastAPI application entry point
"""
import os
# Disable LangSmith tracing before any imports (only if not explicitly configured)
if not os.environ.get("LANGCHAIN_TRACING_V2"):
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
if not os.environ.get("LANGCHAIN_ENDPOINT"):
    os.environ["LANGCHAIN_ENDPOINT"] = ""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from core.config import settings
from core.database import SessionLocal
from api.v1 import api_router
from models.user import User, UserRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MultiPrompt Sandbox API with LangChain agents and Gemini Pro",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def sync_admin_users():
    """Sync admin users from ADMIN_EMAILS on startup"""
    admin_emails = settings.ADMIN_EMAIL_LIST
    if not admin_emails:
        logger.info("No ADMIN_EMAILS configured, skipping admin sync")
        return

    logger.info(f"Syncing admin users: {admin_emails}")
    db = SessionLocal()
    try:
        for email in admin_emails:
            user = db.query(User).filter(User.email.ilike(email)).first()
            if user:
                if user.role != UserRole.ADMIN.value:
                    user.role = UserRole.ADMIN.value
                    db.commit()
                    logger.info(f"Upgraded user {email} to admin")
                else:
                    logger.info(f"User {email} is already admin")
            else:
                logger.info(f"User {email} not found in database (will get admin on first login)")
    except Exception as e:
        logger.error(f"Error syncing admin users: {e}")
    finally:
        db.close()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MultiPrompt Sandbox API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    # Add checks for database, external services, etc.
    return {"status": "ready"}


# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
