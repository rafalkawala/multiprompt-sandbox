from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime, timezone
from core.database import Base

class ImportJobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class AnnotationImportJob(Base):
    __tablename__ = "annotation_import_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(Enum(ImportJobStatus), default=ImportJobStatus.PENDING, nullable=False)
    
    # File handling
    temp_file_path = Column(String, nullable=True)
    
    # Progress tracking
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    
    # Stats
    created_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    # Detailed logs
    errors = Column(JSON, default=list)  # [{row: 1, error: "..."}]
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    dataset = relationship("Dataset")
    created_by = relationship("User")

    def to_dict(self):
        return {
            "id": str(self.id),
            "status": self.status,
            "total_rows": self.total_rows,
            "processed_rows": self.processed_rows,
            "created_count": self.created_count,
            "updated_count": self.updated_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "errors": self.errors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
