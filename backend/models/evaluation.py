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

    temperature = Column(Float, default=0.0)
    max_tokens = Column(Integer, default=1024)
    additional_params = Column(JSON, nullable=True)

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

    latency_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    evaluation = relationship("Evaluation", back_populates="results")
    image = relationship("Image")
