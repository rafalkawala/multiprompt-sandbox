# MultiPromptSandbox

A professional full-stack application with Angular frontend, FastAPI backend, LangChain agents, and Gemini Pro image recognition, deployed on Google Kubernetes Engine.

## Architecture

```
Frontend (Angular) → Backend (FastAPI + LangChain) → Gemini Pro API
         ↓                      ↓
    Kubernetes (GKE)      Google Cloud Services
```

## Technology Stack

### Frontend
- Angular 17+
- TypeScript
- RxJS
- Material UI (optional)
- Karma/Jasmine (unit tests)
- Protractor/Cypress (e2e tests)

### Backend
- Python 3.10+
- FastAPI
- LangChain/LangGraph
- Gemini Pro API
- Pydantic
- pytest (unit & integration tests)

### Infrastructure
- Docker & Docker Compose
- Kubernetes (GKE)
- Google Artifact Registry
- GitHub Actions (CI/CD)
- Google Cloud Platform

## Project Structure

```
MultiPromptSandbox/
├── frontend/              # Angular application
├── backend/              # FastAPI application
├── k8s/                  # Kubernetes manifests
├── docs/                 # Documentation
├── scripts/              # Utility scripts
├── tests/                # Integration tests
└── .github/              # GitHub workflows
```

## Prerequisites

- Node.js 18+
- Python 3.10+
- Docker Desktop
- kubectl
- gcloud CLI
- Angular CLI (`npm install -g @angular/cli`)

## Getting Started

### Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd MultiPromptSandbox
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Start with Docker Compose:
```bash
docker-compose up
```

4. Access the application:
- Frontend: http://localhost:4200
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Development Without Docker

**Frontend:**
```bash
cd frontend
npm install
ng serve
```

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing

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
pytest tests/unit        # Unit tests only
pytest tests/integration # Integration tests
pytest --cov=app         # Coverage report
```

### Integration Tests
```bash
cd tests/integration
pytest
```

## Deployment

See [docs/deployment/README.md](docs/deployment/README.md) for detailed deployment instructions.

### Quick Deploy to GKE
```bash
# Build and push images
./scripts/gcp/build-and-push.sh

# Deploy to GKE
kubectl apply -k k8s/overlays/prod
```

## Documentation

- [Architecture](docs/architecture/README.md)
- [API Documentation](docs/api/README.md)
- [Requirements](docs/requirements/README.md)
- [Deployment Guide](docs/deployment/README.md)

## Contributing

1. Create a feature branch
2. Make your changes
3. Write/update tests
4. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions, please use the GitHub issue tracker.
