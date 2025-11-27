# Two-Phase Upload System Implementation Status

## Overview
Implementing scalable two-phase image upload system with Cloud Tasks for background processing.
- **GitHub Issue**: #32 (ADR for Cloud Tasks architecture)
- **Implementation Plan**: `.claude/plans/splendid-juggling-meteor.md`

## Completed ✅

### 1. Documentation
- ✅ Created GitHub issue #32 with architectural decision record
- ✅ Documented Cloud Tasks vs Redis/Celery comparison
- ✅ Cost analysis: $0.0008 for 2000 images vs $50-100/month for Redis

### 2. Database Schema (Migration: 640889d5a1e8)
**Files Modified**:
- `backend/models/project.py` - Added processing columns to Dataset model
- `backend/models/image.py` - Added processing columns to Image model

**Dataset Model - New Columns**:
```python
processing_status = Column(String, default="ready")  # ready, uploading, processing, completed, failed
processing_started_at = Column(DateTime, nullable=True)
processing_completed_at = Column(DateTime, nullable=True)
total_files = Column(Integer, default=0)
processed_files = Column(Integer, default=0)
failed_files = Column(Integer, default=0)
processing_errors = Column(JSON, nullable=True)
```

**Image Model - New Columns**:
```python
processing_status = Column(String, default="pending")  # pending, processing, completed, failed
processing_error = Column(Text, nullable=True)
```

**Migration File**: `backend/alembic/versions/640889d5a1e8_add_processing_status_columns.py`

### 3. Backend Services
**Files Created**:
- ✅ `backend/services/image_processing_service.py`
  - `ImageProcessingService` class with `process_dataset_images()` method
  - Downloads images from GCS, generates thumbnails in thread pool
  - Updates database with progress tracking
  - 5 concurrent thumbnail generations with semaphore

- ✅ `backend/services/cloud_tasks_service.py`
  - `CloudTasksService` class with `enqueue_dataset_processing()` method
  - Singleton pattern with `get_cloud_tasks_service()` factory
  - Enqueues HTTP tasks to call internal endpoint

### 4. Internal Task Endpoint
**Files Created**:
- ✅ `backend/api/v1/tasks.py`
  - POST `/api/v1/internal/tasks/process-dataset/{dataset_id}`
  - Protected endpoint (verifies X-CloudTasks-TaskName header)
  - Instantiates ImageProcessingService and processes dataset

**Files Modified**:
- ✅ `backend/api/v1/__init__.py` - Registered tasks router

## Remaining Work 🔨

### 5. Batch Upload Endpoint
**Priority**: HIGH (Next step)

**Files to Modify**:
- `backend/api/v1/datasets.py`

**Implementation**:
1. Add new endpoint: `POST /{project_id}/datasets/{dataset_id}/images/batch-upload`
2. Stream files directly to GCS (no BytesIO buffering)
3. Parallel upload with `asyncio.gather()` and `Semaphore(10)`
4. Create Image records with `processing_status='pending'`
5. Update Dataset: `processing_status='uploading'` → `'processing'`
6. Enqueue Cloud Tasks for background processing
7. Add progress status endpoint: `GET /{project_id}/datasets/{dataset_id}/processing-status`

**Key Changes**:
```python
# Remove file buffering
# OLD: file_bytes = await file.read()
# NEW: await storage.upload(file, storage_path)  # Stream directly

# Parallel upload
semaphore = asyncio.Semaphore(10)
results = await asyncio.gather(*[upload_single_file(f) for f in files])

# Enqueue background task
from services.cloud_tasks_service import get_cloud_tasks_service
tasks_service = get_cloud_tasks_service()
tasks_service.enqueue_dataset_processing(project_id, dataset_id)
```

### 6. Cloud Tasks Infrastructure
**Priority**: HIGH (Required for deployment)

**Files to Modify**:
- `infrastructure/main.tf`
- `backend/requirements.txt`
- `backend/core/config.py`
- `cloudbuild.yaml`

**Terraform Changes**:
```terraform
# Enable Cloud Tasks API
resource "google_project_service" "cloud_tasks" {
  service = "cloudtasks.googleapis.com"
}

# Create queue
resource "google_cloud_tasks_queue" "image_processing" {
  name     = "image-processing-queue"
  location = var.region

  rate_limits {
    max_concurrent_dispatches = 10
    max_dispatches_per_second = 5
  }

  retry_config {
    max_attempts = 3
    max_retry_duration = "3600s"
  }
}

# Grant IAM permissions
resource "google_cloud_tasks_queue_iam_member" "backend_enqueuer" {
  name = google_cloud_tasks_queue.image_processing.name
  location = var.region
  role = "roles/cloudtasks.enqueuer"
  member = "serviceAccount:${google_service_account.backend.email}"
}
```

**Requirements.txt**:
```
google-cloud-tasks==2.14.2
```

**Config.py**:
```python
REGION: str = "us-central1"
BACKEND_URL: str = ""  # Set via env var
```

**cloudbuild.yaml** (in deploy-backend step):
```yaml
echo "REGION: \"${_REGION}\"" >> deploy_env_vars.yaml
echo "BACKEND_URL: \"$$BACKEND_URL\"" >> deploy_env_vars.yaml
```

### 7. Frontend Progress UI
**Priority**: MEDIUM

**Files to Modify**:
- `frontend/src/app/core/services/projects.service.ts`
- `frontend/src/app/features/projects/project-detail.component.ts`
- `frontend/src/app/features/projects/project-detail.component.html`

**New Service Methods**:
```typescript
// Batch upload with progress
uploadImagesBatch(projectId: string, datasetId: string, files: File[]): Observable<{...}>

// Poll processing status
getProcessingStatus(projectId: string, datasetId: string): Observable<{
  status: string;
  progress_percent: number;
  ...}>
```

**Component Logic**:
```typescript
// Phase 1: Upload to GCS with progress bar
uploadFiles(datasetId: string, files: File[]) {
  this.uploadPhase.set('uploading');
  // Show upload progress

  // On complete, switch to Phase 2
  this.uploadPhase.set('processing');
  this.startProcessingStatusPolling(datasetId);
}

// Phase 2: Poll every 2 seconds
startProcessingStatusPolling(datasetId: string) {
  interval(2000).pipe(
    switchMap(() => this.projectsService.getProcessingStatus(...))
  ).subscribe(status => {
    // Update progress, check if completed/failed
  });
}
```

### 8. Testing & Deployment
**Priority**: HIGH (Final step)

**Test Plan**:
1. **Local Testing**:
   - Run migration: `alembic upgrade head`
   - Test internal endpoint with mock Cloud Tasks headers
   - Test batch upload with small dataset (10 images)

2. **Cloud SQL Migration**:
   - Migrations run automatically on Cloud Run startup (Dockerfile CMD)
   - Verify in Cloud Run logs

3. **Infrastructure Deployment**:
   ```bash
   cd infrastructure
   terraform plan
   terraform apply
   ```

4. **Backend Deployment**:
   - Commit changes
   - Push to trigger Cloud Build
   - Monitor deployment logs
   - Verify environment variables set

5. **End-to-End Testing**:
   - Upload 20-50 images to test dataset
   - Verify Phase 1 completes (files in GCS)
   - Verify Cloud Task enqueued
   - Verify Phase 2 processes (thumbnails generated)
   - Check dataset `processing_status` = 'completed'

6. **Load Testing** (Optional):
   - Upload 500-1000 images
   - Monitor Cloud Tasks queue depth
   - Check processing time
   - Verify no timeouts or connection pool issues

## Important Notes

### Current State
- **Migration created but NOT run**: Database schema unchanged in production
- **Services implemented**: Code ready but untested
- **No infrastructure**: Cloud Tasks queue doesn't exist yet
- **Frontend unchanged**: Still uses old synchronous upload

### Migration Strategy
Per plan:
1. Add new endpoints alongside existing upload (both work)
2. Deploy infrastructure (Cloud Tasks)
3. Deploy backend with new code
4. Update frontend to use batch upload
5. Deprecate old endpoint after testing

### Configuration Required
Environment variables needed:
- `REGION=us-central1` (in Cloud Run)
- `BACKEND_URL=https://multiprompt-backend-xxx.run.app` (in Cloud Run)
- `GCP_PROJECT_ID` (already set)

### Potential Issues to Watch
1. **Synchronous GCS calls**: Storage upload/download are marked async but use sync SDK
   - Current workaround: Already in async functions, should work
   - Future improvement: Use `asyncio.to_thread()` if needed

2. **Database sessions in async**: ImageProcessingService uses single session
   - May need session-per-image for better concurrency
   - Monitor for deadlocks

3. **Cloud Tasks authentication**: Internal endpoint protected by header check
   - OIDC token authentication configured in Cloud Tasks
   - Service account must have permission to invoke Cloud Run

## Next Session Checklist

When continuing implementation:

1. ✅ Read this status document
2. ✅ Review implementation plan: `.claude/plans/splendid-juggling-meteor.md`
3. ✅ Check GitHub issue #32 for context
4. ⬜ Implement batch upload endpoint in `datasets.py`
5. ⬜ Add `google-cloud-tasks` to requirements.txt
6. ⬜ Update `core/config.py` with REGION and BACKEND_URL
7. ⬜ Modify `infrastructure/main.tf` for Cloud Tasks
8. ⬜ Update `cloudbuild.yaml` with new env vars
9. ⬜ Frontend: Update `projects.service.ts`
10. ⬜ Frontend: Update `project-detail.component.ts`
11. ⬜ Test locally if possible
12. ⬜ Deploy infrastructure with Terraform
13. ⬜ Deploy backend and test end-to-end

## Files Changed So Far

**Modified**:
- `backend/models/project.py` (Dataset model)
- `backend/models/image.py` (Image model)
- `backend/api/v1/__init__.py` (router registration)

**Created**:
- `backend/alembic/versions/640889d5a1e8_add_processing_status_columns.py`
- `backend/services/image_processing_service.py`
- `backend/services/cloud_tasks_service.py`
- `backend/api/v1/tasks.py`

**No changes yet**:
- Infrastructure (Terraform, cloudbuild)
- Frontend
- Requirements.txt
- Config.py
- datasets.py (batch upload endpoint)
