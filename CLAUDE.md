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
