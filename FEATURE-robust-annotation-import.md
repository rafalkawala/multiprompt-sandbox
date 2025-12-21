# Feature: Robust Annotation Import

## 1. Problem Statement
The current annotation import process is synchronous, potentially slow for large files, and lacks user feedback. Users receive vague error messages and cannot see progress. The UI blocks without a clear "busy" state, leading to a poor user experience.

## 2. Objectives
- **Responsiveness**: Move processing to a background task to prevent timeouts and UI freezing.
- **Visibility**: Provide real-time progress (processed/total rows) and a detailed log of errors as they happen.
- **Robustness**: Handle large files gracefully. Provide a final comprehensive report.
- **UX**: Use a modal dialog with a "greyed out" backdrop to focus the user on the task and prevent accidental interruptions.

## 3. Architecture Design

### 3.1 Backend (Async Background Task)
We will use FastAPI's built-in `BackgroundTasks` to handle the processing without external queues (Cloud Tasks), keeping the architecture simple while ensuring the UI remains responsive.

**New Database Model:** `AnnotationImportJob`
- `id` (UUID): Primary Key
- `dataset_id` (UUID): Foreign Key
- `user_id` (UUID): Foreign Key
- `status`: Enum (`pending`, `processing`, `completed`, `failed`)
- `total_rows` (int): Total rows to process
- `processed_rows` (int): Rows processed so far
- `created_rows` (int): Successful inserts
- `updated_rows` (int): Successful updates
- `skipped_rows` (int): Rows skipped (empty/duplicates)
- `error_count` (int): Total errors found
- `errors` (JSON): List of error objects `[{row: 1, message: "Invalid value", data: {...}}]`
- `created_at`, `updated_at`, `completed_at`

**API Changes:**
- `POST .../import`:
  - Accepts file upload.
  - Creates `AnnotationImportJob` (pending).
  - Triggers `BackgroundTasks.add_task(service.process_import_job, job_id, file_path)`.
  - Returns `job_id`.
- `GET .../import/{job_id}`:
  - Returns job status, progress counts, and error list.

**Processing Logic (Chunked):**
1.  Read CSV in chunks (e.g., 100 rows) using `pandas` chunksize or manual slicing.
2.  **Validation**: Validate batch in memory.
3.  **Bulk Operations**:
    -   Identify images (bulk query).
    -   Prepare `Annotation` objects.
    -   Use `bulk_save_objects` or equivalent for efficient upserts (SQLAlchemy 2.0 style or bulk_insert_mappings).
4.  **Progress Update**: Update `AnnotationImportJob` counters after each chunk.
5.  **Error Handling**: Capture row-level errors, append to `job.errors` (limit size if needed), and continue processing other rows.

### 3.2 Frontend (Polling Dialog)
- **New Component:** `AnnotationImportDialogComponent`
  - **State 1: Selection**: File picker.
  - **State 2: Processing**:
    -   Start Import -> Receive `job_id`.
    -   Poll `GET /import/{job_id}` every 1s.
    -   Display Progress Bar (`processed / total`).
    -   Display "Live Log" of errors/warnings as they appear.
  - **State 3: Summary**:
    -   Final counts.
    -   List of all errors.
    -   Option to close.

## 4. Implementation Plan

### Phase 1: Backend Foundation
1.  **Model**: Create `backend/models/import_job.py`.
    ```python
    class ImportJobStatus(str, enum.Enum):
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"

    class AnnotationImportJob(Base):
        __tablename__ = "annotation_import_jobs"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
        created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
        status = Column(Enum(ImportJobStatus), default=ImportJobStatus.PENDING, nullable=False)
        
        # File handling
        temp_file_path = Column(String, nullable=True)
        
        # Progress tracking
        total_rows = Column(Integer, default=0)
        processed_rows = Column(Integer, default=0)
        
        # Stats
        created_count = Column(Integer, default=0)
        updated_count = Column(Integer, default=0)
        skipped_count = Column(Integer, default=0)
        error_count = Column(Integer, default=0)
        
        # Detailed logs
        errors = Column(JSON, default=list)  # [{row: 1, error: "..."}]
        
        # Timestamps
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        completed_at = Column(DateTime, nullable=True)
    ```

2.  **Migration**: Generate Alembic migration.
3.  **Service Refactor**:
    -   Update `AnnotationImportService`.
    -   Implement `process_import_job` with chunking (BATCH_SIZE = 100).
    ```python
    async def process_import_job(self, job_id: str, file_path: str):
        """
        Background task to process the import.
        1. Read CSV in chunks (pd.read_csv(chunksize=...))
        2. Validate & Map to DB objects
        3. Bulk Insert/Update
        4. Update Job status & stats per chunk
        5. Handle exceptions & cleanup
        """
    ```
    -   Implement bulk DB logic.
4.  **API**: Update `backend/api/v1/annotations.py` to use `BackgroundTasks`.

### Phase 2: Frontend Implementation
1.  **Service**: Add methods to `EvaluationsService` (or new `ImportService`).
2.  **Dialog**: Build `AnnotationImportDialogComponent`.
3.  **Integration**: Hook up to `ProjectDetailComponent`.


## 5. Verification
-   **Unit Tests**: Test `process_import_job` logic with mock DB.
-   **Manual Test**:
    -   Upload valid file -> Verify success.
    -   Upload file with mixed errors -> Verify progress bar and error log.
    -   Upload large file -> Verify UI doesn't freeze.
