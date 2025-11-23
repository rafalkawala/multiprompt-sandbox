"""
Model Configuration API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import httpx
import logging

from core.database import SessionLocal
from models.evaluation import ModelConfig
from models.user import User
from api.v1.auth import get_current_user

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
    api_key: str
    temperature: float = 0.0
    max_tokens: int = 1024
    additional_params: Optional[dict] = None

class ModelConfigUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    additional_params: Optional[dict] = None
    is_active: Optional[bool] = None

class ModelConfigResponse(BaseModel):
    id: str
    name: str
    provider: str
    model_name: str
    temperature: float
    max_tokens: int
    additional_params: Optional[dict]
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
        additional_params=data.additional_params,
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
        additional_params=config.additional_params,
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
        additional_params=config.additional_params,
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
        additional_params=config.additional_params,
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
    import time

    config = db.query(ModelConfig).filter(
        ModelConfig.id == config_id,
        ModelConfig.created_by_id == current_user.id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Model config not found")

    start_time = time.time()

    try:
        if config.provider == 'gemini':
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{config.model_name}:generateContent",
                    params={"key": config.api_key},
                    json={
                        "contents": [{"parts": [{"text": data.prompt}]}],
                        "generationConfig": {
                            "temperature": config.temperature,
                            "maxOutputTokens": config.max_tokens
                        }
                    }
                )

            latency = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                return TestResponse(
                    success=False,
                    error=f"API error ({response.status_code}): {response.text}",
                    latency_ms=latency
                )

            result = response.json()
            text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')

            return TestResponse(
                success=True,
                response=text,
                latency_ms=latency
            )

        elif config.provider == 'openai':
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {config.api_key}"},
                    json={
                        "model": config.model_name,
                        "messages": [{"role": "user", "content": data.prompt}],
                        "temperature": config.temperature,
                        "max_tokens": config.max_tokens
                    }
                )

            latency = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                return TestResponse(
                    success=False,
                    error=f"API error ({response.status_code}): {response.text}",
                    latency_ms=latency
                )

            result = response.json()
            text = result.get('choices', [{}])[0].get('message', {}).get('content', '')

            return TestResponse(
                success=True,
                response=text,
                latency_ms=latency
            )

        elif config.provider == 'anthropic':
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": config.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": config.model_name,
                        "max_tokens": config.max_tokens,
                        "messages": [{"role": "user", "content": data.prompt}]
                    }
                )

            latency = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                return TestResponse(
                    success=False,
                    error=f"API error ({response.status_code}): {response.text}",
                    latency_ms=latency
                )

            result = response.json()
            text = result.get('content', [{}])[0].get('text', '')

            return TestResponse(
                success=True,
                response=text,
                latency_ms=latency
            )

        else:
            return TestResponse(
                success=False,
                error=f"Unknown provider: {config.provider}"
            )

    except Exception as e:
        latency = int((time.time() - start_time) * 1000)
        logger.error(f"Test error: {str(e)}", exc_info=True)
        return TestResponse(
            success=False,
            error=str(e),
            latency_ms=latency
        )
