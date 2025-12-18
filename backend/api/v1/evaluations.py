"""
Evaluation API endpoints with LLM integrations
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import httpx
import base64
import os
import structlog
import json
import time
import asyncio
import threading
import math
from sqlalchemy.sql.expression import func

from core.database import SessionLocal
from core.prompt_config import get_system_prompt
from core.prompt_utils import substitute_variables, validate_variable_references
from models.evaluation import ModelConfig, Evaluation, EvaluationResult
from models.project import Project, Dataset
from models.image import Image, Annotation
from models.user import User
from api.deps import get_db, get_current_user
# from services.evaluation_service import EvaluationService

# Import Storage Service
from services.storage_service import get_storage_provider
# Import LLM Service
from services.llm_service import get_llm_service
# Import Cost Estimation Service
from services.cost_estimation_service import get_cost_service
# Import HttpClient for cleanup
from core.http_client import HttpClient
# Import Helper
from api.v1.evaluations_helper import ImageEvalData

logger = structlog.get_logger(__name__)
router = APIRouter()

# Schemas
class EvaluationCreate(BaseModel):
    name: str
    project_id: str
    dataset_id: str
    model_config_id: str

    # Legacy single-prompt (optional, for backward compatibility)
    system_message: Optional[str] = None
    question_text: Optional[str] = None

    # New multi-phase prompting (optional)
    # Structure: [{"step_number": 1, "system_message": "...", "prompt": "..."}, ...]
    prompt_chain: Optional[List[Dict[str, Any]]] = None

    # Dataset selection configuration (subselection)
    # Structure: {"mode": "all"|"random"|"manual", "limit": 100, "image_ids": [...]}
    selection_config: Optional[Dict[str, Any]] = None

    @field_validator('prompt_chain')
    @classmethod
    def validate_chain(cls, v):
        """Validate prompt chain structure and constraints"""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError('prompt_chain must be a list')

            if len(v) < 1 or len(v) > 5:
                raise ValueError('Prompt chain must have 1-5 steps')

            for i, step in enumerate(v):
                if not isinstance(step, dict):
                    raise ValueError(f'Step {i+1} must be a dictionary')

                # Validate required fields
                if 'step_number' not in step:
                    raise ValueError(f'Step {i+1} missing required field: step_number')
                if 'prompt' not in step:
                    raise ValueError(f'Step {i+1} missing required field: prompt')

                # Validate step_number is correct
                expected_step = i + 1
                if step['step_number'] != expected_step:
                    raise ValueError(f'Step {i+1} has incorrect step_number: expected {expected_step}, got {step["step_number"]}')

        return v

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
    prompt_chain: Optional[List[Dict[str, Any]]] = None  # Multi-phase prompting
    selection_config: Optional[Dict[str, Any]] = None
    estimated_cost: Optional[float] = None  # Cost estimation before execution
    actual_cost: Optional[float] = None  # Actual cost after execution
    cost_details: Optional[Dict[str, Any]] = None  # Detailed cost breakdown
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

async def preload_images(images: List[ImageEvalData]) -> dict:
    """Pre-load all images in parallel for faster evaluation

    Returns: dict mapping image_id -> (base64_data, mime_type)
    """
    image_cache = {}

    async def load_image(image: ImageEvalData):
        try:
            # Storage provider handles async/sync logic
            image_data, mime_type = await get_image_data(image.storage_path)
            return image.id, (image_data, mime_type)
        except Exception as e:
            logger.error(f"Failed to preload image {image.id} (dataset: {image.dataset_id}, filename: {image.filename}, storage_path: {image.storage_path}): {e}")
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
        # Detach config data from session to use safely in async
        # Ensure pricing_config is populated (handle potential None)
        pricing_config = evaluation.model_config.pricing_config or {}

        model_config_data = {
            'provider': evaluation.model_config.provider,
            'api_key': evaluation.model_config.api_key,
            'auth_type': evaluation.model_config.auth_type,
            'model_name': evaluation.model_config.model_name,
            'temperature': evaluation.model_config.temperature,
            'max_tokens': evaluation.model_config.max_tokens,
            'pricing_config': pricing_config,
            'concurrency': getattr(evaluation.model_config, 'concurrency', 3)
        }

        project_data = {
            'question_type': evaluation.project.question_type,
            'question_options': evaluation.project.question_options,
            'question_text': evaluation.project.question_text
        }

        # Get images with annotations (Apply Selection Config)
        # Exclude failed images, but include pending/completed (for backwards compatibility)
        query = db.query(Image).join(Annotation).filter(
            Image.dataset_id == evaluation.dataset_id,
            Image.processing_status != 'failed'
        )

        # Apply subselection logic
        if evaluation.selection_config:
            mode = evaluation.selection_config.get('mode', 'all')
            
            if mode == 'random_count':
                limit = evaluation.selection_config.get('count', 0)
                if limit > 0:
                    query = query.order_by(func.random()).limit(limit)
                    
            elif mode == 'random_percent':
                percent = evaluation.selection_config.get('percent', 0)
                if percent > 0:
                    # Count images with annotations (same criteria as main query)
                    # Exclude failed images but include pending/completed
                    total_count = db.query(Image).join(Annotation).filter(
                        Image.dataset_id == evaluation.dataset_id,
                        Image.processing_status != 'failed'
                    ).count()
                    limit = math.ceil((total_count * percent) / 100)
                    query = query.order_by(func.random()).limit(limit)
                    
            elif mode == 'manual':
                image_ids = evaluation.selection_config.get('image_ids', [])
                if image_ids:
                    # Verify these image IDs belong to the correct dataset (defensive check)
                    query = query.filter(Image.id.in_(image_ids))
                    logger.info(f"Evaluation {evaluation_id}: Manual selection mode with {len(image_ids)} image IDs")
        
        image_objects = query.all()

        evaluation.total_images = len(image_objects)
        db.commit()

        if not image_objects:
            evaluation.status = 'failed'
            evaluation.error_message = 'No annotated images in dataset (or selection criteria matched none)'
            db.commit()
            return

        # Convert SQLA objects to safe Data Class
        images: List[ImageEvalData] = []
        for img in image_objects:
            images.append(ImageEvalData(
                id=str(img.id),
                dataset_id=str(img.dataset_id),
                filename=img.filename,
                storage_path=img.storage_path,
                ground_truth=img.annotation.answer_value
            ))

        # Log selected images for debugging
        logger.info(f"Evaluation {evaluation_id}: Selected {len(images)} images from dataset {evaluation.dataset_id}")
        logger.debug(f"Evaluation {evaluation_id}: Image IDs: {[img.id for img in images[:10]]}")  # Log first 10 IDs

        # Load prompt chain (multi-phase) or fallback to legacy single prompt
        if evaluation.prompt_chain and len(evaluation.prompt_chain) > 0:
            # Multi-phase prompting: use prompt_chain
            steps = evaluation.prompt_chain
            logger.info(f"Evaluation {evaluation_id}: Using multi-phase prompting with {len(steps)} steps")
        else:
            # Legacy single-prompt: convert to single-step chain
            if evaluation.system_message:
                system_message = evaluation.system_message
            else:
                # Get system prompt from config based on question type
                system_message = get_system_prompt(
                    project_data['question_type'],
                    project_data['question_options'] if project_data['question_type'] == 'multiple_choice' else None
                )

            # Build user prompt (just the question)
            if evaluation.question_text:
                prompt = evaluation.question_text
            else:
                prompt = project_data['question_text']

            # Create single-step chain for backward compatibility
            steps = [{
                "step_number": 1,
                "system_message": system_message,
                "prompt": prompt
            }]
            logger.info(f"Evaluation {evaluation_id}: Using legacy single-prompt mode")

        # Close the main session before starting async tasks to avoid thread-safety issues
        db.close()

        # Preload all images in parallel for faster processing
        logger.info(f"Evaluation {evaluation_id}: Preloading {len(images)} images...")
        image_cache = await preload_images(images)

        if len(image_cache) == 0:
            # Need a new session to update status
            db = SessionLocal()
            try:
                eval_obj = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
                if eval_obj:
                    eval_obj.status = 'failed'
                    eval_obj.error_message = 'Failed to load any images'
                    db.commit()
            finally:
                db.close()
            return

        correct_count = 0
        failed_count = 0
        error_messages = []
        total_actual_cost = 0.0

        # Get concurrency limit from model config
        concurrency = model_config_data.get('concurrency', 3)
        semaphore = asyncio.Semaphore(concurrency)

        # Track completed images (not index-based, to avoid race conditions in parallel processing)
        completed_count = 0
        
        # Progress tracking variables
        task_start_time = time.time()
        
        # Process images in parallel with concurrency limit
        async def process_image(i: int, image: ImageEvalData):
            nonlocal correct_count, failed_count, error_messages, completed_count, total_actual_cost

            async with semaphore:  # Limit concurrent API calls
                # Use a dedicated session for this task to ensure thread safety
                task_db = SessionLocal()
                try:
                    # Get cached image data
                    cached_data = image_cache.get(image.id)
                    if not cached_data:
                        raise Exception(f"Image {image.id} not found in cache")

                    image_data, mime_type = cached_data

                    # Execute steps sequentially for this image
                    step_results = []
                    outputs = {}  # {step_number: output_text}
                    total_latency = 0
                    total_row_prompt_tokens = 0
                    total_row_completion_tokens = 0
                    total_row_cost = 0.0

                    for step in steps:
                        step_num = step['step_number']
                        system_message = step.get('system_message')
                        prompt_template = step['prompt']

                        # Substitute variables from previous steps
                        prompt = substitute_variables(prompt_template, outputs)

                        # Initialize default values in case of error
                        response_text = ""
                        usage_metadata = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
                        latency = 0

                        # Call LLM Service
                        start_time = time.time()
                        llm_service = get_llm_service()

                        response_text, token_count, usage_metadata = await llm_service.generate_content(
                            provider_name=model_config_data['provider'],
                            api_key=model_config_data['api_key'],
                            auth_type=model_config_data['auth_type'],
                            model_name=model_config_data['model_name'],
                            prompt=prompt,
                            image_data=image_data,
                            mime_type=mime_type,
                            system_message=system_message,
                            temperature=model_config_data['temperature'],
                            max_tokens=model_config_data['max_tokens']
                        )

                        latency = int((time.time() - start_time) * 1000)
                        total_latency += latency

                        # Store output for subsequent steps
                        outputs[step_num] = response_text

                        # Calculate cost for this step
                        step_cost = 0.0
                        step_cost_details = {}
                        if model_config_data['pricing_config']:
                            # Calculate actual cost including image cost handling
                            # Use high precision (no rounding here if possible, but service might round)
                            # We trust the service to return float.
                            step_cost = get_cost_service().calculate_actual_cost(
                                usage_metadata,
                                model_config_data['pricing_config'],
                                has_image=bool(image_data),
                                provider=model_config_data['provider']
                            )

                            step_cost_details = {
                                'step_cost': step_cost
                            }

                            total_actual_cost += step_cost

                            # Accumulate row totals
                            total_row_cost += step_cost
                            total_row_prompt_tokens += usage_metadata.get('prompt_tokens', 0)
                            total_row_completion_tokens += usage_metadata.get('completion_tokens', 0)

                        # Record step result
                        step_results.append({
                            "step_number": step_num,
                            "raw_output": response_text,
                            "latency_ms": latency,
                            "usage": usage_metadata,
                            "cost": step_cost_details,
                            "error": None
                        })

                        logger.debug(f"Evaluation {evaluation_id}: Image {i+1} Step {step_num} completed - Output: {response_text[:50]}...")

                    # Use final step's output for accuracy calculation
                    final_step_num = steps[-1]["step_number"]
                    final_output = outputs[final_step_num]

                    # Parse and check
                    parsed = parse_answer(final_output, project_data['question_type'])
                    ground_truth = image.ground_truth
                    is_correct = check_answer(parsed, ground_truth, project_data['question_type'])

                    if is_correct:
                        correct_count += 1

                    # Save result with step_results
                    result = EvaluationResult(
                        evaluation_id=evaluation_id,
                        image_id=image.id,
                        model_response=final_output,
                        parsed_answer=parsed,
                        ground_truth=ground_truth,
                        is_correct=is_correct,
                        step_results=step_results,
                        latency_ms=total_latency,
                        prompt_tokens=total_row_prompt_tokens,
                        completion_tokens=total_row_completion_tokens,
                        cost=total_row_cost,
                        token_count=total_row_prompt_tokens + total_row_completion_tokens
                    )
                    task_db.add(result)
                    logger.info(f"Evaluation {evaluation_id}: Processed image {i+1}/{len(images)} ({len(steps)} steps) - Correct: {is_correct}")

                except Exception as e:
                    failed_count += 1
                    error_msg = f"Image {image.filename}: {str(e)}"
                    error_messages.append(error_msg)
                    logger.error(f"Evaluation {evaluation_id}: Failed image {i+1}/{len(images)} - {error_msg}", exc_info=True)

                    result = EvaluationResult(
                        evaluation_id=evaluation_id, # Use ID string
                        image_id=image.id,           # Use ID string
                        error=str(e),
                        step_results=step_results if 'step_results' in locals() and step_results else None
                    )
                    task_db.add(result)

                # Update progress atomically (increment count, not use index)
                # We need to re-fetch evaluation object in this session
                current_eval = task_db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
                if current_eval:
                    completed_count += 1
                    current_eval.processed_images = completed_count
                    current_eval.progress = int((completed_count / len(images)) * 100)
                    
                    # Calculate ETA
                    # Update only after first batch completes and at start of new batches
                    if completed_count >= concurrency and completed_count % concurrency == 0:
                        now = time.time()
                        elapsed_total = now - task_start_time
                        avg_time_per_image = elapsed_total / completed_count
                        remaining_images = len(images) - completed_count

                        # Formula: (avg_time * remaining) / concurrency + single_photo_time
                        # single_photo_time is approximated as avg_time_per_image
                        eta_seconds = (avg_time_per_image * remaining_images) / concurrency + avg_time_per_image

                        if not current_eval.results_summary:
                            current_eval.results_summary = {}
                        # Make a copy to update JSON field (SQLAlchemy requirement for JSON updates)
                        summary = dict(current_eval.results_summary) if current_eval.results_summary else {}
                        summary['eta_seconds'] = round(eta_seconds, 1)
                        current_eval.results_summary = summary

                    task_db.commit()
                else:
                     logger.error(f"Could not find evaluation {evaluation_id} to update progress")

                task_db.close()

        # Run all images in parallel with concurrency limit
        await asyncio.gather(*[process_image(i, img) for i, img in enumerate(images)])

        # Final metrics and status update
        # New session for final update
        db = SessionLocal()
        try:
            evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
            if not evaluation:
                 logger.error(f"Evaluation {evaluation_id} disappeared during processing")
                 return
            
            # Calculate metrics
            total_processed = len(images)
            successful_count = total_processed - failed_count
            failure_rate = (failed_count / total_processed * 100) if total_processed > 0 else 0

            # Confusion Matrix for Binary Classification
            confusion_matrix = None
            if project_data['question_type'] == 'binary':
                tp = 0
                tn = 0
                fp = 0
                fn = 0
                
                # Re-query results to calculate matrix
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
            evaluation.actual_cost = round(total_actual_cost, 4)

            # Calculate cost details breakdown
            total_prompt_tokens = 0
            total_completion_tokens = 0

            # Aggregate token counts from all results
            results = db.query(EvaluationResult).filter(EvaluationResult.evaluation_id == evaluation.id).all()
            for r in results:
                if r.step_results:
                    for step in r.step_results:
                        usage = step.get('usage', {})
                        total_prompt_tokens += usage.get('prompt_tokens', 0)
                        total_completion_tokens += usage.get('completion_tokens', 0)

            evaluation.cost_details = {
                'total_prompt_tokens': total_prompt_tokens,
                'total_completion_tokens': total_completion_tokens,
                'total_tokens': total_prompt_tokens + total_completion_tokens,
                'total_cost': evaluation.actual_cost,
                'average_cost_per_image': round(evaluation.actual_cost / total_processed, 6) if total_processed > 0 else 0
            }

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
            db.rollback()  # Rollback any pending transaction
            # Try to save error to DB
            try:
                evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
                if evaluation:
                    evaluation.status = 'failed'
                    evaluation.error_message = str(e)
                    db.commit()
            except:
                pass
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Evaluation setup error: {str(e)}", exc_info=True)
        try:
             # Ensure cleanup if possible
             if 'db' in locals():
                 db.close()
             # Recovery session
             db = SessionLocal()
             evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
             if evaluation:
                evaluation.status = 'failed'
                evaluation.error_message = f"Setup error: {str(e)}"
                db.commit()
             db.close()
        except:
            pass

# Endpoints
@router.get("", response_model=List[EvaluationListItem])
async def list_evaluations(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List evaluations"""
    service = EvaluationService(db)
    evaluations = service.list_evaluations(project_id, current_user)

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

@router.post("", response_model=EvaluationResponse)
async def create_evaluation(
    data: EvaluationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create and start a new evaluation (runs in background thread)"""
    service = EvaluationService(db)
    evaluation = service.create_evaluation(data, current_user)

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
        created_at=evaluation.created_at,
        prompt_chain=evaluation.prompt_chain,
        selection_config=evaluation.selection_config,
        estimated_cost=evaluation.estimated_cost,
        actual_cost=evaluation.actual_cost,
        cost_details=evaluation.cost_details
    )

@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get evaluation details"""
    service = EvaluationService(db)
    evaluation = service.get_evaluation(evaluation_id, current_user)

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
        created_at=evaluation.created_at,
        prompt_chain=evaluation.prompt_chain,
        selection_config=evaluation.selection_config,
        estimated_cost=evaluation.estimated_cost,
        actual_cost=evaluation.actual_cost,
        cost_details=evaluation.cost_details
    )

@router.get("/{evaluation_id}/estimate-cost")
async def estimate_evaluation_cost(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Estimate the cost of running an evaluation"""
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == evaluation_id,
        Evaluation.created_by_id == current_user.id
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    # Get model config with pricing
    model_config = db.query(ModelConfig).filter(ModelConfig.id == evaluation.model_config_id).first()
    if not model_config:
        raise HTTPException(status_code=404, detail="Model config not found")

    # Get pricing configuration
    pricing_config = model_config.pricing_config or {}
    if not pricing_config:
        return {
            "estimated_cost": 0,
            "image_count": 0,
            "avg_cost_per_image": 0,
            "details": {"error": "No pricing configuration available for this model"}
        }

    # Determine image count based on selection_config
    if evaluation.selection_config:
        selection_mode = evaluation.selection_config.get('mode', 'all')
        if selection_mode == 'manual' and 'image_ids' in evaluation.selection_config:
            image_count = len(evaluation.selection_config['image_ids'])
        elif selection_mode == 'random' and 'limit' in evaluation.selection_config:
            total_images = db.query(Image).filter(Image.dataset_id == evaluation.dataset_id).count()
            image_count = min(evaluation.selection_config['limit'], total_images)
        else:
            image_count = db.query(Image).filter(Image.dataset_id == evaluation.dataset_id).count()
    else:
        image_count = db.query(Image).filter(Image.dataset_id == evaluation.dataset_id).count()

    # Calculate cost per image
    input_price_per_1m = pricing_config.get('input_price_per_1m', 0)
    output_price_per_1m = pricing_config.get('output_price_per_1m', 0)
    image_price_val = pricing_config.get('image_price_val', 0)
    discount_percent = pricing_config.get('discount_percent', 0)

    # Estimate token usage (rough estimates)
    # System message + question text + image tokens
    estimated_input_tokens = 1000  # Base prompt
    estimated_output_tokens = 200   # Expected response

    # Calculate text cost
    text_cost_per_image = (
        (estimated_input_tokens * input_price_per_1m / 1_000_000) +
        (estimated_output_tokens * output_price_per_1m / 1_000_000)
    )

    # Calculate image cost
    image_cost = image_price_val / 1_000_000  # Convert to per-image cost

    # Total per image
    cost_per_image = text_cost_per_image + image_cost

    # Apply discount
    if discount_percent > 0:
        cost_per_image *= (1 - discount_percent / 100)

    # Total cost
    total_cost = cost_per_image * image_count

    return {
        "estimated_cost": round(total_cost, 6),
        "image_count": image_count,
        "avg_cost_per_image": round(cost_per_image, 6),
        "details": {
            "input_price_per_1m": input_price_per_1m,
            "output_price_per_1m": output_price_per_1m,
            "image_price_val": image_price_val,
            "discount_percent": discount_percent,
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_output_tokens": estimated_output_tokens
        }
    }

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
    service = EvaluationService(db)
    message = service.delete_evaluation(evaluation_id, current_user)
    return {"message": message}
