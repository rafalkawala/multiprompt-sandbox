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

The Terraform configuration includes:
- Cloud SQL with private IP (no public IP)
- VPC networking
- Secret Manager
- Cloud Run services
- All required APIs

Important: for any database migration ALWAYS use Alembic

Your terminal is running on Windows

For every architectural decision taken create Git issue eg. [ADR-001] Background Job Infrastructure for Image Processing