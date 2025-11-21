# MLLM Benchmarking Platform

> **A systematic experimentation platform for achieving 95-98% accuracy with Multimodal Large Language Models on enterprise image datasets.**

An enterprise-grade, deployable application that serves as a persistent repository and sandbox for validating MLLM performance on proprietary image datasets. Built for Retail, CPG, Manufacturing, and E-commerce teams who need precision visual AI.

[![GitHub Issues](https://img.shields.io/github/issues/rafalkawala/multiprompt-sandbox)](https://github.com/rafalkawala/multiprompt-sandbox/issues)
[![GitHub Stars](https://img.shields.io/github/stars/rafalkawala/multiprompt-sandbox)](https://github.com/rafalkawala/multiprompt-sandbox/stargazers)

## 🎯 The Problem

**Insufficient Out-of-the-Box Accuracy**: Standard models (Gemini, Claude) with simple prompts often fail to deliver the 95-98% accuracy required for business-critical tasks like:
- Store execution verification
- Object counting and naming
- Planogram compliance checking
- Out-of-stock validation
- Quality control inspections

**Lack of Systematic Testing**: Enterprises lack tools for:
- Measuring accuracy against ground truth
- Testing complex prompt chains and agents
- Comparing model versions (flash vs. pro)
- Storing and versioning experiments
- Few-shot prompting with proprietary data

## 💡 The Solution

A **deployable experimentation platform** that transforms how enterprises achieve required accuracy with MLLMs:

1. **📊 Ground Truth Labeling**: Fast human labeling tool for creating reference datasets (up to 500 images)
2. **🔧 Prompt Engineering Sandbox**: Design and version complex prompt chains and agentic workflows
3. **⚖️ Multi-Model Benchmarking**: Run experiments across Gemini Pro, Flash, Claude on labeled datasets
4. **📈 Accuracy Measurement**: Automatic comparison against ground truth with persistent metrics storage
5. **🎨 Few-Shot Prompting**: Automatic similar-example identification using multimodal embeddings
6. **📦 Experiment Repository**: Persistent storage of all experiments, prompts, and results

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Angular Frontend                           │
│  Projects → Datasets → Labeling → Prompts → Experiments      │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────┴─────────────────────────────────┐
│                    FastAPI Backend                            │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Project    │  │  Labeling    │  │  Experiment  │        │
│  │  Management │  │  Service     │  │  Engine      │        │
│  └─────────────┘  └──────────────┘  └──────┬───────┘        │
│                                             │                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────┴───────┐        │
│  │  Prompt     │  │  Accuracy    │  │  Multi-Model │        │
│  │  Manager    │  │  Scoring     │  │  Integration │        │
│  └─────────────┘  └──────────────┘  └──────┬───────┘        │
└────────────────────────────────────────────┼─────────────────┘
                                             │
        ┌────────────────────────────────────┼──────────────┐
        │                                    │              │
        ▼                                    ▼              ▼
   PostgreSQL                         Gemini Pro      Claude API
  (Cloud SQL)                         Gemini Flash
        │
        ▼
  Cloud Storage
  (Image Datasets)
```

## 🚀 Key Features

### 📁 Project & Dataset Management
- Create projects organized by business use case
- Upload up to 500 images per dataset
- Batch upload with progress tracking
- Cloud Storage integration for scalable image storage

### 🏷️ Ground Truth Labeling Tool
- Intuitive labeling interface with keyboard shortcuts
- Multiple question types: Yes/No, Multiple Choice, Text, Counting
- Image zoom and pan for detailed inspection
- Progress tracking and annotation export (JSON/CSV)
- Multi-user workflow support

### ✍️ Prompt Engineering Sandbox
- Rich text editor with variable support (`{{variable}}`)
- Multi-turn prompt chain builder
- Version control for prompts
- Test prompts on sample images
- Prompt template library

### ⚡ Multi-Model Benchmarking
- Run experiments across multiple models simultaneously
- Supported models: Gemini Pro, Gemini Flash, Claude (Anthropic)
- Batch processing with concurrent execution
- Real-time progress monitoring
- Cost estimation and tracking

### 📊 Accuracy & Scoring
- Automated accuracy calculation vs ground truth
- Per-question accuracy breakdown
- Confusion matrix visualization
- Precision, Recall, F1 scores
- Confidence distribution analysis

### 🔬 Experiment Repository
- Persistent storage of all experiments
- Side-by-side experiment comparison
- Trend analysis over time
- Export results (CSV, JSON, PDF)
- Shareable experiment reports

### 🎯 Few-Shot Prompting
- Automatic similar-example identification
- Multimodal embedding generation
- Configurable number of shots
- Improves accuracy for edge cases

## 🛠️ Technology Stack

### Frontend
- **Angular 17+** - Modern, component-based UI framework
- **TypeScript** - Type-safe development
- **RxJS** - Reactive programming for real-time updates
- **Angular Material** - Enterprise UI components

### Backend
- **Python 3.11+** - Modern Python with type hints
- **FastAPI** - High-performance async API framework
- **SQLAlchemy** - Database ORM with Alembic migrations
- **Pydantic** - Data validation and settings management

### AI/ML Integration
- **Gemini Pro & Flash** - Google's multimodal LLMs
- **Claude (Anthropic)** - Advanced reasoning capabilities
- **Vertex AI** - Embedding generation for few-shot prompting
- **LangChain** - Future agentic workflow support

### Infrastructure
- **PostgreSQL (Cloud SQL)** - Relational data storage
- **Google Cloud Storage** - Scalable image storage
- **Google Cloud Run** - Serverless container platform
- **Terraform** - Infrastructure as Code
- **Docker** - Containerization
- **GitHub Actions** - CI/CD pipeline

## 📋 Prerequisites

- **Node.js 18+** and npm
- **Python 3.11+**
- **Docker Desktop**
- **Terraform** (for infrastructure deployment)
- **gcloud CLI** (Google Cloud SDK)
- **GitHub CLI** (optional, for issue management)
- **Google Cloud Project** with billing enabled
- **Gemini API Key** (from Google AI Studio or Vertex AI)

## 🏃 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/rafalkawala/multiprompt-sandbox.git
cd multiprompt-sandbox
```

### 2. Set Up Environment Variables
```bash
# Copy example files
cp .env.example .env
cp backend/.env.example backend/.env

# Edit .env files with your API keys
# Required: GEMINI_API_KEY, GCP_PROJECT_ID
```

### 3. Install Dependencies

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

**Backend:**
```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
cd ..
```

### 4. Start Local Development

**Option A: Docker Compose (Recommended)**
```bash
docker-compose up
```

**Option B: Run Separately**
```bash
# Terminal 1 - Backend
cd backend
venv\Scripts\activate  # Windows
uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm start
```

### 5. Access the Application
- **Frontend**: http://localhost:4200
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## 🔧 Development Workflow

### Running Backend Only

```bash
cd backend

# Create virtual environment (first time only)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file (first time only)
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run the server
uvicorn app.main:app --reload

# Server runs at http://localhost:8000
```

### Running Frontend Only

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm start

# Frontend runs at http://localhost:4200
```

### Testing Backend Changes

```bash
cd backend
pytest                    # Run all tests
pytest tests/unit        # Run unit tests only
pytest tests/integration # Run integration tests
pytest --cov=app         # Run with coverage report

# Linting
flake8 app/
black app/ --check
mypy app/
```

### Testing Frontend Changes

```bash
cd frontend
npm run test              # Run unit tests (Karma/Jasmine)
npm run test:coverage     # Run with coverage
npm run lint              # Run ESLint
npm run e2e              # Run E2E tests (when implemented)
```

### Adding a New Backend Endpoint

1. **Create endpoint file** in `backend/app/api/v1/endpoints/`
   ```python
   # backend/app/api/v1/endpoints/my_feature.py
   from fastapi import APIRouter, HTTPException
   from pydantic import BaseModel

   router = APIRouter()

   class MyRequest(BaseModel):
       data: str

   @router.post("/my-endpoint")
   async def my_endpoint(request: MyRequest):
       return {"result": "success"}
   ```

2. **Register router** in `backend/app/api/v1/__init__.py`
   ```python
   from backend.app.api.v1.endpoints import my_feature

   api_router.include_router(
       my_feature.router,
       prefix="/my-feature",
       tags=["my-feature"]
   )
   ```

3. **Add tests** in `backend/tests/`
   ```python
   # backend/tests/test_my_feature.py
   from fastapi.testclient import TestClient
   from app.main import app

   client = TestClient(app)

   def test_my_endpoint():
       response = client.post("/api/v1/my-feature/my-endpoint",
                             json={"data": "test"})
       assert response.status_code == 200
   ```

### Adding a New Angular Component

```bash
cd frontend

# Generate a new component
ng generate component features/my-feature

# Generate a service
ng generate service services/my-service

# Generate a model
ng generate interface models/my-model
```

### Working with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Start services in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild specific service
docker-compose up --build backend
```

### Environment Variables

**Backend** (`backend/.env`):
```env
GEMINI_API_KEY=your_gemini_api_key_here
GCP_PROJECT_ID=your_gcp_project_id
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:4200,http://localhost:3000
```

**Frontend** (`frontend/src/environments/environment.ts`):
```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1'
};
```

### Common Development Tasks

**Reset backend virtual environment:**
```bash
cd backend
deactivate  # If venv is active
rm -rf venv  # or rmdir /s venv on Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Clear frontend node_modules:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Rebuild Docker images:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Debugging

**Backend debugging** (VS Code):
- Use the "Python: FastAPI" launch configuration in `.vscode/launch.json`
- Set breakpoints in Python files
- Press F5 to start debugging

**Frontend debugging** (VS Code):
- Use the "Angular: ng serve" launch configuration
- Open Chrome DevTools
- Source maps enabled for TypeScript debugging

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and commit
git add .
git commit -m "Add my feature"

# Push to GitHub
git push origin feature/my-feature

# Create pull request on GitHub
```

## 📍 Current Implementation Status

> **Last Updated**: 2025-11-14

This section helps you understand **what's actually working** vs. what's planned. Essential for AI agents and new developers.

### ✅ Currently Working

- **Backend API (FastAPI)**
  - Health check endpoints (`/health`, `/ready`)
  - Image analysis endpoint (`POST /api/v1/images/analyze`) using Gemini Pro Vision
  - CORS configuration for frontend integration
  - Global exception handling
  - OpenAPI documentation at `/docs`

- **Frontend (Angular 17)**
  - Home dashboard with feature overview
  - Material Design UI with GCP-like theme
  - Responsive sidenav navigation
  - Basic routing structure

- **Infrastructure**
  - Docker and Docker Compose setup
  - Terraform foundation for Cloud Run deployment
  - GitHub Actions CI/CD pipeline
  - VS Code workspace configuration

- **Documentation**
  - Comprehensive README and architecture docs
  - API documentation
  - Deployment guides
  - GitHub project setup

### ⚠️ Partially Working / Known Issues

- **LangChain Agents Endpoint**: Currently **DISABLED** due to import issues in `langchain_community.tools`
  - Endpoint exists at `POST /api/v1/agents/execute` but is commented out in router
  - Service code exists in `backend/app/services/agent_service.py`
  - Frontend placeholder exists but no integration

### ❌ Not Yet Implemented (MVP Roadmap)

The following features are documented and planned but **not yet built**:

- **Projects & Dataset Management**
  - Create/manage projects
  - Upload images to datasets (up to 500 images)
  - Cloud Storage integration

- **Ground Truth Labeling Tool**
  - Labeling interface with keyboard shortcuts
  - Multiple question types (Yes/No, Multiple Choice, Text, Counting)
  - Annotation export (JSON/CSV)

- **Prompt Engineering Sandbox**
  - Rich text editor with variable support
  - Multi-turn prompt chain builder
  - Version control for prompts

- **Multi-Model Benchmarking**
  - Experiment execution across models
  - Batch processing with progress tracking
  - Cost estimation

- **Accuracy & Scoring Engine**
  - Automated accuracy calculation
  - Confusion matrices
  - Precision/Recall/F1 scores

- **Experiment Repository**
  - Persistent storage (requires PostgreSQL)
  - Side-by-side comparison
  - Trend analysis and export

- **Few-Shot Prompting**
  - Multimodal embeddings
  - Similar-example identification

- **Database Persistence**
  - PostgreSQL setup (currently no persistence)
  - SQLAlchemy models
  - Alembic migrations

- **Authentication & Authorization**
  - User registration/login
  - JWT tokens
  - Role-based access control

For detailed implementation plan, see [MVP Roadmap](#-mvp-roadmap-2-months) and [GitHub Issues](https://github.com/rafalkawala/multiprompt-sandbox/issues).

---

## 📚 Codebase and Documentation Guide

> **For AI Agents & New Developers**: Start here to navigate the project efficiently.

### Quick Start for Understanding the Project

1. **First, read this README** - Understand the vision and current state
2. **Then read** [`PROJECT_STATE.md`](./PROJECT_STATE.md) - Current technical state and key file locations
3. **For architecture details** - See [`docs/architecture/README.md`](./docs/architecture/README.md)
4. **For API details** - See [`docs/api/README.md`](./docs/api/README.md)

### Codebase Structure

The repository is organized as a monorepo. Below is a guide to the key directories:

| Path | Description |
|---|---|
| [`/frontend`](./frontend/) | Contains the **Angular** frontend application. All UI components, services, and styles are located here. |
| [`/backend`](./backend/) | Contains the **Python FastAPI** backend application. This is where the core business logic, API endpoints, and database models reside. |
| [`/terraform`](./terraform/) | Contains **Terraform** configurations for deploying infrastructure to GCP (Cloud Run, Cloud SQL, Cloud Storage). |
| [`/scripts`](./scripts/) | A collection of automation scripts for local setup, deployment, and creating GitHub issues. |
| [`/docs`](./docs/) | Home to all official project documentation. |

### Key Files Quick Reference

**Essential entry points and configuration files:**

| File Path | Purpose | Status |
|-----------|---------|--------|
| [`backend/app/main.py`](./backend/app/main.py) | FastAPI application entry point | ✅ Working |
| [`backend/app/api/v1/__init__.py`](./backend/app/api/v1/__init__.py) | API router configuration | ✅ Working (agents disabled) |
| [`backend/app/services/gemini_service.py`](./backend/app/services/gemini_service.py) | Gemini Pro Vision integration | ✅ Working |
| [`backend/app/services/agent_service.py`](./backend/app/services/agent_service.py) | LangChain agent service | ⚠️ Disabled |
| [`backend/app/core/config.py`](./backend/app/core/config.py) | Backend configuration & settings | ✅ Working |
| [`backend/requirements.txt`](./backend/requirements.txt) | Python dependencies | ✅ Current |
| [`frontend/src/app/app.component.ts`](./frontend/src/app/app.component.ts) | Angular root component | ✅ Working |
| [`frontend/src/app/app.routes.ts`](./frontend/src/app/app.routes.ts) | Frontend routing configuration | ✅ Working |
| [`frontend/src/app/app.config.ts`](./frontend/src/app/app.config.ts) | Angular providers & config | ✅ Working |
| [`frontend/package.json`](./frontend/package.json) | npm dependencies | ✅ Current |
| [`terraform/main.tf`](./terraform/main.tf) | Terraform infrastructure config | ✅ Foundation |
| [`.github/workflows/ci-cd.yaml`](./.github/workflows/ci-cd.yaml) | CI/CD pipeline | ✅ Working |
| [`docker-compose.yaml`](./docker-compose.yaml) | Local development setup | ✅ Working |

### Official Documentation

For specific needs, refer to the detailed documentation files.

| Document | When to Use It |
|---|---|
| **[Project State](./PROJECT_STATE.md)** | **START HERE** for current technical state, known issues, and file locations. Essential for AI agents. |
| **[Architecture Overview](./docs/architecture/README.md)** | To understand the high-level system design, component interactions, and infrastructure layout. |
| **[API Reference](./docs/api/README.md)** | When you need to know about specific API endpoints, request/response formats, and authentication. |
| **[Deployment Guide](./docs/deployment/README.md)** | For step-by-step instructions on deploying the application to Cloud Run or a local environment. |
| **[Project Requirements](./docs/requirements/README.md)** | To understand the project's goals, user stories, epics, and functional requirements. Start here to see what we are building. |
| **[GitHub Setup](./docs/github-setup.md)** | For guidelines on our GitHub workflow, including how to create issues and manage project boards. |
| **[Issues Summary](./docs/requirements/issues-summary.md)** | A quick-start document that lists all initial epics and tasks to be created on GitHub. Use this to populate a new project board. |

## 🎯 MVP Roadmap (2 Months)

**Week 1-2: Foundation**
- [ ] Project and dataset management
- [ ] Image upload and Cloud Storage integration
- [ ] PostgreSQL database setup

**Week 2-3: Labeling**
- [ ] Ground truth labeling interface
- [ ] Question management
- [ ] Annotation storage and export

**Week 3-4: Prompt Engineering**
- [ ] Prompt template editor
- [ ] Prompt chain builder
- [ ] Prompt versioning

**Week 4-6: Benchmarking**
- [ ] Multi-model integration (Gemini, Claude)
- [ ] Experiment execution engine
- [ ] Batch processing with progress tracking

**Week 5-6: Accuracy & Scoring**
- [ ] Accuracy calculation engine
- [ ] Confusion matrix generation
- [ ] Results visualization

**Week 6-7: Dashboard**
- [ ] Experiment history and comparison
- [ ] Trend analysis
- [ ] Export functionality

**Week 7-8: Polish & Testing**
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Documentation completion

See [GitHub Issues](https://github.com/rafalkawala/multiprompt-sandbox/issues) for detailed task breakdown.

## 🧪 Testing

### Frontend Tests
```bash
cd frontend
npm run test              # Unit tests
npm run test:coverage     # Coverage report
npm run e2e              # E2E tests
```

### Backend Tests
```bash
cd backend
pytest                    # All tests
pytest tests/unit        # Unit tests
pytest tests/integration # Integration tests
pytest --cov=app         # Coverage report
```

## 🚀 Deployment

### Local Development
Use Docker Compose (see Quick Start above)

### Production Deployment to Cloud Run

**1. Set up Terraform variables:**
```bash
cd terraform

# Create terraform.tfvars with your values
cat > terraform.tfvars << EOF
gcp_project_id      = "your-project-id"
gcp_project_name    = "MLLM Benchmarking Platform"
gcp_billing_account = "your-billing-account-id"
gcp_region          = "us-central1"
EOF
```

**2. Initialize and apply Terraform:**
```bash
# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply infrastructure
terraform apply
```

**3. Build and deploy services:**
```bash
# Build and push Docker images
export GCP_PROJECT_ID=your-project-id
./scripts/gcp/build-and-push.sh

# Deploy to Cloud Run (uses Terraform outputs)
./scripts/gcp/deploy-to-cloud-run.sh
```

**4. Configure GitHub Actions:**
Add secrets to your GitHub repository:
- `GCP_PROJECT_ID`
- `GCP_SA_KEY`
- `GEMINI_API_KEY`

See [Deployment Guide](docs/deployment/README.md) for detailed instructions.

## 🎯 Target Use Cases

### Retail & CPG
- **Planogram Compliance**: Verify product placement matches planograms
- **Shelf Audits**: Count products, check for out-of-stocks
- **Store Execution**: Validate promotional displays and signage
- **Quality Control**: Inspect product condition and packaging

### Manufacturing
- **Visual Inspection**: Detect defects and anomalies
- **Assembly Verification**: Ensure correct component placement
- **Safety Compliance**: Check PPE and safety equipment usage

### E-commerce
- **Product Categorization**: Classify products from images
- **Content Moderation**: Validate user-generated images
- **Inventory Management**: Track stock levels from photos

## 🏆 Competitive Advantages

| Feature | Generic MLOps Platforms | In-House Scripts | **MLLM Benchmarking Platform** |
|---------|------------------------|------------------|-------------------------------|
| MLLM Specialization | ❌ | ❌ | ✅ |
| Built-in Labeling Tool | ❌ | ❌ | ✅ |
| Persistent Experiments | ⚠️ | ❌ | ✅ |
| Prompt Chain Builder | ❌ | ❌ | ✅ |
| Multi-Model Comparison | ⚠️ | ⚠️ | ✅ |
| Self-Hosted Deployment | ⚠️ | ✅ | ✅ |
| Few-Shot Prompting | ❌ | ❌ | ✅ |
| Enterprise Ready | ✅ | ❌ | ✅ |

## 👥 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write/update tests
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- **Issues**: [GitHub Issues](https://github.com/rafalkawala/multiprompt-sandbox/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rafalkawala/multiprompt-sandbox/discussions)
- **Email**: support@multiprompt.dev (coming soon)

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Angular](https://angular.io/) - Platform for building web applications
- [Google Gemini](https://deepmind.google/technologies/gemini/) - Multimodal AI models
- [Anthropic Claude](https://www.anthropic.com/claude) - Advanced AI assistant
- [LangChain](https://www.langchain.com/) - Building applications with LLMs

---

**Built by AI engineers, for AI engineers** 🚀

*Transform your visual AI from 80% accuracy to 95-98% with systematic experimentation.*
