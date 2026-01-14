"""
Statistical utilities for calculating sample sizes.
"""
import math
from typing import Dict


def calculate_sample_size(
    population_size: int,
    confidence_level: float = 0.95,
    margin_of_error: float = 0.05,
    population_proportion: float = 0.5
) -> Dict[str, any]:
    """
    Calculate statistically significant sample size using Cochran's formula for finite populations.

    Formula: n = [N × Z² × p × (1-p)] / [E² × (N-1) + Z² × p × (1-p)]

    Args:
        population_size: Total number of items in the population (dataset size)
        confidence_level: Desired confidence level (0.90, 0.95, or 0.99). Default: 0.95 (95%)
        margin_of_error: Desired margin of error as a decimal (e.g., 0.05 for ±5%). Default: 0.05
        population_proportion: Expected proportion (0-1). Use 0.5 for maximum variability. Default: 0.5

    Returns:
        Dictionary containing:
        - recommended_size: int - Number of samples needed
        - percentage: float - Percentage of total population
        - confidence_level: float - Confidence level used
        - margin_of_error: float - Margin of error used
        - z_score: float - Z-score for the confidence level
        - formula_explanation: str - Human-readable formula explanation

    Example:
        >>> calculate_sample_size(population_size=1000, confidence_level=0.95, margin_of_error=0.05)
        {
            'recommended_size': 278,
            'percentage': 27.8,
            'confidence_level': 0.95,
            'margin_of_error': 0.05,
            ...
        }
    """
    # Z-score lookup table for common confidence levels
    z_scores = {
        0.90: 1.645,  # 90% confidence
        0.95: 1.96,   # 95% confidence
        0.99: 2.576   # 99% confidence
    }

    # Get Z-score (default to 1.96 for 95% if not in table)
    z = z_scores.get(confidence_level, 1.96)

    # Validate inputs
    if population_size <= 0:
        raise ValueError("Population size must be greater than 0")

    if not (0 < margin_of_error < 1):
        raise ValueError("Margin of error must be between 0 and 1")

    if not (0 < population_proportion < 1):
        raise ValueError("Population proportion must be between 0 and 1")

    # Handle edge case: if population is very small, recommend sampling all
    if population_size < 10:
        return {
            "recommended_size": population_size,
            "percentage": 100.0,
            "confidence_level": confidence_level,
            "margin_of_error": margin_of_error,
            "z_score": z,
            "formula_explanation": "Population too small - recommend sampling entire dataset",
            "is_exact": True
        }

    # Cochran's formula for finite population
    N = population_size
    E = margin_of_error
    p = population_proportion

    numerator = N * (z ** 2) * p * (1 - p)
    denominator = (E ** 2) * (N - 1) + (z ** 2) * p * (1 - p)

    n = numerator / denominator

    # Round up to ensure we meet the confidence level
    recommended_size = math.ceil(n)

    # Cap at population size (can't sample more than total)
    recommended_size = min(recommended_size, population_size)

    percentage = round((recommended_size / population_size) * 100, 2)

    formula_explanation = (
        f"For a population of {population_size} images, to achieve "
        f"{int(confidence_level * 100)}% confidence with ±{int(margin_of_error * 100)}% margin of error, "
        f"you need {recommended_size} samples ({percentage}%)."
    )

    return {
        "recommended_size": recommended_size,
        "percentage": percentage,
        "confidence_level": confidence_level,
        "margin_of_error": margin_of_error,
        "z_score": z,
        "formula_explanation": formula_explanation,
        "is_exact": False
    }


def get_k_value_for_clustering(
    population_size: int,
    confidence_level: float = 0.95
) -> Dict[str, any]:
    """
    Calculate statistically significant k value for k-means clustering.

    This ensures sufficient cluster granularity to represent dataset diversity
    while maintaining statistical power within each cluster.

    Rule of thumb: k should be chosen such that each cluster has at least
    ~10-15 samples for statistical validity.

    Args:
        population_size: Total number of items in the dataset
        confidence_level: Desired confidence level (affects minimum cluster size)

    Returns:
        Dictionary containing:
        - recommended_k: int - Recommended number of clusters
        - min_cluster_size: int - Minimum samples per cluster
        - max_k: int - Maximum reasonable k value
        - explanation: str - Human-readable explanation
    """
    # Minimum samples per cluster for statistical validity
    # Higher confidence requires larger clusters
    min_cluster_sizes = {
        0.90: 10,
        0.95: 15,
        0.99: 20
    }

    min_cluster_size = min_cluster_sizes.get(confidence_level, 15)

    # Calculate maximum reasonable k
    max_k = max(1, population_size // min_cluster_size)

    # Recommended k: 10% of population (capped by max_k)
    # This balances granularity with statistical validity
    recommended_k = min(max(5, population_size // 10), max_k)

    # Floor k at 2 (minimum for clustering)
    recommended_k = max(2, recommended_k)

    explanation = (
        f"For {population_size} images, recommended k={recommended_k} clusters. "
        f"This ensures each cluster has ≥{min_cluster_size} samples for "
        f"{int(confidence_level * 100)}% confidence. Valid range: 2 to {max_k}."
    )

    return {
        "recommended_k": recommended_k,
        "min_cluster_size": min_cluster_size,
        "max_k": max_k,
        "min_k": 2,
        "explanation": explanation,
        "confidence_level": confidence_level
    }
