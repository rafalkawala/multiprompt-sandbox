"""
Evaluation API endpoints with LLM integrations
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
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
import asyncio
import threading

from core.database import SessionLocal
from core.prompt_config import get_system_prompt
from models.evaluation import ModelConfig, Evaluation, EvaluationResult
from models.project import Project, Dataset
from models.image import Image, Annotation
from models.user import User
from api.v1.auth import get_current_user

# Import Storage Service
from services.storage_service import get_storage_provider
# Import LLM Service
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
class EvaluationCreate(BaseModel):
    name: str
    project_id: str
    dataset_id: str
    model_config_id: str
    system_message: Optional[str] = None
    question_text: Optional[str] = None

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
    results_summary: Optional[dict] = None
    system_message: Optional[str]
    question_text: Optional[str]
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
    total_images: int
    processed_images: int
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

# Helper function to get image data from storage
async def get_image_data(storage_path: str) -> tuple:
    """Get image data and mime type from storage path (GCS or local)

    Returns: (image_data_base64, mime_type)
    """
    storage = get_storage_provider()

    # Determine mime type from path
    ext = os.path.splitext(storage_path)[1].lower()
    mime_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp'}
    mime_type = mime_types.get(ext, 'image/jpeg')

    try:
        image_bytes = await storage.download(storage_path)
        image_data = base64.standard_b64encode(image_bytes).decode('utf-8')
        return image_data, mime_type
    except Exception as e:
        logger.error(f"Failed to download image {storage_path}: {e}")
        raise

async def preload_images(images: list) -> dict:
    """Pre-load all images in parallel for faster evaluation

    Returns: dict mapping image_id -> (base64_data, mime_type)
    """
    image_cache = {}

    async def load_image(image):
        try:
            # Storage provider handles async/sync logic
            image_data, mime_type = await get_image_data(image.storage_path)
            return image.id, (image_data, mime_type)
        except Exception as e:
            logger.error(f"Failed to preload image {image.id}: {e}")
            return image.id, None

    # Load all images in parallel
    results = await asyncio.gather(*[load_image(img) for img in images])

    # Build cache dict
    for img_id, data in results:
        if data:
            image_cache[img_id] = data

    logger.info(f"Preloaded {len(image_cache)}/{len(images)} images into cache")
    return image_cache

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

        # Use saved prompts if available, otherwise fall back to project defaults
        if evaluation.system_message:
            system_message = evaluation.system_message
        else:
            # Get system prompt from config based on question type
            system_message = get_system_prompt(
                project.question_type,
                project.question_options if project.question_type == 'multiple_choice' else None
            )

        # Build user prompt (just the question)
        if evaluation.question_text:
            prompt = evaluation.question_text
        else:
            prompt = project.question_text

        # Preload all images in parallel for faster processing
        logger.info(f"Evaluation {evaluation_id}: Preloading {len(images)} images...")
        image_cache = await preload_images(images)

        if len(image_cache) == 0:
            evaluation.status = 'failed'
            evaluation.error_message = 'Failed to load any images'
            db.commit()
            return

        correct_count = 0
        failed_count = 0
        error_messages = []

        # Get concurrency limit from model config
        concurrency = getattr(model_config, 'concurrency', 3)
        semaphore = asyncio.Semaphore(concurrency)

        # Process images in parallel with concurrency limit
        async def process_image(i: int, image):
            nonlocal correct_count, failed_count, error_messages

            async with semaphore:  # Limit concurrent API calls
                try:
                    # Get cached image data
                    cached_data = image_cache.get(image.id)
                    if not cached_data:
                        raise Exception(f"Image {image.id} not found in cache")

                    image_data, mime_type = cached_data

                    # Call LLM Service
                    llm_service = get_llm_service()
                    response_text, latency = await llm_service.generate_content(
                        provider_name=model_config.provider,
                        api_key=model_config.api_key,
                        model_name=model_config.model_name,
                        image_data=image_data,
                        mime_type=mime_type,
                        prompt=prompt,
                        system_message=system_message,
                        temperature=model_config.temperature,
                        max_tokens=model_config.max_tokens
                    )

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
                    logger.info(f"Evaluation {evaluation_id}: Processed image {i+1}/{len(images)} - Correct: {is_correct}")

                except Exception as e:
                    failed_count += 1
                    error_msg = f"Image {image.filename}: {str(e)}"
                    error_messages.append(error_msg)
                    logger.error(f"Evaluation {evaluation_id}: Failed image {i+1}/{len(images)} - {error_msg}", exc_info=True)

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

        # Run all images in parallel with concurrency limit
        await asyncio.gather(*[process_image(i, img) for i, img in enumerate(images)])

        # Calculate metrics
        total_processed = len(images)
        successful_count = total_processed - failed_count
        failure_rate = (failed_count / total_processed * 100) if total_processed > 0 else 0

        # Confusion Matrix for Binary Classification
        confusion_matrix = None
        if project.question_type == 'binary':
            tp = 0
            tn = 0
            fp = 0
            fn = 0
            
            # Re-query results to calculate matrix (or accumulate during loop)
            # Since we are in the same transaction, we can query the just-added results
            results = db.query(EvaluationResult).filter(EvaluationResult.evaluation_id == evaluation.id).all()
            
            for r in results:
                if r.is_correct is None: continue
                
                # Ensure we have boolean values
                gt = r.ground_truth.get('value') if r.ground_truth else None
                pred = r.parsed_answer.get('value') if r.parsed_answer else None
                
                if gt is True and pred is True:
                    tp += 1
                elif gt is False and pred is False:
                    tn += 1
                elif gt is False and pred is True:
                    fp += 1
                elif gt is True and pred is False:
                    fn += 1
            
            confusion_matrix = {
                'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn
            }

        # Determine if evaluation should be marked as failed due to high failure rate
        FAILURE_THRESHOLD_PERCENT = 50  # If >50% of predictions fail, mark evaluation as failed

        if failure_rate > FAILURE_THRESHOLD_PERCENT:
            evaluation.status = 'failed'
            evaluation.error_message = f"Evaluation failed: {failure_rate:.1f}% of predictions failed ({failed_count}/{total_processed}). Errors: {'; '.join(error_messages[:3])}"
            if len(error_messages) > 3:
                evaluation.error_message += f" (and {len(error_messages) - 3} more errors)"
            logger.error(f"Evaluation {evaluation_id} marked as failed due to high failure rate: {failure_rate:.1f}%")
        else:
            evaluation.status = 'completed'
            if failed_count > 0:
                logger.warning(f"Evaluation {evaluation_id} completed with {failed_count} failures ({failure_rate:.1f}%)")

        evaluation.completed_at = datetime.utcnow()
        evaluation.accuracy = correct_count / successful_count if successful_count > 0 else 0
        evaluation.results_summary = {
            'correct': correct_count,
            'total': total_processed,
            'successful': successful_count,
            'failed': failed_count,
            'failure_rate_percent': round(failure_rate, 2),
            'accuracy_percent': round(evaluation.accuracy * 100, 2),
            'confusion_matrix': confusion_matrix
        }
        db.commit()

        logger.info(f"Evaluation {evaluation_id} finished: status={evaluation.status}, accuracy={evaluation.accuracy:.2%}, failed={failed_count}/{total_processed}")

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
            total_images=e.total_images,
            processed_images=e.processed_images,
            accuracy=e.accuracy,
            created_at=e.created_at
        )
        for e in evaluations
    ]

def run_evaluation_in_thread(evaluation_id: str):
    """Wrapper to run async evaluation task in a thread with its own event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_evaluation_task(evaluation_id))
    finally:
        loop.close()

@router.post("", response_model=EvaluationResponse)
async def create_evaluation(
    data: EvaluationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create and start a new evaluation (runs in background thread)"""
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
        system_message=data.system_message,
        question_text=data.question_text,
        created_by_id=current_user.id
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    # Start evaluation in a background thread (survives even if user closes page)
    thread = threading.Thread(
        target=run_evaluation_in_thread,
        args=(str(evaluation.id),),
        daemon=True  # Daemon thread won't prevent app shutdown
    )
    thread.start()
    logger.info(f"Started evaluation {evaluation.id} in background thread")

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
        results_summary=evaluation.results_summary,
        system_message=evaluation.system_message,
        question_text=evaluation.question_text,
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
        results_summary=evaluation.results_summary,
        system_message=evaluation.system_message,
        question_text=evaluation.question_text,
        started_at=evaluation.started_at,
        completed_at=evaluation.completed_at,
        created_at=evaluation.created_at
    )

@router.get("/{evaluation_id}/results", response_model=List[EvaluationResultItem])
async def get_evaluation_results(
    evaluation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    filter: str = Query('all', regex="^(all|correct|incorrect|tp|tn|fp|fn)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get evaluation results with filtering"""
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == evaluation_id,
        Evaluation.created_by_id == current_user.id
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    query = db.query(EvaluationResult).filter(
        EvaluationResult.evaluation_id == evaluation_id
    )

    # Apply filters
    if filter == 'correct':
        query = query.filter(EvaluationResult.is_correct == True)
    elif filter == 'incorrect':
        query = query.filter(EvaluationResult.is_correct == False)
    elif filter in ['tp', 'tn', 'fp', 'fn']:
        # Advanced filters for binary classification (requires casting JSON)
        # This relies on Postgres/SQLite JSON operators. 
        # We assume 'value' key exists and is boolean.
        from sqlalchemy import cast, String
        
        # We'll filter in Python for simplicity and safety across generic SQL setups 
        # unless we strictly enforce Postgres JSONB.
        # Given pagination, Python filtering of the WHOLE set is bad. 
        # BUT we can try to filter at DB level using text casting which is safer.
        
        # Note: In JSON, True is 'true', False is 'false'
        
        if filter == 'tp':
            # True Positive: Correct + Prediction is True
            query = query.filter(
                EvaluationResult.is_correct == True,
                cast(EvaluationResult.parsed_answer['value'], String) == 'true'
            )
        elif filter == 'tn':
            # True Negative: Correct + Prediction is False
            query = query.filter(
                EvaluationResult.is_correct == True,
                cast(EvaluationResult.parsed_answer['value'], String) == 'false'
            )
        elif filter == 'fp':
            # False Positive: Incorrect + Prediction is True (Actual was False)
            query = query.filter(
                EvaluationResult.is_correct == False,
                cast(EvaluationResult.parsed_answer['value'], String) == 'true'
            )
        elif filter == 'fn':
            # False Negative: Incorrect + Prediction is False (Actual was True)
            query = query.filter(
                EvaluationResult.is_correct == False,
                cast(EvaluationResult.parsed_answer['value'], String) == 'false'
            )

    results = query.offset(skip).limit(limit).all()

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