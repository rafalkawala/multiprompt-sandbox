# Architecture Documentation

> **Last Updated**: 2025-11-14

## System Overview

**MLLM Benchmarking Platform** is a full-stack enterprise application designed to systematically improve the accuracy of Multimodal Large Language Models (MLLMs) on proprietary image datasets through structured experimentation and benchmarking.

### Technology Stack

- **Frontend**: Angular 17+ with TypeScript and Material Design
- **Backend**: Python 3.11+ FastAPI with async/await
- **AI Services**: Google Gemini Pro/Flash, Anthropic Claude (planned)
- **Database**: PostgreSQL on Cloud SQL (planned)
- **Storage**: Google Cloud Storage for images (planned)
- **Infrastructure**: Google Cloud Run (serverless) with Terraform

### Current Implementation Status

**Working**: Image analysis with Gemini Pro Vision, basic Angular dashboard, Docker setup
**Disabled**: LangChain agents (import issues)
**Planned**: Full MLLM benchmarking features (see MVP roadmap)

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         Users                                 │
│   (Retail, CPG, Manufacturing, E-commerce Teams)             │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              Google Cloud Load Balancer (Ingress)            │
│              Path-based routing: /api/* → Backend            │
│                                  /* → Frontend               │
└────────────────────────┬─────────────────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
┌──────────────────────┐    ┌──────────────────────────────────┐
│   Frontend Pods      │    │      Backend Pods                │
│   (Angular 17)       │    │      (FastAPI)                   │
│                      │    │                                  │
│   - Nginx            │◄───┤   - REST API                     │
│   - Static Assets    │    │   - Image Analysis Service       │
│   - Material UI      │    │   - Benchmarking Engine (future) │
│                      │    │   - Accuracy Scoring (future)    │
└──────────────────────┘    └────────┬─────────────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
   │  PostgreSQL     │   │  Cloud Storage  │   │  AI Services    │
   │  (Cloud SQL)    │   │  (Images)       │   │                 │
   │                 │   │                 │   │  - Gemini Pro   │
   │  - Projects     │   │  - Datasets     │   │  - Gemini Flash │
   │  - Experiments  │   │  - Annotations  │   │  - Claude       │
   │  - Results      │   │  - Exports      │   │  - Vertex AI    │
   │  - Users        │   │                 │   │    Embeddings   │
   └─────────────────┘   └─────────────────┘   └─────────────────┘
         (Planned)            (Planned)              (Partial)
```

## Component Architecture

### Frontend (Angular)

**Current Structure:**
```
src/
├── app/
│   ├── features/          # Feature modules
│   │   └── home/          # ✅ Dashboard (implemented)
│   ├── app.component.ts   # ✅ Root with sidenav navigation
│   ├── app.routes.ts      # ✅ Routing configuration
│   └── app.config.ts      # ✅ Angular providers
```

**Planned Structure (MVP):**
```
src/
├── app/
│   ├── core/              # Singleton services, guards
│   │   ├── auth/          # Authentication service
│   │   └── api/           # HTTP client services
│   ├── shared/            # Shared components, pipes, directives
│   │   ├── components/    # Reusable UI components
│   │   └── models/        # TypeScript interfaces
│   ├── features/
│   │   ├── home/          # ✅ Dashboard
│   │   ├── projects/      # ❌ Project management
│   │   ├── datasets/      # ❌ Dataset upload & management
│   │   ├── labeling/      # ❌ Ground truth labeling tool
│   │   ├── prompts/       # ❌ Prompt engineering sandbox
│   │   ├── experiments/   # ❌ Benchmark execution
│   │   └── results/       # ❌ Accuracy & analytics
│   └── environments/      # ✅ Environment configs
```

**Key Features:**
- Standalone components (Angular 17+)
- Lazy loading for feature modules
- RxJS for reactive state management
- Material Design UI components
- Responsive layout with sidenav

### Backend (FastAPI)

**Current Structure:**
```
app/
├── api/
│   └── v1/
│       ├── __init__.py           # ✅ API router
│       └── endpoints/
│           ├── images.py         # ✅ Image analysis
│           └── agents.py         # ⚠️ Disabled
├── core/
│   └── config.py                 # ✅ Settings
├── services/
│   ├── gemini_service.py         # ✅ Gemini integration
│   └── agent_service.py          # ⚠️ Disabled
└── main.py                       # ✅ FastAPI app entry
```

**Planned Structure (MVP):**
```
app/
├── api/
│   └── v1/
│       └── endpoints/
│           ├── images.py         # ✅ Image analysis
│           ├── projects.py       # ❌ Project CRUD
│           ├── datasets.py       # ❌ Dataset management
│           ├── annotations.py    # ❌ Ground truth labels
│           ├── prompts.py        # ❌ Prompt templates
│           ├── experiments.py    # ❌ Benchmark execution
│           └── results.py        # ❌ Accuracy calculations
├── core/
│   ├── config.py                 # ✅ Settings
│   ├── security.py               # ❌ Auth & JWT
│   └── database.py               # ❌ DB connection
├── models/                       # ❌ SQLAlchemy models
│   ├── project.py
│   ├── dataset.py
│   ├── experiment.py
│   └── user.py
├── schemas/                      # Pydantic request/response
│   ├── project.py
│   ├── experiment.py
│   └── accuracy.py
└── services/
    ├── gemini_service.py         # ✅ Gemini Pro/Flash
    ├── claude_service.py         # ❌ Claude integration
    ├── storage_service.py        # ❌ Cloud Storage
    ├── embedding_service.py      # ❌ Vertex AI embeddings
    ├── accuracy_service.py       # ❌ Scoring engine
    └── experiment_service.py     # ❌ Benchmark orchestration
```

**Key Features:**
- Async/await for I/O operations
- Pydantic v2 for data validation
- Dependency injection
- OpenAPI documentation at `/docs`
- Global exception handling

### Database Schema (Planned)

**PostgreSQL on Cloud SQL:**

```sql
-- Users (Google OAuth2)
users
  - id (UUID, PK)
  - email (VARCHAR, UNIQUE, NOT NULL)
  - name (VARCHAR)
  - picture_url (VARCHAR)
  - google_id (VARCHAR, UNIQUE)
  - created_at (TIMESTAMP)
  - last_login_at (TIMESTAMP)

-- Projects with 1:1 Question relationship
projects
  - id (UUID, PK)
  - name (VARCHAR, NOT NULL)
  - description (TEXT)
  - question_text (VARCHAR, NOT NULL)  -- The KEY question for this project
  - question_type (ENUM: binary, multiple_choice, text, count)
  - question_options (JSONB, NULLABLE)  -- For multiple choice
  - created_by (FK → users)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)

-- Datasets contain images
datasets
  - id (UUID, PK)
  - project_id (FK → projects)
  - name (VARCHAR, NOT NULL)
  - created_by (FK → users)
  - created_at (TIMESTAMP)

-- Images in datasets
images
  - id (UUID, PK)
  - dataset_id (FK → datasets)
  - filename (VARCHAR, NOT NULL)
  - storage_path (VARCHAR, NOT NULL)
  - file_size (INTEGER)
  - uploaded_by (FK → users)
  - uploaded_at (TIMESTAMP)

-- Ground truth annotations (one per image)
annotations
  - id (UUID, PK)
  - image_id (FK → images, UNIQUE)  -- 1:1 with image
  - answer_value (JSONB)  -- true/false, "text", 5, "option_id"
  - is_skipped (BOOLEAN, DEFAULT false)
  - is_flagged (BOOLEAN, DEFAULT false)
  - flag_reason (TEXT, NULLABLE)
  - annotator_id (FK → users)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)

-- Model Registry (App-level, admin-managed)
model_registry
  - id (UUID, PK)
  - provider (VARCHAR) -- 'Google', 'Anthropic'
  - model_name (VARCHAR) -- 'gemini-1.5-pro', 'claude-3-sonnet'
  - display_name (VARCHAR) -- 'Gemini 1.5 Pro'
  - api_endpoint (VARCHAR)
  - default_config (JSONB)
  - rate_limit_rpm (INTEGER)
  - cost_per_1k_tokens (DECIMAL)
  - is_active (BOOLEAN)
  - created_at (TIMESTAMP)

-- Project Models (user-configured API keys)
project_models
  - id (UUID, PK)
  - project_id (FK → projects)
  - model_registry_id (FK → model_registry)
  - api_key_encrypted (BYTEA) -- Cloud KMS or AES-256
  - custom_config (JSONB)
  - is_active (BOOLEAN)
  - created_by (FK → users)
  - created_at (TIMESTAMP)

-- Experiments (link model to project)
experiments
  - id (UUID, PK)
  - project_id (FK → projects)
  - project_model_id (FK → project_models)
  - name (VARCHAR)
  - description (TEXT)
  - created_by (FK → users)
  - created_at (TIMESTAMP)

-- Experiment Runs (execution records)
experiment_runs
  - id (UUID, PK)
  - experiment_id (FK → experiments)
  - dataset_id (FK → datasets)
  - status (ENUM: pending, running, completed, failed)
  - total_images (INTEGER)
  - processed_images (INTEGER)
  - successful_predictions (INTEGER)
  - failed_predictions (INTEGER)
  - accuracy_score (FLOAT)
  - estimated_cost (DECIMAL)
  - actual_cost (DECIMAL)
  - error_message (TEXT)
  - started_at (TIMESTAMP)
  - completed_at (TIMESTAMP)

-- Predictions (per-image results)
predictions
  - id (UUID, PK)
  - experiment_run_id (FK → experiment_runs)
  - image_id (FK → images)
  - predicted_value (JSONB)
  - ground_truth_value (JSONB)
  - is_correct (BOOLEAN)
  - confidence (FLOAT)
  - latency_ms (INTEGER)
  - tokens_used (INTEGER)
  - error_message (TEXT)
  - created_at (TIMESTAMP)
```

### AI Service Integration

#### Gemini Pro Vision (Currently Working)

```python
Image Analysis Flow:
1. User uploads image via frontend
2. FastAPI receives multipart/form-data
3. Validate format (JPEG, PNG, GIF, WebP) & size (<10MB)
4. Send to Gemini Pro Vision API
5. Receive analysis (description, labels)
6. Return structured JSON response
7. Display results in frontend
```

**Endpoint**: `POST /api/v1/images/analyze`
**File**: `backend/app/services/gemini_service.py`
**Status**: ✅ Working

#### Multi-Model Benchmarking (Planned)

```python
Experiment Execution Flow:
1. User creates experiment (dataset + prompt + models)
2. System queues batch processing
3. For each image in dataset:
   a. Load image from Cloud Storage
   b. Apply prompt template
   c. Send to selected models (Gemini Pro/Flash, Claude)
   d. Collect predictions
   e. Compare against ground truth
   f. Calculate accuracy metrics
4. Aggregate results and store in database
5. Generate confusion matrix and visualizations
6. Display comparison dashboard
```

**Models Planned**:
- Google Gemini Pro (high quality)
- Google Gemini Flash (speed optimized)
- Anthropic Claude (advanced reasoning)

#### Few-Shot Prompting (Planned)

```python
Similar Example Flow:
1. User enables few-shot mode for experiment
2. System generates multimodal embeddings for all dataset images
3. For each test image:
   a. Generate embedding via Vertex AI
   b. Find K most similar images (cosine similarity)
   c. Retrieve ground truth for similar images
   d. Inject examples into prompt template
   e. Send enriched prompt to model
4. Compare accuracy: zero-shot vs few-shot
```

## Data Flow

### Current: Image Analysis
```
User → Frontend Upload
     → Backend API (/api/v1/images/analyze)
     → Gemini Pro Vision
     → Backend (format response)
     → Frontend (display results)
```

### Planned: Complete Benchmarking Workflow

```
1. Project Setup:
   User → Create Project → PostgreSQL

2. Dataset Upload:
   User → Upload Images → Cloud Storage → Update DB

3. Ground Truth Labeling:
   User → Labeling Interface → Annotations → PostgreSQL

4. Prompt Design:
   User → Prompt Editor → Save Template → PostgreSQL

5. Experiment Execution:
   User → Configure Experiment → Queue Job
       → Batch Processor:
           - Load images from GCS
           - Apply prompts
           - Call Gemini/Claude APIs
           - Store predictions
       → Calculate Accuracy
       → Store Results → PostgreSQL

6. Results Analysis:
   User → Dashboard → Fetch Metrics → Display Charts
       → Compare Experiments → Export Reports
```

## Security Considerations

### Currently Implemented
1. **CORS Configuration**
   - Configured in `backend/app/main.py`
   - Allows localhost origins for development
   - Will be restricted to specific domains in production

2. **Input Validation**
   - File type validation (JPEG, PNG, GIF, WebP only)
   - File size limits (10MB max)
   - Pydantic validation for all API requests

3. **API Key Management**
   - Gemini API key stored in environment variables
   - Not committed to version control
   - Google Secret Manager for production

### Planned Security Features

1. **Authentication & Authorization**
   - **Google OAuth2** as primary authentication (Gmail/Google accounts)
   - JWT tokens for API session management
   - Role-based access control (RBAC):
     - Admin: Full access
     - User: Project owner access
     - Viewer: Read-only access
   - API key authentication for programmatic access (future)

   **Environment-specific OAuth configuration via Terraform variables:**
   ```yaml
   # DEV
   GOOGLE_OAUTH_REDIRECT_URI: http://localhost:4200/auth/callback

   # UAT
   GOOGLE_OAUTH_REDIRECT_URI: https://uat.multiprompt.dev/auth/callback

   # PROD
   GOOGLE_OAUTH_REDIRECT_URI: https://multiprompt.dev/auth/callback
   ```

2. **Data Protection**
   - Encrypted database connections (Cloud SQL)
   - Encrypted storage (Cloud Storage with encryption at rest)
   - HTTPS enforced via Cloud Run
   - Sensitive data redaction in logs

3. **API Security**
   - Rate limiting per user/IP
   - Request size limits
   - CSRF protection
   - SQL injection prevention (SQLAlchemy ORM)
   - XSS protection (Angular sanitization)

4. **Image Security**
   - Virus scanning for uploaded images
   - Content moderation
   - Image metadata stripping
   - Signed URLs for Cloud Storage access

5. **Audit Logging**
   - User action tracking
   - API access logs
   - Change history for experiments
   - Compliance reporting

## Scalability

### Current Setup
- **Docker Compose**: Single-instance local development
- **Cloud Run**: Serverless auto-scaling deployment
- **Terraform**: Infrastructure as Code for all environments

### Scalability Strategy

1. **Horizontal Scaling**
   - Frontend: Stateless, Cloud Run auto-scales to N instances
   - Backend: Stateless API, Cloud Run auto-scales to N instances
   - Built-in load balancing via Cloud Run
   - Session affinity not required

2. **Auto-scaling**
   - Cloud Run automatic scaling based on:
     - Concurrent requests
     - CPU utilization
     - Min/max instances configurable per service
   - Scale to zero when idle (cost optimization)

3. **Database Scalability**
   - Cloud SQL with read replicas
   - Connection pooling (SQLAlchemy)
   - Query optimization and indexing
   - Caching layer (Redis planned)

4. **Storage Scalability**
   - Google Cloud Storage (virtually unlimited)
   - CDN for image delivery
   - Lazy loading and pagination

5. **AI Service Rate Limits**
   - Quota management for Gemini API
   - Request queuing for batch processing
   - Fallback to alternative models
   - Circuit breaker pattern

6. **Performance Optimization**
   - Redis caching for:
     - Frequently accessed experiments
     - User sessions
     - API responses
   - Database query optimization
   - Image compression and resizing
   - Frontend code splitting and lazy loading

## Monitoring & Logging

### Planned Monitoring Stack

1. **Application Monitoring**
   - Prometheus for metrics collection
   - Grafana for visualization
   - Dashboards for:
     - Request latency
     - Error rates
     - API usage
     - Model performance

2. **Logging**
   - Structured logging (JSON format)
   - Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
   - Google Cloud Logging integration
   - Log aggregation and search

3. **Error Tracking**
   - Sentry or Cloud Error Reporting
   - Automatic error grouping
   - Stack trace collection
   - User impact analysis

4. **Distributed Tracing**
   - OpenTelemetry instrumentation
   - Request tracing across services
   - Performance bottleneck identification

5. **Custom Metrics**
   - Experiment execution time
   - Model accuracy trends
   - User engagement metrics
   - Cost per experiment

6. **Alerts**
   - High error rate
   - API latency exceeds SLA
   - Failed experiments
   - Resource exhaustion

## Technology Stack Summary

| Layer | Technology | Status |
|-------|------------|--------|
| **Frontend** | Angular 17, TypeScript, Material Design | ✅ Working |
| **Backend** | Python 3.11, FastAPI, Uvicorn | ✅ Working |
| **AI Models** | Google Gemini Pro/Flash | ✅ Partial |
| | Anthropic Claude | ❌ Planned |
| | Vertex AI Embeddings | ❌ Planned |
| **Database** | PostgreSQL (Cloud SQL) | ❌ Planned |
| **Storage** | Google Cloud Storage | ❌ Planned |
| **Caching** | Redis | ❌ Planned |
| **Container** | Docker | ✅ Working |
| **Orchestration** | Cloud Run (serverless) | ❌ Planned |
| **Infrastructure** | Terraform | ✅ Foundation |
| **CI/CD** | GitHub Actions | ✅ Working |
| **Monitoring** | Cloud Monitoring | ❌ Planned |
| **Logging** | Cloud Logging | ❌ Planned |
| **Cloud Platform** | Google Cloud Platform | ✅ Configured |

## Deployment Architecture

### Development Environment
```
Docker Compose
├── Frontend container (localhost:4200)
├── Backend container (localhost:8000)
└── Shared network
```

### Production Environment (Cloud Run)
```
Google Cloud Run (Serverless)
├── Frontend Service
│   ├── Nginx + Angular build
│   ├── Auto-scaling (0 to N instances)
│   ├── Custom domain with SSL
│   └── CDN via Cloud CDN (optional)
├── Backend Service
│   ├── FastAPI application
│   ├── Auto-scaling (0 to N instances)
│   ├── Serverless VPC Connector
│   └── Health checks configured
└── Managed Services
    ├── Cloud SQL (PostgreSQL)
    ├── Cloud Storage (Images)
    ├── Secret Manager (API keys)
    └── Artifact Registry (Docker images)

Infrastructure managed by Terraform:
├── infrastructure/main.tf
├── infrastructure/variables.tf
└── Workspaces: dev, staging, prod
```

## MVP Implementation Roadmap

See [README.md](../../README.md#-mvp-roadmap-2-months) for detailed 8-week implementation plan.

**Phase 1** (Weeks 1-2): Foundation - Projects, Datasets, Database
**Phase 2** (Weeks 2-6): Core Features - Labeling, Prompts, Benchmarking
**Phase 3** (Weeks 6-8): Analytics & Polish - Results, Comparison, Testing

## Future Enhancements (Post-MVP)

1. **Advanced Features**
   - Multi-language support
   - Custom model fine-tuning
   - Automated prompt optimization
   - A/B testing for prompts

2. **Enterprise Features**
   - SSO integration (SAML, LDAP)
   - Advanced RBAC
   - Multi-tenancy support
   - Audit compliance reports

3. **Performance**
   - WebSocket for real-time updates
   - GraphQL API option
   - Edge caching (Cloudflare)
   - Image preprocessing pipeline

4. **Integration**
   - REST API for external systems
   - Webhook notifications
   - Slack/Teams integration
   - Export to data warehouses

5. **AI Capabilities**
   - Active learning loops
   - Confidence calibration
   - Explainability features
   - Model ensembling
