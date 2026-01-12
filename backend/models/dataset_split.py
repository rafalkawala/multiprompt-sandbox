from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from core.database import Base

class DatasetSplit(Base):
    __tablename__ = "dataset_splits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)

    # The core data: which images are in this split
    image_ids = Column(JSON, nullable=False)  # List[UUID] as strings

    # Metadata about how it was created
    split_type = Column(String, nullable=False) # 'random_percent', 'random_count', 'manual', 'stratified'
    split_value = Column(Integer, nullable=True) # e.g. 5 (percent) or 100 (count)

    # To track lineage (e.g., "Round 2" excluding "Round 1")
    excluded_split_ids = Column(JSON, nullable=True) # List[UUID] of splits excluded during creation

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset")
    created_by = relationship("User")
