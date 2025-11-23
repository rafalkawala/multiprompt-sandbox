"""
Evaluation API endpoints with LLM integrations
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import httpx
import base64
import os
import logging
import json
import time

from core.database import SessionLocal
from core.prompt_config import get_system_prompt
from models.evaluation import ModelConfig, Evaluation, EvaluationResult
from models.project import Project, Dataset
from models.image import Image, Annotation
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
class EvaluationCreate(BaseModel):
    name: str
    project_id: str
    dataset_id: str
    model_config_id: str

class EvaluationResponse(BaseModel):
    id: str
    name: str
    project_id: str
    dataset_id: str
    model_config_id: str
    status: str
    progress: int
    total_images: int
    processed_images: int
    accuracy: Optional[float]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

class EvaluationListItem(BaseModel):
    id: str
    name: str
    project_name: str
    dataset_name: str
    model_name: str
    status: str
    progress: int
    accuracy: Optional[float]
    created_at: datetime

class EvaluationResultItem(BaseModel):
    id: str
    image_id: str
    image_filename: str
    model_response: Optional[str]
    parsed_answer: Optional[dict]
    ground_truth: Optional[dict]
    is_correct: Optional[bool]
    latency_ms: Optional[int]

# LLM Provider Functions
async def call_gemini(api_key: str, model_name: str, image_path: str, prompt: str, system_message: str, temperature: float, max_tokens: int) -> tuple:
    """Call Gemini API with image

    If api_key is provided, uses Google AI API (for local dev).
    If api_key is empty/None, uses Vertex AI with service account (for Cloud Run).
    """
    start_time = time.time()

    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = base64.standard_b64encode(f.read()).decode('utf-8')

    # Determine mime type
    ext = os.path.splitext(image_path)[1].lower()
    mime_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp'}
    mime_type = mime_types.get(ext, 'image/jpeg')

    # Combine system message with prompt
    full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt

    # Use Vertex AI if no API key (service account auth in Cloud Run)
    if not api_key:
        return await call_gemini_vertex(model_name, image_path, image_data, mime_type, full_prompt, temperature, max_tokens, start_time)

    # Use Google AI API with API key (local development)
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
            params={"key": api_key},
            json={
                "contents": [{
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": image_data}},
                        {"text": full_prompt}
                    ]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens
                }
            }
        )

    latency = int((time.time() - start_time) * 1000)

    if response.status_code != 200:
        raise Exception(f"Gemini API error: {response.text}")

    result = response.json()
    text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
    return text, latency

async def call_gemini_vertex(model_name: str, image_path: str, image_data: str, mime_type: str, prompt: str, temperature: float, max_tokens: int, start_time: float) -> tuple:
    """Call Gemini via Vertex AI using service account credentials (ADC)"""
    import google.auth
    import google.auth.transport.requests

    # Get credentials and project from ADC
    credentials, project = google.auth.default()

    # Get project from environment if not in credentials
    if not project:
        project = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('GCP_PROJECT')

    if not project:
        raise Exception("No GCP project found. Set GOOGLE_CLOUD_PROJECT environment variable.")

    # Refresh credentials to get access token
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)

    # Vertex AI endpoint
    location = os.environ.get('VERTEX_AI_LOCATION', 'us-central1')
    endpoint = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/{model_name}:generateContent"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json"
            },
            json={
                "contents": [{
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": image_data}},
                        {"text": prompt}
                    ]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens
                }
            }
        )

    latency = int((time.time() - start_time) * 1000)

    if response.status_code != 200:
        raise Exception(f"Vertex AI error: {response.text}")

    result = response.json()
    text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
    return text, latency

async def call_openai(api_key: str, model_name: str, image_path: str, prompt: str, system_message: str, temperature: float, max_tokens: int) -> tuple:
    """Call OpenAI API with image"""
    start_time = time.time()

    with open(image_path, 'rb') as f:
        image_data = base64.standard_b64encode(f.read()).decode('utf-8')

    ext = os.path.splitext(image_path)[1].lower()
    mime_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp'}
    mime_type = mime_types.get(ext, 'image/jpeg')

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}},
            {"type": "text", "text": prompt}
        ]
    })

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )

    latency = int((time.time() - start_time) * 1000)

    if response.status_code != 200:
        raise Exception(f"OpenAI API error: {response.text}")

    result = response.json()
    text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
    return text, latency

async def call_anthropic(api_key: str, model_name: str, image_path: str, prompt: str, system_message: str, temperature: float, max_tokens: int) -> tuple:
    """Call Anthropic API with image"""
    start_time = time.time()

    with open(image_path, 'rb') as f:
        image_data = base64.standard_b64encode(f.read()).decode('utf-8')

    ext = os.path.splitext(image_path)[1].lower()
    mime_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp'}
    mime_type = mime_types.get(ext, 'image/jpeg')

    request_body = {
        "model": model_name,
        "max_tokens": max_tokens,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": image_data}},
                {"type": "text", "text": prompt}
            ]
        }]
    }

    if system_message:
        request_body["system"] = system_message

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json=request_body
        )

    latency = int((time.time() - start_time) * 1000)

    if response.status_code != 200:
        raise Exception(f"Anthropic API error: {response.text}")

    result = response.json()
    text = result.get('content', [{}])[0].get('text', '')
    return text, latency

def parse_answer(response: str, question_type: str):
    """Parse model response based on question type"""
    response_lower = response.lower().strip()

    if question_type == 'binary':
        if any(word in response_lower for word in ['yes', 'true', '1']):
            return {'value': True}
        elif any(word in response_lower for word in ['no', 'false', '0']):
            return {'value': False}
        return {'value': None, 'raw': response}

    elif question_type == 'count':
        import re
        numbers = re.findall(r'\d+', response)
        if numbers:
            return {'value': int(numbers[0])}
        return {'value': None, 'raw': response}

    elif question_type == 'multiple_choice':
        return {'value': response.strip()}

    else:  # text
        return {'value': response.strip()}

def check_answer(parsed: dict, ground_truth: dict, question_type: str) -> bool:
    """Check if answer matches ground truth"""
    if parsed.get('value') is None or ground_truth is None:
        return False

    if question_type in ['binary', 'count']:
        return parsed.get('value') == ground_truth.get('value')
    else:
        # Text comparison - case insensitive
        return str(parsed.get('value', '')).lower().strip() == str(ground_truth.get('value', '')).lower().strip()

async def run_evaluation_task(evaluation_id: str):
    """Background task to run evaluation"""
    db = SessionLocal()
    try:
        evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
        if not evaluation:
            return

        evaluation.status = 'running'
        evaluation.started_at = datetime.utcnow()
        db.commit()

        # Get related data
        model_config = evaluation.model_config
        project = evaluation.project

        # Get images with annotations
        images = db.query(Image).join(Annotation).filter(
            Image.dataset_id == evaluation.dataset_id
        ).all()

        evaluation.total_images = len(images)
        db.commit()

        if not images:
            evaluation.status = 'failed'
            evaluation.error_message = 'No annotated images in dataset'
            db.commit()
            return

        # Get system prompt from config based on question type
        system_message = get_system_prompt(
            project.question_type,
            project.question_options if project.question_type == 'multiple_choice' else None
        )

        # Build user prompt (just the question)
        prompt = project.question_text

        correct_count = 0

        for i, image in enumerate(images):
            try:
                # Call appropriate LLM
                if model_config.provider == 'gemini':
                    response_text, latency = await call_gemini(
                        model_config.api_key, model_config.model_name,
                        image.storage_path, prompt, system_message, model_config.temperature, model_config.max_tokens
                    )
                elif model_config.provider == 'openai':
                    response_text, latency = await call_openai(
                        model_config.api_key, model_config.model_name,
                        image.storage_path, prompt, system_message, model_config.temperature, model_config.max_tokens
                    )
                elif model_config.provider == 'anthropic':
                    response_text, latency = await call_anthropic(
                        model_config.api_key, model_config.model_name,
                        image.storage_path, prompt, system_message, model_config.temperature, model_config.max_tokens
                    )
                else:
                    raise Exception(f"Unknown provider: {model_config.provider}")

                # Parse and check
                parsed = parse_answer(response_text, project.question_type)
                ground_truth = image.annotation.answer_value
                is_correct = check_answer(parsed, ground_truth, project.question_type)

                if is_correct:
                    correct_count += 1

                # Save result
                result = EvaluationResult(
                    evaluation_id=evaluation.id,
                    image_id=image.id,
                    model_response=response_text,
                    parsed_answer=parsed,
                    ground_truth=ground_truth,
                    is_correct=is_correct,
                    latency_ms=latency
                )
                db.add(result)

            except Exception as e:
                result = EvaluationResult(
                    evaluation_id=evaluation.id,
                    image_id=image.id,
                    error=str(e)
                )
                db.add(result)

            # Update progress
            evaluation.processed_images = i + 1
            evaluation.progress = int((i + 1) / len(images) * 100)
            db.commit()

        # Complete evaluation
        evaluation.status = 'completed'
        evaluation.completed_at = datetime.utcnow()
        evaluation.accuracy = correct_count / len(images) if images else 0
        evaluation.results_summary = {
            'correct': correct_count,
            'total': len(images),
            'accuracy_percent': round(evaluation.accuracy * 100, 2)
        }
        db.commit()

    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}", exc_info=True)
        evaluation.status = 'failed'
        evaluation.error_message = str(e)
        db.commit()
    finally:
        db.close()

# Endpoints
@router.get("", response_model=List[EvaluationListItem])
async def list_evaluations(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List evaluations"""
    query = db.query(Evaluation).filter(Evaluation.created_by_id == current_user.id)
    if project_id:
        query = query.filter(Evaluation.project_id == project_id)

    evaluations = query.order_by(Evaluation.created_at.desc()).all()

    return [
        EvaluationListItem(
            id=str(e.id),
            name=e.name,
            project_name=e.project.name,
            dataset_name=e.dataset.name,
            model_name=f"{e.model_config.provider}/{e.model_config.model_name}",
            status=e.status,
            progress=e.progress,
            accuracy=e.accuracy,
            created_at=e.created_at
        )
        for e in evaluations
    ]

@router.post("", response_model=EvaluationResponse)
async def create_evaluation(
    data: EvaluationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create and start a new evaluation"""
    # Verify project and dataset
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dataset = db.query(Dataset).filter(
        Dataset.id == data.dataset_id,
        Dataset.project_id == data.project_id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    model_config = db.query(ModelConfig).filter(
        ModelConfig.id == data.model_config_id,
        ModelConfig.created_by_id == current_user.id
    ).first()
    if not model_config:
        raise HTTPException(status_code=404, detail="Model config not found")

    # Create evaluation
    evaluation = Evaluation(
        name=data.name,
        project_id=data.project_id,
        dataset_id=data.dataset_id,
        model_config_id=data.model_config_id,
        created_by_id=current_user.id
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    # Start background task
    background_tasks.add_task(run_evaluation_task, str(evaluation.id))

    return EvaluationResponse(
        id=str(evaluation.id),
        name=evaluation.name,
        project_id=str(evaluation.project_id),
        dataset_id=str(evaluation.dataset_id),
        model_config_id=str(evaluation.model_config_id),
        status=evaluation.status,
        progress=evaluation.progress,
        total_images=evaluation.total_images,
        processed_images=evaluation.processed_images,
        accuracy=evaluation.accuracy,
        error_message=evaluation.error_message,
        started_at=evaluation.started_at,
        completed_at=evaluation.completed_at,
        created_at=evaluation.created_at
    )

@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get evaluation details"""
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == evaluation_id,
        Evaluation.created_by_id == current_user.id
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return EvaluationResponse(
        id=str(evaluation.id),
        name=evaluation.name,
        project_id=str(evaluation.project_id),
        dataset_id=str(evaluation.dataset_id),
        model_config_id=str(evaluation.model_config_id),
        status=evaluation.status,
        progress=evaluation.progress,
        total_images=evaluation.total_images,
        processed_images=evaluation.processed_images,
        accuracy=evaluation.accuracy,
        error_message=evaluation.error_message,
        started_at=evaluation.started_at,
        completed_at=evaluation.completed_at,
        created_at=evaluation.created_at
    )

@router.get("/{evaluation_id}/results", response_model=List[EvaluationResultItem])
async def get_evaluation_results(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get evaluation results"""
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == evaluation_id,
        Evaluation.created_by_id == current_user.id
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    results = db.query(EvaluationResult).filter(
        EvaluationResult.evaluation_id == evaluation_id
    ).all()

    return [
        EvaluationResultItem(
            id=str(r.id),
            image_id=str(r.image_id),
            image_filename=r.image.filename,
            model_response=r.model_response,
            parsed_answer=r.parsed_answer,
            ground_truth=r.ground_truth,
            is_correct=r.is_correct,
            latency_ms=r.latency_ms
        )
        for r in results
    ]

@router.delete("/{evaluation_id}")
async def delete_evaluation(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an evaluation"""
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == evaluation_id,
        Evaluation.created_by_id == current_user.id
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    db.delete(evaluation)
    db.commit()
    return {"message": "Evaluation deleted"}
