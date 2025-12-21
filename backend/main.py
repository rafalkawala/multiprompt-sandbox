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
import structlog
from core.logging_config import configure_logging

from core.config import settings
from core.database import SessionLocal
from api.v1 import api_router
from models.user import User, UserRole

# Configure logging
configure_logging()
logger = structlog.get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MultiPrompt Sandbox API with LangChain agents and Gemini Pro",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    redirect_slashes=False  # Prevent 307 redirects that strip Authorization headers
)

# Configure CORS
allowed_origins = settings.ALLOWED_ORIGINS
logger.info(f"Configuring CORS with allowed origins: {allowed_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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

@app.on_event("startup")
async def seed_model_configs():
    """Seed model configurations from models.json on startup"""
    import json
    from models.evaluation import ModelConfig
    import os
    
    config_path = os.path.join(os.path.dirname(__file__), "config", "models.json")
    if not os.path.exists(config_path):
        logger.warning(f"Model config seed file not found at {config_path}")
        return

    logger.info(f"Seeding model configs from {config_path}")
    db = SessionLocal()
    try:
        # Find an admin user to own these configs
        admin = db.query(User).filter(User.role == UserRole.ADMIN.value).first()
        if not admin:
            # Fallback to any user
            admin = db.query(User).first()
        
        if not admin:
            logger.warning("No users found in database. Skipping model config seeding.")
            return

        with open(config_path, 'r') as f:
            data = json.load(f)

        imported = 0
        updated = 0

        for item in data:
            # Check for existing config
            existing = db.query(ModelConfig).filter(
                ModelConfig.created_by_id == admin.id,
                ModelConfig.provider == item["provider"],
                ModelConfig.model_name == item["model_name"]
            ).first()

            if existing:
                # Update essential fields
                existing.name = item.get("display_name", item.get("model_name"))
                existing.auth_type = item.get("auth_type", "api_key")
                existing.temperature = item.get("temperature", 0.0)
                existing.max_tokens = item.get("max_tokens", 1024)
                existing.pricing_config = item.get("pricing_config", existing.pricing_config)
                # Keep API key if set in DB, unless seed has one? Seed usually doesn't have secrets.
                updated += 1
            else:
                new_config = ModelConfig(
                    name=item.get("display_name", item.get("model_name")),
                    provider=item["provider"],
                    model_name=item["model_name"],
                    api_key="sk-placeholder", # Placeholder
                    auth_type=item.get("auth_type", "api_key"),
                    temperature=0.0,
                    max_tokens=1024,
                    concurrency=3,
                    pricing_config=item.get("pricing_config", {}),
                    is_active=True,
                    created_by_id=admin.id
                )
                db.add(new_config)
                imported += 1
        
        db.commit()
        logger.info(f"Model config seeding complete: {imported} imported, {updated} updated.")

    except Exception as e:
        logger.error(f"Error seeding model configs: {e}")
    finally:
        db.close()

@app.on_event("startup")
async def restart_interrupted_evaluations():
    """Restart evaluations that were interrupted by backend restart"""
    import threading
    from models.evaluation import Evaluation
    from api.v1.evaluations import run_evaluation_in_thread

    db = SessionLocal()
    try:
        # Find evaluations that were running when backend died
        interrupted = db.query(Evaluation).filter(
            Evaluation.status == 'running'
        ).all()

        if not interrupted:
            logger.info("No interrupted evaluations to restart")
            return

        logger.info(f"Found {len(interrupted)} interrupted evaluations, restarting...")

        for evaluation in interrupted:
            # Reset progress for clean restart
            evaluation.processed_images = 0
            evaluation.results_summary = {'latest_images': ['Restarting interrupted evaluation...']}
            db.commit()

            # Start in background thread
            thread = threading.Thread(
                target=run_evaluation_in_thread,
                args=(str(evaluation.id),),
                daemon=True
            )
            thread.start()
            logger.info(f"Restarted evaluation {evaluation.id}: {evaluation.name}")

    except Exception as e:
        logger.error(f"Error restarting interrupted evaluations: {e}")
    finally:
        db.close()

@app.on_event("shutdown")
async def shutdown_event():
    """Close resources on shutdown"""
    from core.http_client import HttpClient
    from core.database import engine
    
    logger.info("Closing database connections...")
    engine.dispose()
    
    await HttpClient.close()



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
