"""
Clustering service for diversity sampling using k-means on image embeddings.
"""
import structlog
import numpy as np
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
from sklearn.cluster import KMeans

from models.image import Image
from models.project import Dataset
from utils.statistical_calculator import get_k_value_for_clustering

logger = structlog.get_logger(__name__)


class ClusteringService:
    """Service for performing k-means clustering on image embeddings."""

    @staticmethod
    def perform_kmeans(
        db: Session,
        dataset_id: UUID,
        k: Optional[int] = None,
        confidence_level: float = 0.95
    ) -> Dict[str, any]:
        """
        Perform k-means clustering on image embeddings for a dataset.

        Updates the cluster_id field for each image in the dataset.

        Args:
            db: Database session
            dataset_id: UUID of the dataset to cluster
            k: Number of clusters (if None, calculated automatically)
            confidence_level: Confidence level for automatic k calculation

        Returns:
            Dictionary containing:
            - cluster_count: int - Number of clusters created
            - centroids: List of centroid vectors
            - cluster_sizes: Dict mapping cluster_id to count
            - images_clustered: int - Total images assigned to clusters
            - images_without_embeddings: int - Images skipped (no embedding)

        Raises:
            ValueError: If dataset not found or insufficient embeddings
        """
        logger.info("starting_kmeans_clustering", dataset_id=str(dataset_id), k=k)

        # Get dataset
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Get all images with embeddings
        images_with_embeddings = db.query(Image).filter(
            Image.dataset_id == dataset_id,
            Image.embedding.isnot(None)
        ).all()

        if not images_with_embeddings:
            raise ValueError(f"No images with embeddings found in dataset {dataset_id}")

        logger.info("found_images_with_embeddings", count=len(images_with_embeddings))

        # Determine k if not provided
        if k is None:
            k_info = get_k_value_for_clustering(
                population_size=len(images_with_embeddings),
                confidence_level=confidence_level
            )
            k = k_info["recommended_k"]
            logger.info("auto_calculated_k", k=k, info=k_info)

        # Validate k
        if k < 2:
            raise ValueError("k must be at least 2 for clustering")

        if k > len(images_with_embeddings):
            logger.warning("k_exceeds_population", k=k, population=len(images_with_embeddings))
            k = len(images_with_embeddings)

        # Extract embeddings as numpy array
        embeddings_matrix = np.array([
            np.array(img.embedding) for img in images_with_embeddings
        ])

        logger.info("embeddings_extracted", shape=embeddings_matrix.shape)

        # Perform k-means clustering
        logger.info("running_kmeans", k=k, n_samples=len(embeddings_matrix))

        kmeans = KMeans(
            n_clusters=k,
            random_state=42,  # For reproducibility
            n_init=10,  # Number of times k-means runs with different centroid seeds
            max_iter=300
        )

        cluster_labels = kmeans.fit_predict(embeddings_matrix)
        centroids = kmeans.cluster_centers_

        logger.info("kmeans_completed", inertia=kmeans.inertia_)

        # Update database with cluster assignments
        cluster_sizes = {}

        for img, cluster_label in zip(images_with_embeddings, cluster_labels):
            cluster_id = int(cluster_label)
            img.cluster_id = cluster_id

            # Track cluster sizes
            cluster_sizes[cluster_id] = cluster_sizes.get(cluster_id, 0) + 1

        db.commit()

        logger.info("cluster_assignments_saved", cluster_sizes=cluster_sizes)

        # Count images without embeddings
        total_images = db.query(func.count(Image.id)).filter(
            Image.dataset_id == dataset_id
        ).scalar()

        images_without_embeddings = total_images - len(images_with_embeddings)

        return {
            "cluster_count": k,
            "centroids": centroids.tolist(),  # Convert numpy array to list for JSON serialization
            "cluster_sizes": cluster_sizes,
            "images_clustered": len(images_with_embeddings),
            "images_without_embeddings": images_without_embeddings,
            "inertia": float(kmeans.inertia_)  # Sum of squared distances to centroids
        }

    @staticmethod
    def select_diverse_samples(
        db: Session,
        dataset_id: UUID,
        sample_size: int,
        excluded_split_ids: Optional[List[UUID]] = None
    ) -> List[UUID]:
        """
        Select diverse samples by choosing images closest to cluster centroids.

        This ensures the sample represents the full diversity of the dataset
        by selecting representative images from each cluster.

        Args:
            db: Database session
            dataset_id: UUID of the dataset
            sample_size: Number of samples to select
            excluded_split_ids: List of split IDs to exclude images from

        Returns:
            List of image UUIDs selected for diversity

        Raises:
            ValueError: If dataset not found or clustering not performed
        """
        logger.info("selecting_diverse_samples", dataset_id=str(dataset_id), sample_size=sample_size)

        # Get excluded image IDs
        excluded_images = []
        if excluded_split_ids:
            from models.dataset_split import DatasetSplit
            for split_id in excluded_split_ids:
                split = db.query(DatasetSplit).filter(DatasetSplit.id == split_id).first()
                if split and split.image_ids:
                    excluded_images.extend(split.image_ids)

            excluded_images = list(set(excluded_images))  # Deduplicate

        # Get images with cluster assignments and embeddings
        query = db.query(Image).filter(
            Image.dataset_id == dataset_id,
            Image.cluster_id.isnot(None),
            Image.embedding.isnot(None)
        )

        if excluded_images:
            query = query.filter(Image.id.notin_(excluded_images))

        images = query.all()

        if not images:
            raise ValueError(f"No clustered images found in dataset {dataset_id}. Run clustering first.")

        logger.info("found_clustered_images", count=len(images))

        # Group images by cluster
        clusters: Dict[int, List[Image]] = {}
        for img in images:
            if img.cluster_id not in clusters:
                clusters[img.cluster_id] = []
            clusters[img.cluster_id].append(img)

        # Re-calculate centroids from current available images
        # (in case some images were excluded)
        centroids = {}
        for cluster_id, cluster_images in clusters.items():
            embeddings = np.array([np.array(img.embedding) for img in cluster_images])
            centroid = np.mean(embeddings, axis=0)
            centroids[cluster_id] = centroid

        logger.info("recalculated_centroids", cluster_count=len(centroids))

        # Select images closest to each centroid
        selected_images = []

        # Calculate how many samples to take from each cluster
        # Distribute proportionally to cluster size
        total_clustered = len(images)
        samples_per_cluster = {}

        for cluster_id, cluster_images in clusters.items():
            proportion = len(cluster_images) / total_clustered
            count = max(1, round(proportion * sample_size))  # At least 1 per cluster
            samples_per_cluster[cluster_id] = count

        # Adjust if we allocated more than sample_size
        total_allocated = sum(samples_per_cluster.values())
        if total_allocated > sample_size:
            # Reduce from largest clusters
            sorted_clusters = sorted(samples_per_cluster.items(), key=lambda x: x[1], reverse=True)
            excess = total_allocated - sample_size
            for cluster_id, count in sorted_clusters:
                if excess <= 0:
                    break
                reduction = min(count - 1, excess)
                samples_per_cluster[cluster_id] -= reduction
                excess -= reduction

        logger.info("samples_per_cluster", allocation=samples_per_cluster)

        # For each cluster, select images closest to centroid
        for cluster_id, cluster_images in clusters.items():
            n_samples = samples_per_cluster.get(cluster_id, 0)

            if n_samples == 0:
                continue

            centroid = centroids[cluster_id]

            # Calculate distances to centroid
            distances = []
            for img in cluster_images:
                embedding = np.array(img.embedding)
                distance = np.linalg.norm(embedding - centroid)
                distances.append((img, distance))

            # Sort by distance and take n_samples closest
            distances.sort(key=lambda x: x[1])
            selected = [img for img, _ in distances[:n_samples]]

            selected_images.extend(selected)

        # If we still haven't reached sample_size, add more from largest clusters
        if len(selected_images) < sample_size:
            remaining = sample_size - len(selected_images)
            selected_ids = {img.id for img in selected_images}

            # Get all unselected images
            unselected = [img for img in images if img.id not in selected_ids]

            # Add random unselected images
            import random
            additional = random.sample(unselected, min(remaining, len(unselected)))
            selected_images.extend(additional)

        # Return UUIDs
        selected_uuids = [str(img.id) for img in selected_images[:sample_size]]

        logger.info("diversity_sampling_complete", selected_count=len(selected_uuids))

        return selected_uuids

    @staticmethod
    def get_clustering_status(db: Session, dataset_id: UUID) -> Dict[str, any]:
        """
        Get clustering status for a dataset.

        Args:
            db: Database session
            dataset_id: UUID of the dataset

        Returns:
            Dictionary containing:
            - is_clustered: bool - Whether clustering has been performed
            - cluster_count: int - Number of unique clusters
            - images_clustered: int - Number of images with cluster assignments
            - images_without_clusters: int - Number of images without clusters
            - images_without_embeddings: int - Number of images without embeddings
        """
        # Count images with cluster assignments
        images_with_clusters = db.query(func.count(Image.id)).filter(
            Image.dataset_id == dataset_id,
            Image.cluster_id.isnot(None)
        ).scalar()

        # Count unique clusters
        cluster_count_result = db.query(func.count(func.distinct(Image.cluster_id))).filter(
            Image.dataset_id == dataset_id,
            Image.cluster_id.isnot(None)
        ).scalar()

        cluster_count = cluster_count_result if cluster_count_result else 0

        # Count images without clusters
        images_without_clusters = db.query(func.count(Image.id)).filter(
            Image.dataset_id == dataset_id,
            Image.cluster_id.is_(None)
        ).scalar()

        # Count images without embeddings
        images_without_embeddings = db.query(func.count(Image.id)).filter(
            Image.dataset_id == dataset_id,
            Image.embedding.is_(None)
        ).scalar()

        is_clustered = images_with_clusters > 0 and cluster_count > 0

        return {
            "is_clustered": is_clustered,
            "cluster_count": cluster_count,
            "images_clustered": images_with_clusters,
            "images_without_clusters": images_without_clusters,
            "images_without_embeddings": images_without_embeddings
        }
