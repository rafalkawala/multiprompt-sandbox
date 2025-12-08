# Implementation Plan: Dataset Subselection for Evaluations (Issue #36)

## Overview
This plan details the implementation of a robust "Dataset Subselection" feature, allowing users to run evaluations on a subset of a dataset (random sample or manual selection) rather than the entire dataset.

## 1. Data Model Changes (Backend)

### Database Schema
*   **Table:** `evaluations`
*   **Column:** Add `selection_config` (JSON, nullable)
*   **Migration:** Create Alembic migration script.

### SQLAlchemy Model (`backend/models/evaluation.py`)
```python
selection_config = Column(JSON, nullable=True) 
# Structure:
# {
#   "mode": "all" | "random_count" | "random_percent" | "manual",
#   "count": 100,       # used for random_count
#   "percent": 20,      # used for random_percent
#   "image_ids": [...]  # used for manual
# }
```

### API Schema (`backend/api/v1/evaluations.py`)
*   Update `EvaluationCreate` to include optional `selection_config`.

## 2. Backend Logic (`backend/api/v1/evaluations.py`)

### `create_evaluation`
*   Accept and validate `selection_config`.
*   Save to database.

### `run_evaluation_task`
*   Modify the image fetching query based on `selection_config`:
    *   **Mode: `all`** (Default): No change.
    *   **Mode: `random_count`**: Use `db.query(Image)...order_by(func.random()).limit(count)`.
    *   **Mode: `random_percent`**: Calculate count based on total, then apply random limit.
    *   **Mode: `manual`**: Use `db.query(Image)...filter(Image.id.in_(image_ids))`.

## 3. Frontend Changes (`frontend/src/app/features/evaluations`)

### UI Layout (`evaluations.component.html`)
*   Add an **"Advanced Settings"** button next to the Dataset dropdown.
*   Button state:
    *   **Default:** Outlined button (inactive look).
    *   **Active:** Filled/Colored button (primary color) when a subselection is configured.
    *   **Label:** "Advanced Settings" or "Subselect: [Summary]" (e.g., "Subselect: 50 images").

### Subselection Dialog (`DatasetSubselectionDialogComponent`)
*   **New Component:** `frontend/src/app/features/evaluations/subselection-dialog/subselection-dialog.component.ts`
*   **UI Elements:**
    *   **Radio Group:** Selection Mode (All Images, Random Sample, Manual Selection).
    *   **Random Settings:**
        *   Radio for "By Count" vs "By Percentage".
        *   Input field for number/percent.
    *   **Manual Selection:**
        *   Re-implement image grid (virtual scroll recommended if large dataset, or simple grid with pagination).
        *   Click to toggle selection.
        *   "Select All" / "Deselect All" buttons.
    *   **Footer:**
        *   "Cancel" (Close without saving).
        *   "Clear Selection" (Reset to "All").
        *   "Save & Close".

### Integration (`evaluations.component.ts`)
*   Add `selectionConfig` state variable.
*   Pass `selectionConfig` to `createEvaluation` service call.

## 4. Execution Plan
1.  **Migration:** Generate and run Alembic migration for `selection_config`.
2.  **Backend:** Update models and logic in `evaluations.py`.
3.  **Frontend Service:** Update `EvaluationsService` interface.
4.  **Frontend UI:** Create dialog component and integrate into main form.
5.  **Verify:** Test random sampling and manual selection.
