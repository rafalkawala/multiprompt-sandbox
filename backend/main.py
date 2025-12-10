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
                existing.name = item.get("display_name", item.get("name", existing.name)) # Use display_name as name if avail
                existing.endpoint = item.get("endpoint", getattr(existing, "endpoint", None)) # Handle endpoint if schema allows (schema doesn't have endpoint col? Check model.)
                # Wait, ModelConfig schema doesn't have 'endpoint' or 'display_name'. It has 'name'.
                # Mapping: json 'display_name' -> db 'name'.
                existing.name = item.get("display_name", item.get("model_name"))
                
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
