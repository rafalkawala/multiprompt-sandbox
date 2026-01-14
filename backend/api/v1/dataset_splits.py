from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_db
from models.user import User
from api.deps import get_current_user
from schemas.dataset_split import DatasetSplitCreate, DatasetSplitResponse
from services.dataset_split_service import DatasetSplitService
from services.clustering_service import ClusteringService
from models.dataset_split import DatasetSplit
from utils.statistical_calculator import calculate_sample_size, get_k_value_for_clustering

router = APIRouter()

@router.post("/{dataset_id}/splits", response_model=DatasetSplitResponse)
def create_dataset_split(
    dataset_id: UUID,
    split_in: DatasetSplitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new split for a dataset (e.g., Random 5%, Diversity Sampling).
    Can optionally exclude images from other splits (e.g., to create 'Next 5%').

    Supported split_types:
    - random_percent: Random selection by percentage
    - random_count: Random selection by fixed count
    - k_means_centroid: Diversity sampling using k-means clustering
    - manual: Manual selection (requires image_ids)

    Supported purposes:
    - annotation: For manual annotation (default)
    - test: For testing/validation
    - unlabeled_pool: For remaining unlabeled images
    """
    try:
        split = DatasetSplitService.create_split(
            db=db,
            dataset_id=dataset_id,
            name=split_in.name,
            split_type=split_in.split_type,
            split_value=split_in.split_value,
            purpose=split_in.purpose or 'annotation',
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


@router.get("/{dataset_id}/sample-size-calculator")
def calculate_statistical_sample_size(
    dataset_id: UUID,
    confidence_level: float = Query(0.95, ge=0.90, le=0.99, description="Confidence level (0.90, 0.95, or 0.99)"),
    margin_of_error: float = Query(0.05, ge=0.01, le=0.10, description="Margin of error (0.01 to 0.10)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Calculate statistically significant sample size for a dataset.

    Uses Cochran's formula for finite populations to determine how many images
    should be sampled to achieve the desired confidence level and margin of error.

    Args:
        dataset_id: UUID of the dataset
        confidence_level: Desired confidence level (default: 0.95 for 95%)
        margin_of_error: Desired margin of error (default: 0.05 for ±5%)

    Returns:
        Dictionary containing:
        - recommended_size: Number of samples needed
        - percentage: Percentage of total dataset
        - confidence_level: Confidence level used
        - margin_of_error: Margin of error used
        - formula_explanation: Human-readable explanation
    """
    # Get total image count
    from models.image import Image
    from sqlalchemy import func

    total_images = db.query(func.count(Image.id)).filter(
        Image.dataset_id == dataset_id
    ).scalar()

    if not total_images or total_images == 0:
        raise HTTPException(status_code=404, detail="No images found in dataset")

    try:
        result = calculate_sample_size(
            population_size=total_images,
            confidence_level=confidence_level,
            margin_of_error=margin_of_error
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ClusterRequest(BaseModel):
    k: Optional[int] = None
    confidence_level: float = 0.95


@router.post("/{dataset_id}/cluster")
def perform_clustering(
    dataset_id: UUID,
    request: ClusterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Perform k-means clustering on dataset images using their embeddings.

    This groups images into clusters based on visual similarity, which enables
    diversity sampling (selecting representative images from each cluster).

    Args:
        dataset_id: UUID of the dataset
        request: ClusterRequest with optional k (number of clusters)

    Returns:
        Dictionary containing clustering results:
        - cluster_count: Number of clusters created
        - images_clustered: Number of images assigned to clusters
        - cluster_sizes: Distribution of images across clusters
    """
    try:
        result = ClusteringService.perform_kmeans(
            db=db,
            dataset_id=dataset_id,
            k=request.k,
            confidence_level=request.confidence_level
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{dataset_id}/clustering-status")
def get_clustering_status(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get clustering status for a dataset.

    Returns:
        Dictionary containing:
        - is_clustered: Whether clustering has been performed
        - cluster_count: Number of clusters
        - images_clustered: Number of images with cluster assignments
        - images_without_embeddings: Number of images without embeddings
    """
    result = ClusteringService.get_clustering_status(db=db, dataset_id=dataset_id)
    return result


@router.get("/{dataset_id}/k-recommendation")
def get_k_recommendation(
    dataset_id: UUID,
    confidence_level: float = Query(0.95, ge=0.90, le=0.99),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get recommended k value for k-means clustering.

    Args:
        dataset_id: UUID of the dataset
        confidence_level: Desired confidence level

    Returns:
        Dictionary containing:
        - recommended_k: Recommended number of clusters
        - min_cluster_size: Minimum samples per cluster for statistical validity
        - explanation: Human-readable explanation
    """
    from models.image import Image
    from sqlalchemy import func

    # Count images with embeddings
    images_with_embeddings = db.query(func.count(Image.id)).filter(
        Image.dataset_id == dataset_id,
        Image.embedding.isnot(None)
    ).scalar()

    if not images_with_embeddings or images_with_embeddings == 0:
        raise HTTPException(
            status_code=404,
            detail="No images with embeddings found. Generate embeddings first."
        )

    result = get_k_value_for_clustering(
        population_size=images_with_embeddings,
        confidence_level=confidence_level
    )
    return result


@router.post("/{dataset_id}/unlabeled-pool", response_model=DatasetSplitResponse)
def create_unlabeled_pool(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create an unlabeled pool split containing all images not in any other split.

    This explicitly tracks remaining unlabeled images after creating annotation
    and test sets, making them queryable for future active learning iterations.

    Returns:
        DatasetSplit for the unlabeled pool
    """
    pool = DatasetSplitService.create_unlabeled_pool(
        db=db,
        dataset_id=dataset_id,
        created_by_id=current_user.id
    )

    if not pool:
        raise HTTPException(
            status_code=404,
            detail="No unlabeled images remaining in dataset"
        )

    return pool
