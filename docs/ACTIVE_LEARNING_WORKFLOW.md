# Implementation Plan: Statistical Sampling & Active Learning Workflow

## Overview
This plan addresses the need to annotate large datasets efficiently by using statistical sampling and model-assisted labeling (Active Learning). It introduces a workflow to label a small "Ground Truth" sample, validate model performance, and then automatically label the remainder of the dataset.

## 1. Core Concepts

### 1.1 Dataset Splits (New Entity)
To support reproducible sampling and "Next 5%" workflows, we need to persist which images belong to which sample.
*   **Entity:** `DatasetSplit`
*   **Fields:**
    *   `id`: UUID
    *   `dataset_id`: UUID
    *   `name`: String (e.g., "Round 1 Sample", "Validation Set")
    *   `image_ids`: JSON/Array (List of UUIDs included in this split)
    *   `created_at`: Timestamp
    *   `type`: String ('random', 'manual', 'stratified')
*   **Purpose:** "Freezes" a subset of images for annotation or evaluation.

### 1.2 Workflow Stages
1.  **Sampling:** Select a subset (e.g., 5%) and save it as a `DatasetSplit`.
2.  **Annotation:** User manually labels images in this `DatasetSplit`.
3.  **Validation:** Run an `Evaluation` against this `DatasetSplit` to measure Model Accuracy.
4.  **Propagation (Auto-Labeling):**
    *   If Accuracy > Target (e.g., 90%): Run a `LabellingJob` on the **Complement** (All images NOT in the split).
    *   If Accuracy < Target: Generate a **New Split** (Next 5%) to increase Ground Truth coverage and retrain/refine logic (or just validate more).

## 2. Backend Changes

### 2.1 Database Schema
*   **Create `dataset_splits` table**:
    ```python
    class DatasetSplit(Base):
        __tablename__ = "dataset_splits"
        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"))
        name = Column(String, nullable=False)
        image_ids = Column(JSON, nullable=False)  # List[UUID]
        # Metadata about how it was created
        criteria = Column(JSON, nullable=True) # e.g. {"method": "random_percent", "value": 5}
    ```

### 2.2 Services & APIs
*   **`DatasetSplitService`**:
    *   `create_split(dataset_id, strategy="random_percent", value=5, exclude_split_ids=[...])`:
        *   Logic: Selects images from Dataset, excluding those in provided `exclude_split_ids` (to support "Next 5%").
    *   `get_split_images(split_id)`: Returns image objects.
*   **`LabellingJobService` Extensions**:
    *   Update `create_labelling_job` to accept `target_split_id` OR `exclude_split_id`.
        *   *Use Case:* "Label the rest" = Target Dataset excluding `DatasetSplit(Round 1)`.
    *   New Method: `promote_results_to_annotations(job_id, confidence_threshold=0.0)`:
        *   Converts `LabellingResult` entries into `Annotation` entries for the images.

### 2.3 Evaluation Updates
*   Enhance `Evaluation` to accept a `dataset_split_id` in its `selection_config`.

## 3. Frontend Changes

### 3.1 New Feature: "Smart Annotation" (Wizard)
*   **Step 1: Sampling Strategy**
    *   UI: "How much to verify?" (Slider 0-100%, or Count).
    *   Display: "Estimated Error Margin" (optional, if we use Cochran's formula).
    *   Action: Creates `DatasetSplit`.
*   **Step 2: Manual Annotation**
    *   Redirects to `DatasetView` filtered by the created `DatasetSplit`.
    *   User annotates these images.
*   **Step 3: Verification**
    *   Button: "Run Validation Evaluation".
    *   Select Model Config.
    *   Runs Evaluation on the split.
    *   Shows Report: "Model Accuracy: 92%".
*   **Step 4: Action**
    *   **Option A: "Auto-Label Remaining"**
        *   Triggers `LabellingJob` for (Total - Split).
        *   On completion, offers "Promote to Ground Truth".
    *   **Option B: "Expand Sample"**
        *   Go back to Step 1, create "Round 2" (Next 5%).

## 4. Integration Roadmap
1.  **Phase 1**: Backend Support for `DatasetSplit` and Split-based Queries.
2.  **Phase 2**: Frontend for creating/viewing Splits.
3.  **Phase 3**: "Promote to Annotation" backend logic.
4.  **Phase 4**: Full Wizard UI.
