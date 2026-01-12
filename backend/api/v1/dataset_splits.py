from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from api.deps import get_current_user
from schemas.dataset_split import DatasetSplitCreate, DatasetSplitResponse
from services.dataset_split_service import DatasetSplitService
from models.dataset_split import DatasetSplit

router = APIRouter()

@router.post("/{dataset_id}/splits", response_model=DatasetSplitResponse)
def create_dataset_split(
    dataset_id: UUID,
    split_in: DatasetSplitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new split for a dataset (e.g., Random 5%).
    Can optionally exclude images from other splits (e.g., to create 'Next 5%').
    """
    try:
        split = DatasetSplitService.create_split(
            db=db,
            dataset_id=dataset_id,
            name=split_in.name,
            split_type=split_in.split_type,
            split_value=split_in.split_value,
            created_by_id=current_user.id,
            excluded_split_ids=split_in.excluded_split_ids
        )
        return split
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{dataset_id}/splits", response_model=List[DatasetSplitResponse])
def list_dataset_splits(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all splits for a dataset.
    """
    splits = db.query(DatasetSplit).filter(DatasetSplit.dataset_id == dataset_id).all()
    return splits

@router.get("/splits/{split_id}", response_model=DatasetSplitResponse)
def get_dataset_split(
    split_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific split.
    """
    split = db.query(DatasetSplit).filter(DatasetSplit.id == split_id).first()
    if not split:
        raise HTTPException(status_code=404, detail="Dataset split not found")
    return split
