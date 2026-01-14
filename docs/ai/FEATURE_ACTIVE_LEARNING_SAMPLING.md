# Implementation Proposal: Smart Dataset Subsets & Active Learning

This document outlines the architectural and functional plan to introduce advanced sampling (statistical & geometric) into the Active Learning workflow without cluttering the UI.

## 1. Architectural Changes

### Database & Models (`backend/models/`)
To support diversity sampling and clustering, we need to store vector representations of images.

*   **`Image` Model**: 
    *   Add `embedding` column. **Technical Note**: Use `pgvector` extension with `Vector(dimension)` type.
    *   Add `cluster_id` (Integer, nullable) to cache k-means assignment results.
*   **`DatasetSplit` Model**: 
    *   Extend `split_type` to support new strategies: 
        *   `'k_means_centroid'` (Diversity)
        *   `'outlier_detection'` (Uncertainty)
        *   `'statistically_sampled'` (Confidence-based)

### Backend Services (`backend/services/`)

*   **`EmbeddingService`**: 
    *   Ensure integration to generate embeddings for all images in a dataset (triggered on upload or via batch job).
*   **New `ClusteringService`**:
    *   **Logic**: Fetch embeddings $\rightarrow$ Run K-Means (e.g., via `scikit-learn` or `faiss`) $\rightarrow$ Update `Image.cluster_id`.
    *   **Selection (Diversity)**: For "Most Centered" strategy, select images with the minimum Euclidean distance to the centroid of each cluster.
*   **`DatasetSplitService` Updates**:
    *   **Statistical Formula**: Implement the sample size determination formula for statistically significant subsets.
    *   **Exclusion Logic**: Ensure "Test Sets" and "Annotation Sets" are mutually exclusive by default.

## 2. Functional Workflow (The "Wizard")

The active learning wizard will guide the user through 3 clear steps to partition their dataset.

### Step 1: Create Annotation Set (The "Training" Data)
*   **Goal**: Select images to be labelled first (by humans or AI).
*   **Input**:
    *   **Size**: User selects a percentage (e.g., "5%") or absolute count.
    *   **Smart Recommendation**: A "Calculator" button/tooltip shows the statistically recommended sample size based on dataset total ($N$) to achieve a 95% Confidence Level with 5% Margin of Error.
        *   *Formula*: $$n = \frac{N \cdot Z^2 \cdot 0.25}{E^2 \cdot (N-1) + Z^2 \cdot 0.25}$$
        *   *Where*: $Z = 1.96$ (for 95% conf), $E = 0.05$ (error margin), $p = 0.5$ (variability, used as 0.25).
*   **Strategy**:
    *   **Random**: Pure random selection.
    *   **Diversity (K-Means)**: "Select Representative Samples". Algorithms picks $k$ centroids and selects the nearest image to each.
    *   **Uncertainty/Dissimilarity**: "Select Least Similar". Focuses on outliers or edge cases (requires reference set or density estimation).

### Step 2: Create Test Set (The "Gold" Standard)
*   **Goal**: A small, high-quality set to verify Prompts/Models.
*   **Action**: Select a fixed number (e.g., 20-50 images).
*   **Source**:
    *   *Manual*: User manually picks images from a gallery view.
    *   *Stratified*: Auto-sample from different `cluster_id` groups to ensure coverage of all data types.
*   **Post-Action**: These images are flagged for "Priority Labelling".

### Step 3: The Unlabelled Pool
*   **Action**: All remaining images (Total - Annotation Set - Test Set) are automatically tagged/grouped as `pool_unlabelled`.
*   **Usage**: These remain available for future active learning iterations (e.g., "Find images similar to the ones the model got wrong in the Test Set").

## 3. Technical Implementation Roadmap

### Phase 1: Embedding Infrastructure
1.  **Migration**: Add `pgvector` extension to Postgres and add `embedding` column to `images` table.
2.  **Backfill**: Create a script/job to generate embeddings for existing datasets using `EmbeddingService`.

### Phase 2: Clustering Logic
1.  Implement `ClusteringService.perform_kmeans(dataset_id, k=20)`.
2.  Store `cluster_id` on images.
3.  Implement "Centroid Selection" logic (finding image with min euclidean distance to cluster center).

### Phase 3: Dataset Split Service Upgrade
1.  Update `create_split` to accept `strategy_config` (json) to handle parameters for advanced strategies.
2.  Implement the Statistical Sample Size formula in Python.
3.  Add logic to handle "Remainder" splits (Unlabelled Pool) automatically.

### Phase 4: Frontend Wizard
1.  Update `ActiveLearningWizardComponent`.
2.  Add UI for "Statistical Accuracy" recommendation.
3.  Add "Sampling Strategy" dropdown (Random vs. Diversity).
