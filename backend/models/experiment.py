from sqlalchemy import Column, String, Text, ForeignKey, DateTime, JSON, Boolean, Integer, Float, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, BYTEA
import uuid
from datetime import datetime
from core.database import Base

class ModelRegistry(Base):
    __tablename__ = "model_registry"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)
    model_name = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    api_endpoint = Column(String, nullable=True)
    default_config = Column(JSON, nullable=True)
    rate_limit_rpm = Column(Integer, nullable=True)
    cost_per_1k_tokens = Column(DECIMAL, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ProjectModel(Base):
    __tablename__ = "project_models"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    model_registry_id = Column(UUID(as_uuid=True), ForeignKey("model_registry.id"), nullable=False)
    api_key_encrypted = Column(BYTEA, nullable=False)
    custom_config = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    model_registry = relationship("ModelRegistry")
    created_by = relationship("User")

class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    project_model_id = Column(UUID(as_uuid=True), ForeignKey("project_models.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    project_model = relationship("ProjectModel")
    created_by = relationship("User")
    runs = relationship("ExperimentRun", back_populates="experiment", cascade="all, delete-orphan")

class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("experiments.id"), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    status = Column(String, default="pending") # pending, running, completed, failed
    total_images = Column(Integer, default=0)
    processed_images = Column(Integer, default=0)
    successful_predictions = Column(Integer, default=0)
    failed_predictions = Column(Integer, default=0)
    accuracy_score = Column(Float, nullable=True)
    estimated_cost = Column(DECIMAL, nullable=True)
    actual_cost = Column(DECIMAL, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    experiment = relationship("Experiment", back_populates="runs")
    dataset = relationship("Dataset")
    predictions = relationship("Prediction", back_populates="run", cascade="all, delete-orphan")

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_run_id = Column(UUID(as_uuid=True), ForeignKey("experiment_runs.id"), nullable=False)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id"), nullable=False)
    predicted_value = Column(JSON)
    ground_truth_value = Column(JSON)
    is_correct = Column(Boolean)
    confidence = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("ExperimentRun", back_populates="predictions")
    image = relationship("Image")
