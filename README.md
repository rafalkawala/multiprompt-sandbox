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
- **Kubernetes (GKE)** - Container orchestration
- **Docker** - Containerization
- **GitHub Actions** - CI/CD pipeline

## 📋 Prerequisites

- **Node.js 18+** and npm
- **Python 3.11+**
- **Docker Desktop**
- **kubectl** (Kubernetes CLI)
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

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture/README.md) | System architecture and component design |
| [API Documentation](docs/api/README.md) | REST API endpoints and examples |
| [Deployment Guide](docs/deployment/README.md) | GKE deployment instructions |
| [Requirements](docs/requirements/README.md) | Product requirements and use cases |
| [GitHub Setup](docs/github-setup.md) | Issue tracking and project management |

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

### Production Deployment to GKE

**1. Set up GCP Infrastructure:**
```bash
# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Create GKE cluster
gcloud container clusters create multiprompt-cluster \
    --num-nodes=3 \
    --machine-type=e2-medium \
    --zone=us-central1-a \
    --enable-autoscaling \
    --min-nodes=1 \
    --max-nodes=5
```

**2. Build and Push Docker Images:**
```bash
export GCP_PROJECT_ID=your-project-id
./scripts/gcp/build-and-push.sh
```

**3. Deploy to GKE:**
```bash
./scripts/gcp/deploy-to-gke.sh prod
```

**4. Configure GitHub Actions:**
Add secrets to your GitHub repository:
- `GCP_PROJECT_ID`
- `GCP_SA_KEY`
- `GEMINI_API_KEY`
- `GKE_CLUSTER_NAME`
- `GKE_ZONE`

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
