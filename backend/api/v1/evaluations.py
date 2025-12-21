"""
Evaluation API endpoints with LLM integrations
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
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
from models.evaluation import ModelConfig, Evaluation, EvaluationResult
from models.project import Project, Dataset
from models.image import Image
from models.user import User
from api.v1.auth import get_current_user

# Import Services
from services.evaluation_service import EvaluationService, run_evaluation_in_thread

logger = structlog.get_logger(__name__)
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from schemas.evaluation import (
    EvaluationCreate,
    EvaluationResponse,
    EvaluationListItem,
    EvaluationResultItem
)


# Endpoints
@router.get("", response_model=List[EvaluationListItem])
async def list_evaluations(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List evaluations"""
    query = db.query(Evaluation)
    if project_id:
        query = query.filter(Evaluation.project_id == project_id)

    evaluations = query.order_by(Evaluation.created_at.desc()).all()

    def get_lite_summary(e):
        """Return only necessary progress fields for list view to reduce payload size"""
        if not e.results_summary:
            return None

        # If running, we want logs and ETA
        if e.status == 'running':
            return {
                'latest_images': e.results_summary.get('latest_images'),
                'eta_seconds': e.results_summary.get('eta_seconds')
            }

        # If completed, we might want minimal stats if needed by UI, but UI calculates accuracy separately
        # For now, return None or minimal to save bandwidth, as detailed results are fetched in detail view
        return None

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
            created_at=e.created_at,
            results_summary=get_lite_summary(e)
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
        ModelConfig.id == data.model_config_id
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
        prompt_chain=data.prompt_chain,  # Multi-phase prompting
        selection_config=data.selection_config,
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
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == evaluation_id
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
        Evaluation.id == evaluation_id
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
        Evaluation.id == evaluation_id
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
        Evaluation.id == evaluation_id
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    db.delete(evaluation)
    db.commit()
    return {"message": "Evaluation deleted"}
