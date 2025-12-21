from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

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
    results_summary: Optional[Dict[str, Any]] = None

class EvaluationResultItem(BaseModel):
    id: str
    image_id: str
    image_filename: str
    model_response: Optional[str]
    parsed_answer: Optional[dict]
    ground_truth: Optional[dict]
    is_correct: Optional[bool]
    latency_ms: Optional[int]
