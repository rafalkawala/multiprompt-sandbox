"""
Model Configuration API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
import structlog
import time
import json
import io

from core.database import SessionLocal
from models.evaluation import ModelConfig
from models.user import User
from api.v1.auth import get_current_user
from services.llm_service import get_llm_service

logger = structlog.get_logger(__name__)
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Schemas
class ModelConfigCreate(BaseModel):
    name: str
    provider: str  # 'gemini', 'openai', 'anthropic'
    model_name: str
    api_key: Optional[str] = None
    auth_type: str = "api_key"  # 'api_key', 'service_account', 'google_adc'
    temperature: float = 0.0
    max_tokens: int = 1024
    concurrency: int = Field(default=3, ge=1, le=100, description="Number of parallel API calls (1-100)")
    additional_params: Optional[dict] = None
    pricing_config: Optional[dict] = None  # Cost tracking configuration
    retry_config: Optional[dict] = None  # Retry configuration: {"max_attempts": 5, "initial_wait": 2, "max_wait": 30, "exponential_base": 2}

    @validator('concurrency')
    def validate_concurrency(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Concurrency must be between 1 and 100')
        return v

class ModelConfigUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    auth_type: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    concurrency: Optional[int] = Field(default=None, ge=1, le=100, description="Number of parallel API calls (1-100)")
    additional_params: Optional[dict] = None
    pricing_config: Optional[dict] = None  # Cost tracking configuration
    retry_config: Optional[dict] = None  # Retry configuration
    is_active: Optional[bool] = None

    @validator('concurrency')
    def validate_concurrency(cls, v):
        if v is not None and (v < 1 or v > 100):
            raise ValueError('Concurrency must be between 1 and 100')
        return v

class ModelConfigResponse(BaseModel):
    id: str
    name: str
    provider: str
    model_name: str
    auth_type: str
    temperature: float
    max_tokens: int
    concurrency: int
    additional_params: Optional[dict]
    pricing_config: Optional[dict]
    retry_config: Optional[dict]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class ModelConfigListItem(BaseModel):
    id: str
    name: str
    provider: str
    model_name: str
    auth_type: str
    is_active: bool
    created_at: datetime

class TestRequest(BaseModel):
    prompt: str

class TestResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None

class ImportResponse(BaseModel):
    message: str
    imported_count: int
    updated_count: int

# Endpoints
@router.get("/export")
async def export_model_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all model configurations as JSON"""
    configs = db.query(ModelConfig).all()

    export_data = []
    for c in configs:
        data = {
            "id": str(c.id), # Include ID to allow updates
            "name": c.name,
            "provider": c.provider,
            "model_name": c.model_name,
            "auth_type": c.auth_type,
            "temperature": c.temperature,
            "max_tokens": c.max_tokens,
            "concurrency": c.concurrency,
            "additional_params": c.additional_params,
            "pricing_config": c.pricing_config,
            "retry_config": c.retry_config,
            "is_active": c.is_active
            # Exclude API Key for security
        }
        export_data.append(data)

    json_str = json.dumps(export_data, indent=2)
    stream = io.StringIO(json_str)

    return StreamingResponse(
        stream,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=model_configs_export.json"}
    )

@router.post("/import", response_model=ImportResponse)
async def import_model_configs(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import model configurations from JSON file"""
    try:
        content = await file.read()
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="JSON root must be a list of model objects")

    imported = 0
    updated = 0

    for item in data:
        # Validate minimal required fields
        if not all(k in item for k in ("name", "provider", "model_name")):
            continue

        existing = None
        if "id" in item and item["id"]:
            # Try to match by ID for update
            existing = db.query(ModelConfig).filter(
                ModelConfig.id == item["id"]
            ).first()

        if existing:
            # Update existing
            existing.name = item.get("name", existing.name)
            existing.provider = item.get("provider", existing.provider)
            existing.model_name = item.get("model_name", existing.model_name)
            existing.auth_type = item.get("auth_type", existing.auth_type)
            existing.temperature = item.get("temperature", existing.temperature)
            existing.max_tokens = item.get("max_tokens", existing.max_tokens)
            existing.concurrency = item.get("concurrency", existing.concurrency)
            existing.additional_params = item.get("additional_params", existing.additional_params)
            existing.pricing_config = item.get("pricing_config", existing.pricing_config)
            existing.retry_config = item.get("retry_config", existing.retry_config)
            existing.is_active = item.get("is_active", existing.is_active)
            if "api_key" in item and item["api_key"]:
                existing.api_key = item["api_key"]
            updated += 1
        else:
            # Create new (Add)
            # Ignore ID from JSON to allow creation of new record with fresh UUID
            new_config = ModelConfig(
                name=item["name"],
                provider=item["provider"],
                model_name=item["model_name"],
                api_key=item.get("api_key", "sk-placeholder"),
                auth_type=item.get("auth_type", "api_key"),
                temperature=item.get("temperature", 0.0),
                max_tokens=item.get("max_tokens", 1024),
                concurrency=item.get("concurrency", 3),
                additional_params=item.get("additional_params", {}),
                pricing_config=item.get("pricing_config", {}),
                retry_config=item.get("retry_config"),
                is_active=item.get("is_active", True),
                created_by_id=current_user.id
            )
            db.add(new_config)
            imported += 1

    db.commit()
    return ImportResponse(
        message="Import completed successfully",
        imported_count=imported,
        updated_count=updated
    )

@router.get("", response_model=List[ModelConfigListItem])
async def list_model_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all model configurations for current user"""
    configs = db.query(ModelConfig).order_by(ModelConfig.created_at.desc()).all()

    return [
        ModelConfigListItem(
            id=str(c.id),
            name=c.name,
            provider=c.provider,
            model_name=c.model_name,
            auth_type=c.auth_type,
            is_active=c.is_active,
            created_at=c.created_at
        )
        for c in configs
    ]

@router.post("", response_model=ModelConfigResponse)
async def create_model_config(
    data: ModelConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new model configuration"""
    config = ModelConfig(
        name=data.name,
        provider=data.provider,
        model_name=data.model_name,
        api_key=data.api_key,
        auth_type=data.auth_type,
        temperature=data.temperature,
        max_tokens=data.max_tokens,
        concurrency=data.concurrency,
        additional_params=data.additional_params,
        pricing_config=data.pricing_config,
        retry_config=data.retry_config,
        created_by_id=current_user.id
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    return ModelConfigResponse(
        id=str(config.id),
        name=config.name,
        provider=config.provider,
        model_name=config.model_name,
        auth_type=config.auth_type,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        concurrency=config.concurrency,
        additional_params=config.additional_params,
        pricing_config=config.pricing_config,
        retry_config=config.retry_config,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at
    )

@router.get("/{config_id}", response_model=ModelConfigResponse)
async def get_model_config(
    config_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific model configuration"""
    config = db.query(ModelConfig).filter(
        ModelConfig.id == config_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")

    return ModelConfigResponse(
        id=str(config.id),
        name=config.name,
        provider=config.provider,
        model_name=config.model_name,
        auth_type=config.auth_type,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        concurrency=config.concurrency,
        additional_params=config.additional_params,
        pricing_config=config.pricing_config,
        retry_config=config.retry_config,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at
    )

@router.patch("/{config_id}", response_model=ModelConfigResponse)
async def update_model_config(
    config_id: str,
    data: ModelConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a model configuration"""
    config = db.query(ModelConfig).filter(
        ModelConfig.id == config_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)

    return ModelConfigResponse(
        id=str(config.id),
        name=config.name,
        provider=config.provider,
        model_name=config.model_name,
        auth_type=config.auth_type,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        concurrency=config.concurrency,
        additional_params=config.additional_params,
        pricing_config=config.pricing_config,
        retry_config=config.retry_config,
        is_active=config.is_active,
        created_at=config.created_at,
        updated_at=config.updated_at
    )

@router.delete("/{config_id}")
async def delete_model_config(
    config_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a model configuration"""
    config = db.query(ModelConfig).filter(
        ModelConfig.id == config_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")

    db.delete(config)
    db.commit()
    return {"message": "Model config deleted"}

@router.post("/{config_id}/test", response_model=TestResponse)
async def test_model_config(
    config_id: str,
    data: TestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test a model configuration with a simple text prompt"""
    config = db.query(ModelConfig).filter(
        ModelConfig.id == config_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")

    start_time = time.time()

    try:
        llm_service = get_llm_service()
        
        response_text, latency, usage = await llm_service.generate_content(
            provider_name=config.provider,
            api_key=config.api_key,
            auth_type=config.auth_type,
            model_name=config.model_name,
            prompt=data.prompt,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )

        return TestResponse(
            success=True,
            response=response_text,
            latency_ms=latency
        )

    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        logger.error(f"Test error: {str(e)}", exc_info=True)
        return TestResponse(
            success=False,
            error=str(e),
            latency_ms=latency
        )