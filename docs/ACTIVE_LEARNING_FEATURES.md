# Active Learning & Smart Sampling Features

## Overview

This document describes the enhanced active learning workflow that enables intelligent dataset sampling for efficient annotation and model validation.

## Key Features

### 1. Statistical Sample Size Calculator

Automatically calculates the statistically significant sample size needed for your dataset using **Cochran's formula for finite populations**.

**Formula:**
```
n = [N × Z² × p(1-p)] / [E² × (N-1) + Z² × p(1-p)]
```

Where:
- `N` = Total dataset size
- `Z` = Z-score for confidence level (1.96 for 95%)
- `p` = Population proportion (0.5 for maximum variability)
- `E` = Margin of error (e.g., 0.05 for ±5%)

**Configurable Parameters:**
- **Confidence Level**: 90%, 95% (default), 99%
- **Margin of Error**: ±1%, ±3%, ±5% (default), ±10%

**API Endpoint:**
```
GET /api/v1/datasets/{dataset_id}/sample-size-calculator?confidence_level=0.95&margin_of_error=0.05
```

**Example Response:**
```json
{
  "recommended_size": 278,
  "percentage": 27.8,
  "confidence_level": 0.95,
  "margin_of_error": 0.05,
  "z_score": 1.96,
  "formula_explanation": "For a population of 1000 images, to achieve 95% confidence with ±5% margin of error, you need 278 samples (27.8%).",
  "is_exact": false
}
```

---

### 2. K-Means Clustering for Diversity Sampling

Groups images into clusters based on their embeddings (visual similarity), enabling selection of the most diverse and representative samples.

**Algorithm:**
1. Extracts embeddings from all images in the dataset
2. Runs k-means clustering with statistically determined `k`
3. Selects images closest to cluster centroids
4. Ensures proportional representation from all clusters

**K Value Selection:**
- **Auto-calculated** based on dataset size and confidence level
- **Formula**: `k = min(max(5, population_size / 10), max_k)`
- **Statistical constraint**: Each cluster must have ≥10-20 samples (based on confidence level)

**API Endpoints:**

```bash
# Perform clustering
POST /api/v1/datasets/{dataset_id}/cluster
{
  "k": 20,  # Optional - auto-calculated if not provided
  "confidence_level": 0.95
}

# Get clustering status
GET /api/v1/datasets/{dataset_id}/clustering-status

# Get recommended k value
GET /api/v1/datasets/{dataset_id}/k-recommendation?confidence_level=0.95
```

**Example: Clustering Result**
```json
{
  "cluster_count": 20,
  "images_clustered": 1000,
  "images_without_embeddings": 0,
  "cluster_sizes": {
    "0": 45,
    "1": 52,
    ...
  },
  "inertia": 1234.56
}
```

---

### 3. Dataset Splits with Purpose Tracking

Organize your dataset into distinct sets for different purposes:

- **Annotation Set**: Images to manually annotate (ground truth)
- **Test Set**: Small gold standard set for model validation
- **Unlabeled Pool**: Remaining images for future active learning iterations

**Split Types:**
- `random_percent`: Random selection by percentage
- `random_count`: Random selection by fixed count
- `k_means_centroid`: Diversity sampling using cluster centroids
- `manual`: Manual selection (future)

**Purpose Types:**
- `annotation`: For manual labeling
- `test`: For validation/testing
- `unlabeled_pool`: Auto-generated remainder

**API Endpoints:**

```bash
# Create a split
POST /api/v1/datasets/{dataset_id}/splits
{
  "name": "Annotation Set 1",
  "split_type": "k_means_centroid",
  "split_value": 5,  # 5% for random_percent
  "purpose": "annotation",
  "excluded_split_ids": ["uuid1", "uuid2"]  # For "Next 5%" workflow
}

# Create unlabeled pool (auto-calculates remainder)
POST /api/v1/datasets/{dataset_id}/unlabeled-pool

# List all splits
GET /api/v1/datasets/{dataset_id}/splits
```

---

### 4. Smart Annotation Wizard (Frontend)

Multi-step guided workflow for creating annotation and test sets.

**Step 1: Create Annotation Set**
- Choose sampling strategy:
  - 🎲 **Random Sampling**: Traditional random selection
  - 🎯 **Diversity Sampling**: K-means based selection (requires clustering)
- View statistical recommendation
- Configure sample size (percentage slider)
- Adjust confidence level & margin of error
- Exclude previous splits for "Next 5%" workflow
- One-click clustering if not already performed

**Step 2: Create Test Set (Optional)**
- Optional small test set (20-50 images recommended)
- Automatically excludes annotation set images
- Random sampling from remaining pool

**Step 3: Review & Finish**
- Visual summary of all splits
- Shows annotation set, test set, and unlabeled pool counts
- Creates unlabeled pool automatically
- Returns all created splits

**UI Features:**
- Expandable statistical calculator panel
- Real-time clustering status detection
- Progressive disclosure (advanced options hidden by default)
- Material Design stepper for clear workflow
- Auto-generates split names

---

## User Workflows

### Workflow 1: First-Time Annotation (Statistical Sampling)

1. **Open Wizard**: Click "Smart Annotation" on dataset
2. **View Recommendation**: Expand "Statistical Recommendation" to see suggested sample size (e.g., 278 images / 27.8%)
3. **Apply**: Click "Apply Recommended Size" to use the statistically valid percentage
4. **Create**: Create annotation set
5. **Skip Test Set**: (Optional) or create a small test set
6. **Finish**: Auto-create unlabeled pool
7. **Result**: Dataset split into:
   - Annotation Set: 278 images (27.8%)
   - Unlabeled Pool: 722 images (72.2%)

### Workflow 2: Diversity-Based Sampling

1. **Run Clustering**: Click "Run Clustering" in wizard (or pre-run via API)
2. **Select Diversity Sampling**: Choose "🎯 Diversity Sampling" radio button
3. **Set Sample Size**: Choose 5% (or use statistical recommendation)
4. **Create**: System selects 50 most diverse images (one from each cluster centroid)
5. **Result**: Annotation set contains maximum visual diversity

### Workflow 3: Iterative "Next 5%" Workflow

**Round 1:**
- Create 5% annotation set → Annotate → Validate model

**Round 2:**
- Open wizard
- Select "Exclude Previous Splits" → Choose "Annotation Set 1"
- Create 5% from remaining 95%
- Result: New 5% that doesn't overlap with Round 1

**Round 3+:**
- Repeat, excluding all previous annotation sets
- System automatically tracks lineage

---

## Database Schema

### Images Table (New Fields)

```sql
ALTER TABLE images ADD COLUMN embedding vector(1408);  -- Google Multimodal embedding
ALTER TABLE images ADD COLUMN cluster_id INTEGER;       -- K-means cluster assignment
CREATE INDEX idx_images_cluster_id ON images(cluster_id);
```

### Dataset Splits Table (New Fields)

```sql
ALTER TABLE dataset_splits ADD COLUMN purpose VARCHAR DEFAULT 'annotation';
CREATE INDEX idx_dataset_splits_purpose ON dataset_splits(purpose);

-- Extended split_type enum:
-- 'random_percent', 'random_count', 'k_means_centroid', 'auto_remainder'
```

---

## Backend Services

### `ClusteringService`

**Methods:**
- `perform_kmeans(db, dataset_id, k, confidence_level)`: Run k-means and update cluster_id
- `select_diverse_samples(db, dataset_id, sample_size, excluded_splits)`: Select centroid-nearest images
- `get_clustering_status(db, dataset_id)`: Check if clustering has been performed

### `DatasetSplitService`

**Methods:**
- `create_split(db, dataset_id, name, split_type, split_value, purpose, excluded_split_ids)`: Create any type of split
- `create_unlabeled_pool(db, dataset_id, created_by_id)`: Auto-create remainder split
- `get_split_images(db, split_id)`: Fetch images in a split

### `utils/statistical_calculator.py`

**Functions:**
- `calculate_sample_size(population_size, confidence_level, margin_of_error, population_proportion)`: Cochran's formula
- `get_k_value_for_clustering(population_size, confidence_level)`: Calculate statistically valid k

---

## Testing

### Manual Testing Checklist

**Statistical Calculator:**
- [ ] Calculator shows correct sample size for 1000 image dataset (should be ~278 for 95% confidence, ±5% error)
- [ ] Adjusting confidence level recalculates (99% should increase sample size)
- [ ] Adjusting margin of error recalculates (±1% should increase sample size)
- [ ] "Apply Recommended Size" updates percentage slider

**K-Means Clustering:**
- [ ] "Run Clustering" button works
- [ ] Clustering status updates after completion
- [ ] Diversity sampling option enables after clustering
- [ ] Diversity sampling selects correct number of images
- [ ] Selected images are visually diverse (manual inspection)

**Split Creation:**
- [ ] Random sampling creates correct percentage
- [ ] Diversity sampling creates correct percentage
- [ ] Excluded splits work (no overlap)
- [ ] Test set excludes annotation set images
- [ ] Unlabeled pool = total - annotation - test

**Wizard Flow:**
- [ ] Step 1 → Step 2 transition requires annotation set creation
- [ ] Step 2 can be skipped
- [ ] Step 3 shows correct summary
- [ ] Final result returns all splits

---

## Performance Considerations

### K-Means Performance

- **Dataset Size**: < 1000 images → instant, 1000-10000 → ~5-30s, 10000+ → ~1-5min
- **Optimization**: Runs async, user can continue working
- **Caching**: cluster_id stored in database, no need to re-cluster

### Embedding Generation

- Embeddings generated on image upload (already implemented in main branch)
- Uses Google Multimodal API (dimension: 1408)
- Stored in pgvector column for efficient similarity queries

---

## Future Enhancements

### Phase 1 (Current Implementation) ✅
- Statistical sample size calculator
- K-means clustering for diversity sampling
- Test set creation
- Unlabeled pool tracking
- Multi-step wizard UI

### Phase 2 (Future)
- **Active Learning Loop**: Auto-suggest next images to annotate based on model uncertainty
- **Stratified Sampling**: Ensure proportional representation of existing annotations
- **Manual Gallery Selection**: Let users manually pick test set images
- **Cluster Visualization**: PCA-reduced scatter plot of clusters
- **Confidence Drop Indicator**: Show when adjusting k reduces statistical significance

### Phase 3 (Advanced)
- **Uncertainty Sampling**: Select images where model is least confident
- **Query by Committee**: Use ensemble disagreement for selection
- **Expected Model Change**: Select images that would change model most
- **Embedding-based Search**: "Find images similar to this misclassified one"

---

## Troubleshooting

### "Clustering failed: No images with embeddings found"
**Cause**: Images haven't been processed yet (embeddings not generated)
**Solution**: Wait for image processing to complete, or trigger manually

### "K-means sampling failed: Ensure clustering has been performed"
**Cause**: Trying to use diversity sampling without running clustering first
**Solution**: Click "Run Clustering" button or run via API

### "No unlabeled images remaining in dataset"
**Cause**: All images already in annotation/test sets
**Solution**: This is expected - no pool needed if everything is labeled

### Unlabeled pool count doesn't match expectation
**Cause**: Test set or annotation set overlaps (shouldn't happen if using excludes)
**Solution**: Check excluded_split_ids in split creation requests

---

## API Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/datasets/{id}/sample-size-calculator` | GET | Calculate recommended sample size |
| `/datasets/{id}/cluster` | POST | Perform k-means clustering |
| `/datasets/{id}/clustering-status` | GET | Check clustering status |
| `/datasets/{id}/k-recommendation` | GET | Get recommended k value |
| `/datasets/{id}/splits` | POST | Create annotation/test split |
| `/datasets/{id}/splits` | GET | List all splits |
| `/datasets/{id}/unlabeled-pool` | POST | Create unlabeled pool |

---

## References

- **Cochran's Formula**: Cochran, W. G. (1977). Sampling Techniques (3rd ed.). Wiley.
- **K-Means Clustering**: MacQueen, J. (1967). Some methods for classification and analysis of multivariate observations.
- **Active Learning**: Settles, B. (2009). Active Learning Literature Survey. Computer Sciences Technical Report 1648.

---

**Last Updated**: 2026-01-14
**Authors**: Claude Sonnet 4.5
**Status**: ✅ Implemented (Plan A - Full Workflow)
