# Claude Code Instructions
## Environment Setup
**IMPORTANT**: Always use the `multiprompt-sandbox` conda environment for all Python operations.
```bash
conda activate multiprompt-sandbox
```
Before running any `pip install` commands, ensure this environment is activated.

## Project Structure
- `backend/` - FastAPI backend with Python
- `frontend/` - Angular frontend with TypeScript
- `infrastructure/` - Terraform/GCP configurations
- `docs/` - Project documentation
Files & folder structure is described in a project root file: folder_structure_with_descriptions.md

## Coding Standards

### Logging Standards (Enterprise-Grade)
We use **structlog** for structured, contextual logging.
1.  **Library:** Always import from `structlog`.
    ```python
    import structlog
    logger = structlog.get_logger(__name__)
    ```
2.  **Contextual Logging:** Do NOT put variables in the message string. Pass them as keyword arguments.
    *   ❌ **Bad:** `logger.info(f"Processing image {image_id} for job {job_id}")`
    *   ✅ **Good:** `logger.info("processing_image", image_id=image_id, job_id=job_id)`
    *   *Why?* This allows us to query logs by field (e.g., `jsonPayload.job_id="123"`) in Google Cloud Logging.
3.  **Binding Context:** For operations spanning multiple log lines, bind the context early.
    ```python
    log = logger.bind(job_id=job_id, user_id=user.id)
    log.info("job_started")
    try:
        ...
        log.info("job_completed")
    except Exception:
        log.exception("job_failed")
    ```

## Common Commands
### Backend Development
```bash
conda activate multiprompt-sandbox
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Database
```bash
docker-compose up -d db
```

### Frontend Development
```bash
cd frontend
npm install
npm start
```

## Google Cloud Project
- Project: `prompting-sandbox-mvp`
- Account: `rafalkawtradegpt@gmail.com`

## Infrastructure Deployment
**IMPORTANT**: Always use Terraform for GCP infrastructure provisioning. Do NOT use gcloud CLI for creating resources like Cloud SQL, VPC, etc.
```bash
cd infrastructure
terraform init
terraform plan
terraform apply
```

Important: for any database migration ALWAYS use Alembic
Your terminal is running on Windows
For every architectural decision taken create Git issue eg. [ADR-001] Background Job Infrastructure for Image Processing
