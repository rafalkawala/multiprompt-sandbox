# Database Index Proposals

This document outlines proposed database indexes to improve the performance of the application's SQL queries. The proposals are based on an analysis of the codebase, specifically the API endpoints and service layers where database interaction occurs.

## 1. Projects Table

### Current State
- **Primary Key:** `id` (UUID)
- **Foreign Keys:** `created_by_id` (indexed by default in some DBs, but explicitly needed for filtering)
- **Queries:**
  - `list_projects`: `SELECT ... FROM projects ORDER BY projects.created_at DESC`
  - Ownership check: `SELECT ... FROM projects WHERE id = :id AND created_by_id = :user_id`

### Proposed Indexes
1.  **`idx_projects_created_at`**
    -   **Columns:** `(created_at DESC)`
    -   **Rationale:** The main dashboard lists projects sorted by creation date. As the number of projects grows, sorting without an index will become slow.
    -   **SQL:** `CREATE INDEX idx_projects_created_at ON projects (created_at DESC);`

2.  **`idx_projects_created_by_id`**
    -   **Columns:** `(created_by_id)`
    -   **Rationale:** Frequently used to filter projects by the current user (e.g., in `list_projects` if we restrict it in the future, or current ownership checks).
    -   **SQL:** `CREATE INDEX idx_projects_created_by_id ON projects (created_by_id);`

## 2. Datasets Table

### Current State
- **Primary Key:** `id` (UUID)
- **Foreign Keys:** `project_id`, `created_by_id`
- **Queries:**
  - `list_datasets`: `SELECT ... FROM datasets WHERE project_id = :project_id`
  - Filtering/Ownership: `SELECT ... FROM datasets WHERE id = :id AND project_id = :project_id`

### Proposed Indexes
1.  **`idx_datasets_project_id`**
    -   **Columns:** `(project_id)`
    -   **Rationale:** Almost every query for datasets filters by `project_id`. This is critical for performance.
    -   **SQL:** `CREATE INDEX idx_datasets_project_id ON datasets (project_id);`

2.  **`idx_datasets_created_by_id`**
    -   **Columns:** `(created_by_id)`
    -   **Rationale:** Used for permission checks and potentially filtering by owner.
    -   **SQL:** `CREATE INDEX idx_datasets_created_by_id ON datasets (created_by_id);`

## 3. Images Table

### Current State
- **Primary Key:** `id` (UUID)
- **Foreign Keys:** `dataset_id`, `uploaded_by_id`
- **Queries:**
  - `list_images`: `SELECT ... FROM images WHERE dataset_id = :dataset_id ORDER BY uploaded_at DESC LIMIT :limit OFFSET :skip`
  - Duplicate check: `SELECT ... FROM images WHERE dataset_id = :dataset_id AND filename = :filename`
  - Evaluation selection: `SELECT ... FROM images WHERE dataset_id = :dataset_id AND processing_status != 'failed'`

### Proposed Indexes
1.  **`idx_images_dataset_id_uploaded_at`**
    -   **Columns:** `(dataset_id, uploaded_at DESC)`
    -   **Rationale:** This composite index is perfect for the paginated `list_images` query, which filters by `dataset_id` and sorts by `uploaded_at`. It allows the database to find the relevant rows and read them in the correct order without a separate sort step.
    -   **SQL:** `CREATE INDEX idx_images_dataset_id_uploaded_at ON images (dataset_id, uploaded_at DESC);`

2.  **`idx_images_dataset_id_filename`**
    -   **Columns:** `(dataset_id, filename)`
    -   **Rationale:** Used to check for duplicate filenames within a dataset during upload.
    -   **SQL:** `CREATE INDEX idx_images_dataset_id_filename ON images (dataset_id, filename);`

3.  **`idx_images_dataset_processing_status`**
    -   **Columns:** `(dataset_id, processing_status)`
    -   **Rationale:** Used by the evaluation service to fetch valid images (`processing_status != 'failed'`).
    -   **SQL:** `CREATE INDEX idx_images_dataset_processing_status ON images (dataset_id, processing_status);`

## 4. Evaluations Table

### Current State
- **Primary Key:** `id` (UUID)
- **Foreign Keys:** `project_id`, `dataset_id`, `model_config_id`, `created_by_id`
- **Queries:**
  - `list_evaluations`: `SELECT ... FROM evaluations WHERE created_by_id = :user_id [AND project_id = :project_id] ORDER BY created_at DESC`

### Proposed Indexes
1.  **`idx_evaluations_created_by_id_created_at`**
    -   **Columns:** `(created_by_id, created_at DESC)`
    -   **Rationale:** Optimizes the main list view for evaluations, which filters by user and sorts by date.
    -   **SQL:** `CREATE INDEX idx_evaluations_created_by_id_created_at ON evaluations (created_by_id, created_at DESC);`

2.  **`idx_evaluations_project_id`**
    -   **Columns:** `(project_id)`
    -   **Rationale:** Used for filtering evaluations by project.
    -   **SQL:** `CREATE INDEX idx_evaluations_project_id ON evaluations (project_id);`

## 5. Evaluation Results Table

### Current State
- **Primary Key:** `id` (UUID)
- **Foreign Keys:** `evaluation_id`, `image_id`
- **Queries:**
  - Statistics: `SELECT count(*), is_correct FROM evaluation_results WHERE evaluation_id = :id GROUP BY is_correct`
  - Results List: `SELECT ... FROM evaluation_results WHERE evaluation_id = :id [AND is_correct = :bool]`

### Proposed Indexes
1.  **`idx_evaluation_results_evaluation_id`**
    -   **Columns:** `(evaluation_id)`
    -   **Rationale:** Essential for fetching all results belonging to an evaluation.
    -   **SQL:** `CREATE INDEX idx_evaluation_results_evaluation_id ON evaluation_results (evaluation_id);`

2.  **`idx_evaluation_results_evaluation_id_is_correct`**
    -   **Columns:** `(evaluation_id, is_correct)`
    -   **Rationale:** Optimizes queries that filter results by correctness (e.g., "Show me all incorrect predictions") and for calculating accuracy statistics.
    -   **SQL:** `CREATE INDEX idx_evaluation_results_evaluation_id_is_correct ON evaluation_results (evaluation_id, is_correct);`

## Summary of Alembic Migration Steps

To implement these changes, create a new Alembic revision (`alembic revision -m "add_performance_indexes"`) and add the following operations to the `upgrade()` function:

```python
def upgrade() -> None:
    # Projects
    op.create_index('idx_projects_created_at', 'projects', [sa.text('created_at DESC')])
    op.create_index('idx_projects_created_by_id', 'projects', ['created_by_id'])

    # Datasets
    op.create_index('idx_datasets_project_id', 'datasets', ['project_id'])
    op.create_index('idx_datasets_created_by_id', 'datasets', ['created_by_id'])

    # Images
    op.create_index('idx_images_dataset_id_uploaded_at', 'images', ['dataset_id', sa.text('uploaded_at DESC')])
    op.create_index('idx_images_dataset_id_filename', 'images', ['dataset_id', 'filename'])
    op.create_index('idx_images_dataset_processing_status', 'images', ['dataset_id', 'processing_status'])

    # Evaluations
    op.create_index('idx_evaluations_created_by_id_created_at', 'evaluations', ['created_by_id', sa.text('created_at DESC')])
    op.create_index('idx_evaluations_project_id', 'evaluations', ['project_id'])

    # Evaluation Results
    op.create_index('idx_evaluation_results_evaluation_id', 'evaluation_results', ['evaluation_id'])
    op.create_index('idx_evaluation_results_evaluation_id_is_correct', 'evaluation_results', ['evaluation_id', 'is_correct'])
```
