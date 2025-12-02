from sqlalchemy import Column, String, Text, ForeignKey, DateTime, JSON, Boolean, Integer, Float, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from core.database import Base

class LabellingJob(Base):
    __tablename__ = "labelling_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)
    gcs_folder_path = Column(String(512), nullable=False)
    last_processed_timestamp = Column(DateTime, nullable=True)

    # Prompt configuration (snapshot from evaluation)
    model_config_id = Column(UUID(as_uuid=True), ForeignKey("model_configs.id"), nullable=False)
    system_message = Column(Text, nullable=False)
    question_text = Column(Text, nullable=False)

    # Scheduling
    frequency_minutes = Column(Integer, default=15, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Status
    status = Column(String(50), default='idle', nullable=False)  # idle, running, error
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    # Statistics
    total_runs = Column(Integer, default=0, nullable=False)
    total_images_processed = Column(Integer, default=0, nullable=False)
    total_images_labeled = Column(Integer, default=0, nullable=False)
    total_errors = Column(Integer, default=0, nullable=False)

    # Metadata
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project")
    dataset = relationship("Dataset")
    model_config = relationship("ModelConfig")
    created_by = relationship("User")
    runs = relationship("LabellingJobRun", back_populates="job", cascade="all, delete-orphan")
    results = relationship("LabellingResult", back_populates="job", cascade="all, delete-orphan")


class LabellingJobRun(Base):
    __tablename__ = "labelling_job_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    labelling_job_id = Column(UUID(as_uuid=True), ForeignKey("labelling_jobs.id", ondelete="CASCADE"), nullable=False)

    status = Column(String(50), default='running', nullable=False)  # running, completed, failed
    trigger_type = Column(String(50), nullable=False)  # manual, scheduled

    # Statistics
    images_discovered = Column(Integer, default=0, nullable=False)
    images_ingested = Column(Integer, default=0, nullable=False)
    images_labeled = Column(Integer, default=0, nullable=False)
    images_failed = Column(Integer, default=0, nullable=False)

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job = relationship("LabellingJob", back_populates="runs")
    results = relationship("LabellingResult", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_labelling_job_runs_job', 'labelling_job_id'),
    )


class LabellingResult(Base):
    __tablename__ = "labelling_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    labelling_job_id = Column(UUID(as_uuid=True), ForeignKey("labelling_jobs.id", ondelete="CASCADE"), nullable=False)
    labelling_job_run_id = Column(UUID(as_uuid=True), ForeignKey("labelling_job_runs.id", ondelete="CASCADE"), nullable=False)
    image_id = Column(UUID(as_uuid=True), ForeignKey("images.id", ondelete="CASCADE"), nullable=False)

    # LLM Response
    model_response = Column(Text, nullable=False)
    parsed_answer = Column(JSON, nullable=False)
    confidence_score = Column(Float, nullable=True)

    # Metrics
    latency_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)

    # Source tracking
    gcs_source_path = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job = relationship("LabellingJob", back_populates="results")
    run = relationship("LabellingJobRun", back_populates="results")
    image = relationship("Image")

    __table_args__ = (
        UniqueConstraint('labelling_job_id', 'image_id', name='unique_job_image'),
        Index('idx_labelling_results_job', 'labelling_job_id'),
        Index('idx_labelling_results_image', 'image_id'),
    )
