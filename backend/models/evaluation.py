from sqlalchemy import Column, String, Text, ForeignKey, DateTime, JSON, Boolean, Integer, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from core.database import Base

class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    provider = Column(String, nullable=False)  # 'gemini', 'openai', 'anthropic'
    model_name = Column(String, nullable=False)  # e.g., 'gemini-1.5-pro', 'gpt-4o', 'claude-3-sonnet'
    api_key = Column(String, nullable=False)  # encrypted in production
    auth_type = Column(String, default="api_key", nullable=False)  # 'api_key', 'service_account', 'google_adc'

    temperature = Column(Float, default=0.0)
    max_tokens = Column(Integer, default=1024)
    concurrency = Column(Integer, default=3)  # Number of parallel API calls
    additional_params = Column(JSON, nullable=True)

    # Pricing configuration
    # Structure: {"input_price_per_1m": 2.50, "output_price_per_1m": 10.00,
    #             "image_price_mode": "per_tile", "image_price_val": 2.50, "discount_percent": 0}
    pricing_config = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = relationship("User")
    evaluations = relationship("Evaluation", back_populates="model_config")

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    model_config_id = Column(UUID(as_uuid=True), ForeignKey("model_configs.id"), nullable=False)

    status = Column(String, default='pending')  # 'pending', 'running', 'completed', 'failed'
    progress = Column(Integer, default=0)  # percentage 0-100
    total_images = Column(Integer, default=0)
    processed_images = Column(Integer, default=0)

    # Results summary
    accuracy = Column(Float, nullable=True)
    results_summary = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Cost tracking
    estimated_cost = Column(Float, nullable=True)  # Cost estimation before execution
    actual_cost = Column(Float, nullable=True)  # Actual cost after execution
    cost_details = Column(JSON, nullable=True)  # Detailed cost breakdown

    # Evaluation prompts (saved at creation time, editable before starting)
    system_message = Column(Text, nullable=True)
    question_text = Column(Text, nullable=True)

    # Multi-phase prompting support (new)
    # Structure: [{"step_number": 1, "system_message": "...", "prompt": "..."}, ...]
    prompt_chain = Column(JSON, nullable=True)

    # Dataset selection configuration (subselection)
    # Structure: {"mode": "all"|"random"|"manual", "limit": 100, "image_ids": [...]}
    selection_config = Column(JSON, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    dataset = relationship("Dataset")
    model_config = relationship("ModelConfig", back_populates="evaluations")
    created_by = relationship("User")
    results = relationship("EvaluationResult", back_populates="evaluation", cascade="all, delete-orphan")

class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id = Column(UUID(as_uuid=True), ForeignKey("evaluations.id"), nullable=False)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id"), nullable=False)

    model_response = Column(Text, nullable=True)
    parsed_answer = Column(JSON, nullable=True)
    ground_truth = Column(JSON, nullable=True)
    is_correct = Column(Boolean, nullable=True)

    # Multi-phase prompting: intermediate results for each step
    # Structure: [{"step_number": 1, "raw_output": "...", "latency_ms": 234, "error": null}, ...]
    step_results = Column(JSON, nullable=True)

    latency_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    evaluation = relationship("Evaluation", back_populates="results")
    image = relationship("Image")
