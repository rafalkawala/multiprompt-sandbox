"""
Model Configuration API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import httpx
import logging
import time

from core.database import SessionLocal
from models.evaluation import ModelConfig
from models.user import User
from api.v1.auth import get_current_user
from services.llm_service import get_llm_service

logger = logging.getLogger(__name__)
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
    api_key: Optional[str] = None  # Optional - will use service account auth if empty
    temperature: float = 0.0
    max_tokens: int = 1024
    concurrency: int = Field(default=3, ge=1, le=100, description="Number of parallel API calls (1-100)")
    additional_params: Optional[dict] = None
    pricing_config: Optional[dict] = None  # Cost tracking configuration

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
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    concurrency: Optional[int] = Field(default=None, ge=1, le=100, description="Number of parallel API calls (1-100)")
    additional_params: Optional[dict] = None
    pricing_config: Optional[dict] = None  # Cost tracking configuration
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
    temperature: float
    max_tokens: int
    concurrency: int
    additional_params: Optional[dict]
    pricing_config: Optional[dict]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class ModelConfigListItem(BaseModel):
    id: str
    name: str
    provider: str
    model_name: str
    is_active: bool
    created_at: datetime

class TestRequest(BaseModel):
    prompt: str

class TestResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[int] = None

# Endpoints
@router.get("", response_model=List[ModelConfigListItem])
async def list_model_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all model configurations for current user"""
    configs = db.query(ModelConfig).filter(
        ModelConfig.created_by_id == current_user.id
    ).order_by(ModelConfig.created_at.desc()).all()

    return [
        ModelConfigListItem(
            id=str(c.id),
            name=c.name,
            provider=c.provider,
            model_name=c.model_name,
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
        temperature=data.temperature,
        max_tokens=data.max_tokens,
        concurrency=data.concurrency,
        additional_params=data.additional_params,
        pricing_config=data.pricing_config,
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
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        concurrency=config.concurrency,
        additional_params=config.additional_params,
        pricing_config=config.pricing_config,
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
        ModelConfig.id == config_id,
        ModelConfig.created_by_id == current_user.id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")

    return ModelConfigResponse(
        id=str(config.id),
        name=config.name,
        provider=config.provider,
        model_name=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        concurrency=config.concurrency,
        additional_params=config.additional_params,
        pricing_config=config.pricing_config,
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
        ModelConfig.id == config_id,
        ModelConfig.created_by_id == current_user.id
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
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        concurrency=config.concurrency,
        additional_params=config.additional_params,
        pricing_config=config.pricing_config,
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
        ModelConfig.id == config_id,
        ModelConfig.created_by_id == current_user.id
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
        ModelConfig.id == config_id,
        ModelConfig.created_by_id == current_user.id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")

    start_time = time.time()

    try:
        llm_service = get_llm_service()
        
        response_text, latency = await llm_service.generate_content(
            provider_name=config.provider,
            api_key=config.api_key,
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