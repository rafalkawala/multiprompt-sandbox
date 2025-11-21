# Project State

> **Last Updated**: 2025-11-14
> **For**: AI Agents and New Developers
> **Purpose**: Single source of truth for current technical state

---

## What This Project Is

**MLLM Benchmarking Platform** - An enterprise-grade web application designed to systematically improve the accuracy of Multimodal Large Language Models (MLLMs) on proprietary image datasets from 80% to 95-98% through structured experimentation and benchmarking.

**Target Users**: Retail, CPG, Manufacturing, and E-commerce teams who need precision visual AI for tasks like planogram compliance, shelf audits, quality control, and product categorization.

---

## Current Technical State

### What's Actually Working (v0.1.0 - Foundation Phase)

#### Backend (FastAPI + Python 3.11)
- ✅ Basic FastAPI application structure (`backend/app/main.py`)
- ✅ Health check endpoints (`/health`, `/ready`)
- ✅ Image analysis endpoint (`POST /api/v1/images/analyze`) using Gemini Pro Vision
- ✅ CORS configuration for local development
- ✅ Global exception handling
- ✅ Pydantic settings management (`backend/app/core/config.py`)
- ✅ OpenAPI documentation at `/docs` and `/redoc`

#### Frontend (Angular 17 + TypeScript)
- ✅ Standalone component architecture
- ✅ Home dashboard with feature overview (`frontend/src/app/features/home/`)
- ✅ Material Design UI with GCP-like theme
- ✅ Responsive sidenav navigation
- ✅ Basic routing structure (`frontend/src/app/app.routes.ts`)

#### Infrastructure
- ✅ Docker setup for both frontend and backend
- ✅ Docker Compose for local development
- ✅ Kubernetes manifests with Kustomize (dev/prod overlays)
- ✅ GitHub Actions CI/CD pipeline (build, test, deploy to GKE)
- ✅ VS Code workspace with launch configurations

#### Documentation
- ✅ Comprehensive README with quick start
- ✅ Architecture documentation
- ✅ API documentation
- ✅ Deployment guides
- ✅ GitHub project setup documentation

### Known Issues / Disabled Features

#### LangChain Agents (Currently DISABLED)
- ⚠️ **Status**: Endpoint commented out in `backend/app/api/v1/__init__.py` (line ~23)
- ⚠️ **Reason**: Import error in `langchain_community.tools` package
- ⚠️ **Impact**: Cannot execute agent workflows
- ⚠️ **Code Location**:
  - Service: `backend/app/services/agent_service.py` (exists but not used)
  - Endpoint: `backend/app/api/v1/endpoints/agents.py` (exists but not routed)
  - Router: `backend/app/api/v1/__init__.py` (line 23 commented out)

#### No Database Persistence
- ❌ PostgreSQL not yet configured
- ❌ All data is ephemeral (lost on restart)
- ❌ No SQLAlchemy models or migrations

#### No Authentication
- ❌ No user registration/login
- ❌ No JWT tokens
- ❌ All endpoints are public

### Not Yet Implemented (MVP Features)

The following features are **documented** in the README and requirements but **not built**:

1. **Projects & Dataset Management**
   - Upload images (up to 500 per dataset)
   - Cloud Storage integration
   - Dataset organization

2. **Ground Truth Labeling Tool**
   - Labeling interface
   - Multiple question types
   - Annotation export

3. **Prompt Engineering Sandbox**
   - Rich text editor
   - Prompt chains
   - Version control

4. **Multi-Model Benchmarking**
   - Experiment execution
   - Batch processing
   - Cost tracking

5. **Accuracy & Scoring Engine**
   - Accuracy calculations
   - Confusion matrices
   - Metrics visualization

6. **Experiment Repository**
   - Persistent storage
   - Comparison tools
   - Export functionality

7. **Few-Shot Prompting**
   - Multimodal embeddings
   - Similar example identification

---

## Key File Locations

### Backend Entry Points

| File | Purpose | Status |
|------|---------|--------|
| `backend/app/main.py` | FastAPI application entry point | ✅ Working |
| `backend/app/api/v1/__init__.py` | API router configuration | ✅ Working (agents disabled) |
| `backend/app/core/config.py` | Configuration and settings | ✅ Working |

### Backend Services

| File | Purpose | Status |
|------|---------|--------|
| `backend/app/services/gemini_service.py` | Gemini Pro Vision integration | ✅ Working |
| `backend/app/services/agent_service.py` | LangChain agent service | ⚠️ Disabled |

### Backend API Endpoints

| File | Purpose | Status |
|------|---------|--------|
| `backend/app/api/v1/endpoints/images.py` | Image analysis endpoints | ✅ Working |
| `backend/app/api/v1/endpoints/agents.py` | Agent execution endpoints | ⚠️ Disabled |

### Frontend Entry Points

| File | Purpose | Status |
|------|---------|--------|
| `frontend/src/main.ts` | Angular bootstrap | ✅ Working |
| `frontend/src/app/app.component.ts` | Root component with navigation | ✅ Working |
| `frontend/src/app/app.routes.ts` | Routing configuration | ✅ Working |
| `frontend/src/app/app.config.ts` | Angular providers | ✅ Working |

### Frontend Features

| File | Purpose | Status |
|------|---------|--------|
| `frontend/src/app/features/home/` | Dashboard component | ✅ Working |

### Configuration Files

| File | Purpose | Status |
|------|---------|--------|
| `backend/.env.example` | Backend environment template | ✅ Current |
| `backend/requirements.txt` | Python dependencies | ✅ Current |
| `frontend/package.json` | npm dependencies | ✅ Current |
| `frontend/angular.json` | Angular CLI configuration | ✅ Current |
| `docker-compose.yaml` | Local dev environment | ✅ Working |
| `k8s/base/kustomization.yaml` | Kubernetes base config | ✅ Working |
| `.github/workflows/ci-cd.yaml` | CI/CD pipeline | ✅ Working |

### Documentation Files

| File | Purpose |
|------|---------|
| `README.md` | Main project documentation (START HERE) |
| `PROJECT_STATE.md` | This file - current state reference |
| `docs/architecture/README.md` | System architecture overview |
| `docs/api/README.md` | API endpoint documentation |
| `docs/deployment/README.md` | Deployment instructions |
| `docs/requirements/README.md` | Requirements and user stories |
| `docs/requirements/issues-summary.md` | GitHub issues to create |
| `docs/github-setup.md` | GitHub project setup |

---

## API Endpoints (Current)

### Working Endpoints

```
GET  /                                  - API info
GET  /health                            - Health check
GET  /ready                             - Kubernetes readiness probe
GET  /docs                              - Swagger UI
GET  /redoc                             - ReDoc API documentation

POST /api/v1/images/analyze             - Analyze image with Gemini
GET  /api/v1/images/health              - Image service health
```

### Disabled Endpoints

```
POST /api/v1/agents/execute             - Execute LangChain agent (DISABLED)
GET  /api/v1/agents/health              - Agent service health (DISABLED)
```

---

## Technology Stack (Actual)

### Frontend
- Angular 17+ (standalone components)
- TypeScript 5.x
- Angular Material 17+
- RxJS 7+
- SCSS for styling

### Backend
- Python 3.11+
- FastAPI 0.109+
- Uvicorn (ASGI server)
- Pydantic v2 (validation)
- Google Generative AI SDK (Gemini)
- LangChain (installed but not working)

### Infrastructure
- Docker & Docker Compose
- Kubernetes (GKE)
- GitHub Actions
- Google Cloud Platform

### Development Tools
- VS Code with configured workspace
- pytest (backend testing)
- Karma/Jasmine (frontend testing)
- Black, Flake8, mypy (Python linting)
- ESLint, Prettier (TypeScript linting)

---

## Quick Start Commands

### Local Development (Docker Compose)
```bash
# Start everything
docker-compose up

# Access:
# Frontend: http://localhost:4200
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Backend Only
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env  # Edit and add GEMINI_API_KEY
uvicorn app.main:app --reload
```

### Frontend Only
```bash
cd frontend
npm install
npm start
```

### Run Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

---

## Git Repository State

**Repository**: https://github.com/rafalkawala/multiprompt-sandbox.git
**Current Branch**: `main`
**Recent Commits**:
- d7c5039 - Add Angular Material with GCP-like design
- 8c01314 - Update README with actual product vision
- 8e8b722 - Add product requirements document

**Modified Files** (as of last check):
- `backend/app/api/v1/__init__.py` (agents disabled)
- `backend/app/main.py` (updated)
- `frontend/src/app/app.config.ts` (updated)

---

## Dependencies and External Services

### Required API Keys
- **GEMINI_API_KEY**: Required for image analysis (get from Google AI Studio)
- **GCP_PROJECT_ID**: Required for GCP services

### Optional (Not Yet Used)
- Claude API key (for multi-model benchmarking)
- PostgreSQL database (for persistence)
- Google Cloud Storage (for image storage)

### External Package Issues
- `langchain_community.tools` - Import error preventing agent functionality

---

## Development Priorities (Next Steps)

Based on MVP roadmap, the next implementation priorities are:

### Phase 1: Foundation (Weeks 1-2)
1. Fix LangChain agents endpoint or remove if not needed
2. Set up PostgreSQL database
3. Implement project and dataset management
4. Add image upload to Cloud Storage

### Phase 2: Core Features (Weeks 2-6)
5. Build ground truth labeling interface
6. Create prompt engineering sandbox
7. Implement multi-model benchmarking engine
8. Add accuracy scoring system

### Phase 3: Repository & Polish (Weeks 6-8)
9. Build experiment repository
10. Add comparison and analytics
11. Implement few-shot prompting
12. E2E testing and optimization

---

## Environment Variables

### Backend (`backend/.env`)
```env
GEMINI_API_KEY=<your_api_key>        # Required
GCP_PROJECT_ID=<your_project_id>     # Required
ENVIRONMENT=development               # Default: development
CORS_ORIGINS=http://localhost:4200   # Default: localhost:4200
```

### Frontend (`frontend/src/environments/environment.ts`)
```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1'
};
```

---

## Common Issues and Solutions

### Backend won't start
- **Check**: Python version is 3.11+
- **Check**: Virtual environment is activated
- **Check**: `.env` file exists with GEMINI_API_KEY
- **Solution**: `pip install -r requirements.txt`

### Frontend won't start
- **Check**: Node.js version is 18+
- **Check**: npm installed
- **Solution**: `rm -rf node_modules && npm install`

### Docker Compose fails
- **Check**: Docker Desktop is running
- **Check**: Ports 4200 and 8000 are available
- **Solution**: `docker-compose down && docker-compose up --build`

### Tests failing
- **Backend**: Check virtual environment has all dependencies
- **Frontend**: Check node_modules are up to date
- **Solution**: Reinstall dependencies

---

## For AI Agents

When working on this project:

1. **Start with this file** to understand current state
2. **Check README.md** for overall vision and features
3. **Look at specific docs** in `/docs` for detailed info
4. **Key entry points**:
   - Backend: `backend/app/main.py`
   - Frontend: `frontend/src/app/app.component.ts`
5. **Known blockers**: LangChain agents disabled, no database persistence
6. **What works**: Image analysis via Gemini, basic Angular UI
7. **What's planned**: Everything in "Not Yet Implemented" section above

When implementing new features:
- Backend endpoints go in `backend/app/api/v1/endpoints/`
- Services go in `backend/app/services/`
- Frontend components go in `frontend/src/app/features/`
- Always add tests in corresponding test directories
- Update this file when making significant changes

---

## Changelog

### 2025-11-14
- Created PROJECT_STATE.md as single source of truth
- Updated README with implementation status
- Documented LangChain agents as disabled
- Added key file locations and quick reference

### Earlier
- Initial project setup
- Angular 17 with Material Design
- FastAPI with Gemini integration
- Docker and Kubernetes configuration
- CI/CD pipeline setup
