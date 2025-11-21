# GitHub Issues Summary

This document provides a complete list of all initial issues to create for the MultiPrompt Sandbox project.

## Quick Start

### Option 1: Using GitHub CLI (Automated)

1. **Install GitHub CLI**: https://cli.github.com/
2. **Authenticate**: `gh auth login`
3. **Run the script**:
   ```bash
   # Windows
   cd C:\Users\rafal\Projects\MultiPromptSandbox
   scripts\github\create-issues.bat

   # Linux/Mac
   cd MultiPromptSandbox
   chmod +x scripts/github/create-issues.sh
   ./scripts/github/create-issues.sh
   ```

### Option 2: Manual Creation

Copy the issues below and create them manually on GitHub.

---

## Epics (7 total)

### Epic 1: Infrastructure and DevOps Setup
**Labels**: `epic`, `infrastructure`, `priority:high`

**Description**:
Set up complete infrastructure for development, testing, and deployment to GKE.

**Tasks**:
- Configure GCP project and enable APIs
- Create GKE cluster with autoscaling
- Set up Artifact Registry for Docker images
- Configure GitHub Actions secrets
- Set up Google Cloud secrets for API keys
- Create separate dev/staging/prod environments
- Configure monitoring and logging

**Success Criteria**:
- CI/CD pipeline successfully deploys to GKE
- Automated testing runs on every PR
- Secrets are properly managed
- Monitoring is in place

**Timeline**: 2-3 weeks

---

### Epic 2: Image Analysis with Gemini Pro Vision
**Labels**: `epic`, `frontend`, `backend`, `priority:high`

**Description**:
Implement complete image analysis functionality using Gemini Pro Vision API.

**User Story**:
As a user, I want to upload images and receive AI-powered analysis including descriptions, object detection, and labels.

**Tasks**:
- Create image upload component in Angular
- Implement drag-and-drop functionality
- Add image preview before upload
- Create Gemini service integration
- Handle multiple image formats
- Display analysis results with labels
- Add export functionality for results
- Implement error handling
- Add loading states
- Write unit and integration tests

**Success Criteria**:
- Users can upload images (JPEG, PNG, GIF, WebP)
- Analysis results are accurate
- Max file size: 10MB
- Response time < 5 seconds
- Mobile responsive

**API Endpoints**: `POST /api/v1/images/analyze`

**Timeline**: 2-3 weeks

---

### Epic 3: LangChain Agent Integration
**Labels**: `epic`, `backend`, `frontend`, `priority:high`

**Description**:
Build an intelligent agent system using LangChain and Gemini Pro for multi-step task execution.

**User Story**:
As a user, I want to interact with an AI agent that can break down complex tasks, use tools, and provide step-by-step reasoning.

**Tasks**:
- Design agent architecture
- Implement core LangChain agent with Gemini
- Create custom tools (search, calculator, etc.)
- Add tool for image analysis integration
- Create chat interface in Angular
- Implement streaming responses
- Add conversation history
- Create agent execution visualization
- Implement context management
- Add agent settings configuration
- Write comprehensive tests

**Success Criteria**:
- Agent can execute multi-step tasks
- Tools work correctly
- Clear visualization of agent thinking
- Conversation context is maintained
- Streaming works smoothly

**API Endpoints**: `POST /api/v1/agents/execute`

**Timeline**: 3-4 weeks

---

### Epic 4: User Authentication and Authorization
**Labels**: `epic`, `backend`, `frontend`, `priority:medium`

**Description**:
Implement secure user authentication and role-based access control.

**User Story**:
As a user, I want to securely log in and have my data protected with proper authorization.

**Tasks**:
- Design authentication flow
- Implement JWT token generation
- Create login/register components
- Add OAuth2 integration (Google)
- Implement password reset flow
- Create user profile management
- Add role-based access control (RBAC)
- Implement API authentication middleware
- Add rate limiting per user
- Create user management dashboard (admin)
- Write security tests

**Success Criteria**:
- Secure password storage (bcrypt)
- JWT tokens with refresh mechanism
- OAuth2 login works
- Protected routes in frontend
- API endpoints require authentication
- RBAC properly enforced
- No security vulnerabilities

**Timeline**: 2-3 weeks

---

### Epic 5: Database and Data Persistence
**Labels**: `epic`, `backend`, `infrastructure`, `priority:medium`

**Description**:
Add PostgreSQL database for storing user data, analysis history, and agent conversations.

**Tasks**:
- Set up PostgreSQL on GKE (Cloud SQL)
- Design database schema
- Implement SQLAlchemy models
- Create Alembic migrations
- Add database connection pooling
- Implement repository pattern
- Store user analysis history
- Store agent conversation history
- Add pagination for history queries
- Implement data export functionality
- Add database backups
- Write database tests

**Success Criteria**:
- Database is properly configured
- Migrations work correctly
- Data is persisted across deployments
- Query performance is optimized
- Backups are automated

**Timeline**: 2 weeks

---

### Epic 6: Ground Truth Labeling Module
**Labels**: `epic`, `frontend`, `backend`, `priority:high`

**Description**:
Implement a complete ground truth labeling system for creating benchmark datasets. Each project has exactly ONE question (the KEY question). Users upload images to datasets and label them through a paginated gallery view with modal-based image inspection. Supports CSV import/export at project level.

**User Story**:
As an AI Engineer, I want to create ground truth datasets by labeling images one-by-one or by uploading a CSV file, so that I can efficiently prepare data for MLLM benchmarking experiments.

**Architecture**:
- 1:1 relationship between Project and Question
- Project contains multiple Datasets
- Dataset contains multiple Images
- Each Image has one Annotation (label)
- Progress tracking at Project level
- Google OAuth2 authentication
- ConfigMaps for DEV/UAT/PROD environments

**Database Schema**:
```sql
-- Projects (updated with question fields)
projects: id, name, description, question_text, question_type, question_options, created_by, created_at, updated_at

-- Datasets
datasets: id, project_id, name, created_by, created_at

-- Images
images: id, dataset_id, filename, storage_path, file_size, uploaded_by, uploaded_at

-- Annotations (one per image)
annotations: id, image_id (UNIQUE), answer_value, is_skipped, is_flagged, flag_reason, annotator_id, created_at, updated_at

-- Users (Google OAuth)
users: id, email, name, picture_url, google_id, created_at, last_login_at
```

**Question Types**:
- Binary (Yes/No)
- Multiple Choice (select one)
- Free Text
- Count (numeric)

**Tasks**:
- **Backend**:
    - Update projects table with question fields (question_text, question_type, question_options)
    - Create database models for datasets, images, annotations
    - Create storage service with local/GCS abstraction (configurable per environment)
    - Implement Google OAuth2 authentication
    - Create Kubernetes ConfigMaps for DEV/UAT/PROD environments
    - Implement project CRUD with question management
    - Implement dataset and image management endpoints
    - Implement labeling endpoints (single image + bulk operations)
    - Create CSV parser with pipe character (`|`) validation
    - Implement CSV import at project level
    - Implement CSV export with columns: filename, answer, status, labeled_by, labeled_at
    - Create project statistics endpoint (progress tracking)
    - Generate thumbnails on image upload
    - Write unit and integration tests

- **Frontend**:
    - Implement Google Sign-In authentication flow
    - Create project management UI with question configuration
    - Build paginated image gallery view with page size selector (10/20/50/100/all)
    - Implement filter controls (all/labeled/unlabeled/skipped/flagged) - filters apply before pagination
    - Create image modal (popup) with zoom/pan functionality
    - Build labeling controls for all question types
    - Implement keyboard shortcuts for gallery and modal views
    - Add input validation to block pipe character (`|`) in labels
    - Create CSV upload component for label import
    - Implement CSV export download button
    - Display project-level progress tracking
    - No preloading/caching - load thumbnails on page render, full image only in modal
    - Write component tests

**UI Behavior**:
- Gallery view shows thumbnails in grid with pagination
- Click image opens modal with full-size image
- Zoom/pan works only in modal
- Quick label buttons below each thumbnail in gallery
- Keyboard shortcuts for fast labeling
- Filters reduce total count, then pagination applies

**Keyboard Shortcuts**:
- Gallery: `1-9` select image, `Enter` open modal
- Modal: `Y/1` Yes, `N/0` No, `S` Skip, `F` Flag, `Space/Enter` Save & close, `→` Next, `←` Previous, `Esc` Close, `+/-` Zoom

**CSV Export Format**:
```csv
filename,answer,status,labeled_by,labeled_at
image1.jpg,Yes,labeled,alice@company.com,2025-11-14T10:30:45Z
image2.jpg,Coca-Cola|Pepsi,labeled,bob@company.com,2025-11-14T11:05:33Z
image3.jpg,,skipped,alice@company.com,2025-11-14T10:33:00Z
image4.jpg,,unlabeled,,
```

**Success Criteria**:
- User can sign in with Google account
- User can create project with one question (any of 4 types)
- User can update the project question
- User can upload images to datasets (max 500 images, max 10MB each)
- User can view images in paginated gallery (10/20/50/100/all per page)
- User can filter images by status (filters apply before pagination)
- User can click image to open modal with zoom/pan
- User can label images quickly using keyboard shortcuts
- User can skip or flag images for review
- User can bulk label all remaining unlabeled images
- User can import CSV labels at project level
- User can export CSV with answer, status, labeled_by, labeled_at columns
- System validates that pipe character (`|`) cannot be entered in labels
- Progress is tracked at project level across all datasets
- Configuration works correctly across DEV/UAT/PROD environments
- Thumbnails load efficiently without browser preloading/caching

**API Endpoints**:
```
Authentication:
  GET    /api/v1/auth/google/login
  GET    /api/v1/auth/google/callback
  POST   /api/v1/auth/logout
  GET    /api/v1/auth/me

Projects:
  POST   /api/v1/projects
  GET    /api/v1/projects
  GET    /api/v1/projects/{project_id}
  PATCH  /api/v1/projects/{project_id}
  DELETE /api/v1/projects/{project_id}
  GET    /api/v1/projects/{project_id}/stats
  GET    /api/v1/projects/{project_id}/export
  POST   /api/v1/projects/{project_id}/labels/import
  POST   /api/v1/projects/{project_id}/labels/bulk

Datasets:
  POST   /api/v1/projects/{project_id}/datasets
  GET    /api/v1/projects/{project_id}/datasets
  GET    /api/v1/datasets/{dataset_id}
  DELETE /api/v1/datasets/{dataset_id}

Images:
  POST   /api/v1/datasets/{dataset_id}/images
  GET    /api/v1/datasets/{dataset_id}/images?status=&page=&limit=
  GET    /api/v1/images/{image_id}
  GET    /api/v1/images/{image_id}/download
  GET    /api/v1/images/{image_id}/thumbnail
  DELETE /api/v1/images/{image_id}

Labeling:
  POST   /api/v1/images/{image_id}/label
  GET    /api/v1/images/{image_id}/label
```

**Timeline**: 3-4 weeks

---

### Epic 7: Experimentation & Benchmarking
**Labels**: `epic`, `frontend`, `backend`, `priority:high`

**Description**:
Implement the core benchmarking engine for running MLLM experiments on labeled datasets. Users configure model API keys at project level, create experiments, and run them to get accuracy scores. The system uses the project's KEY question (from Epic 6) directly - no separate prompt management for MVP.

**User Story**:
As an AI Engineer, I want to configure different MLLM models with my API keys, run experiments on my ground truth datasets, and see accuracy scores for each run, so that I can compare performance of different models.

**Architecture**:
- **Model Registry**: Global list of supported models (admin-managed)
- **Project Models**: Per-project API key configuration (user-managed, encrypted)
- **Experiments**: Link project model to run benchmarks
- **Experiment Runs**: Execution record with accuracy score
- **Predictions**: Individual image results for analysis

**Key Design Decisions**:
- Uses project's KEY question directly (no separate prompts for MVP)
- API keys encrypted with Cloud KMS (prod) or AES-256 (dev)
- Background job execution with rate limiting
- Retry failed API calls 3 times before marking as error
- Progress tracking during execution
- Cost estimation and tracking

**Database Schema**:
```sql
-- ModelRegistry (App-level, managed by admins)
model_registry
  - id (UUID, PK)
  - provider (VARCHAR) -- 'Google', 'Anthropic'
  - model_name (VARCHAR) -- 'gemini-1.5-pro', 'claude-3-sonnet'
  - display_name (VARCHAR) -- 'Gemini 1.5 Pro'
  - api_endpoint (VARCHAR)
  - default_config (JSONB) -- { "temperature": 0.7, "max_tokens": 1000 }
  - rate_limit_rpm (INTEGER) -- requests per minute
  - cost_per_1k_tokens (DECIMAL) -- for cost estimation
  - is_active (BOOLEAN)
  - created_at (TIMESTAMP)

-- ProjectModels (Project-level, configured by users)
project_models
  - id (UUID, PK)
  - project_id (FK → projects)
  - model_registry_id (FK → model_registry)
  - api_key_encrypted (BYTEA) -- encrypted with KMS/AES-256
  - custom_config (JSONB) -- override defaults
  - is_active (BOOLEAN)
  - created_by (FK → users)
  - created_at (TIMESTAMP)

-- Experiments
experiments
  - id (UUID, PK)
  - project_id (FK → projects)
  - project_model_id (FK → project_models)
  - name (VARCHAR)
  - description (TEXT)
  - created_by (FK → users)
  - created_at (TIMESTAMP)

-- ExperimentRuns
experiment_runs
  - id (UUID, PK)
  - experiment_id (FK → experiments)
  - dataset_id (FK → datasets)
  - status (ENUM: pending, running, completed, failed)
  - total_images (INTEGER)
  - processed_images (INTEGER) -- progress tracking
  - successful_predictions (INTEGER)
  - failed_predictions (INTEGER)
  - accuracy_score (FLOAT) -- 0.0 to 100.0
  - estimated_cost (DECIMAL)
  - actual_cost (DECIMAL)
  - error_message (TEXT)
  - started_at (TIMESTAMP)
  - completed_at (TIMESTAMP)

-- Predictions
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

**Accuracy Calculation**:
- Formula: `(correct_predictions / successful_predictions) * 100`
- Only successful predictions counted (failed API calls excluded)
- Comparison rules by question type:
  - Binary: Exact match (Yes/No, case-insensitive)
  - Multiple Choice: Exact match (case-insensitive)
  - Text: Case-insensitive exact match (for MVP)
  - Count: Exact numeric match (for MVP)

**Tasks**:
- **Backend**:
    - Create ModelRegistry model with seed data for Gemini and Claude
    - Implement API key encryption service (Cloud KMS for prod, AES-256 for dev)
    - Create CRUD APIs for ProjectModels with encrypted API key storage
    - Create CRUD APIs for Experiments
    - Create endpoint to trigger experiment run: `POST /api/v1/experiments/{id}/run`
    - Implement background Execution Engine service:
        - Queue-based job processing (or async task)
        - Iterate through all images in target dataset
        - Call MLLM API through abstraction layer (ModelService)
        - Respect rate limits per model provider
        - Retry failed calls 3 times with exponential backoff
        - Save predictions to database
        - Update progress (processed_images) every 10 images
    - Implement Scoring Service:
        - Compare predictions with ground truth annotations
        - Apply comparison rules per question type
        - Calculate accuracy score
        - Update experiment run with final results
    - Implement cost tracking (tokens used, estimated/actual cost)
    - Create endpoint for real-time progress: `GET /api/v1/experiment-runs/{id}/progress`
    - Write unit and integration tests

- **Frontend**:
    - Create "Models" tab in project settings:
        - Display available models from registry
        - Form to add API key for each model
        - Show masked API key (last 4 chars)
        - Test connection button
    - Create "Experiments" page within project:
        - List of experiments with name, model, created date
        - "New Experiment" button → modal/form
        - Select model (from configured project models)
        - Enter name and description
    - Create experiment detail view:
        - Table of ExperimentRuns with columns:
            - Run ID, Dataset, Status, Progress, Accuracy Score, Cost, Completed At
        - "Run on Dataset" button → select dataset modal
        - Real-time status updates (polling or WebSocket)
        - Progress bar during execution
    - Display accuracy as percentage (e.g., "87.5%")
    - Write component tests

**Error Handling**:
- API call failures: Retry 3 times with exponential backoff (1s, 2s, 4s)
- After 3 retries: Mark prediction as failed, continue with next image
- Track failed predictions separately from successful ones
- If >50% predictions fail: Mark entire run as failed
- Store error messages for debugging

**Rate Limiting Strategy**:
- Read `rate_limit_rpm` from model registry
- Implement token bucket or sliding window
- Queue requests when limit reached
- Different limits per model provider

**API Endpoints**:
```
Model Registry (Admin):
  GET    /api/v1/admin/models
  POST   /api/v1/admin/models
  PUT    /api/v1/admin/models/{id}
  DELETE /api/v1/admin/models/{id}

Project Models:
  GET    /api/v1/projects/{project_id}/models
  POST   /api/v1/projects/{project_id}/models
  PUT    /api/v1/project-models/{id}
  DELETE /api/v1/project-models/{id}
  POST   /api/v1/project-models/{id}/test -- test API key

Experiments:
  GET    /api/v1/projects/{project_id}/experiments
  POST   /api/v1/projects/{project_id}/experiments
  GET    /api/v1/experiments/{id}
  PUT    /api/v1/experiments/{id}
  DELETE /api/v1/experiments/{id}
  POST   /api/v1/experiments/{id}/run -- trigger run on dataset

Experiment Runs:
  GET    /api/v1/experiments/{id}/runs
  GET    /api/v1/experiment-runs/{id}
  GET    /api/v1/experiment-runs/{id}/progress
  GET    /api/v1/experiment-runs/{id}/predictions
  DELETE /api/v1/experiment-runs/{id}
```

**Success Criteria**:
- [ ] Admin can manage model registry (add/edit/disable models)
- [ ] User can add their API key for a supported model within a project
- [ ] API keys are encrypted at rest (Cloud KMS or AES-256)
- [ ] User can test API key connection before saving
- [ ] User can create an experiment by selecting a configured model
- [ ] User can trigger a run on a labeled dataset
- [ ] Progress is shown during execution (e.g., "50/100 images processed")
- [ ] Status updates in real-time (running → completed)
- [ ] Final accuracy score displayed as percentage (e.g., "87.5%")
- [ ] Failed API calls are retried 3 times before being marked as errors
- [ ] Accuracy calculated only on successful predictions
- [ ] Cost tracking shows estimated and actual cost per run
- [ ] Text comparison is case-insensitive
- [ ] Count comparison is exact numeric match
- [ ] System handles different model APIs (Gemini, Claude) through abstraction

**Dependencies**:
- Epic 5: Database and Data Persistence (required)
- Epic 6: Ground Truth Labeling (need labeled datasets)

**Timeline**: 3-4 weeks

---

## Frontend Issues (4 total)

### 1. Create image upload component with drag-and-drop
**Labels**: `frontend`, `enhancement`, `priority:high`

Implement Angular component for image upload with drag-and-drop support, preview, and validation.

---

### 2. Build agent chat interface
**Labels**: `frontend`, `enhancement`, `priority:high`

Create a chat-like interface for interacting with LangChain agents, showing messages and agent reasoning steps.

---

### 3. Add loading states and animations
**Labels**: `frontend`, `enhancement`, `priority:medium`

Implement proper loading indicators, skeletons, and animations for better UX.

---

### 4. Implement responsive design for mobile
**Labels**: `frontend`, `enhancement`, `priority:medium`

Ensure all components work properly on mobile devices with responsive layouts.

---

## Backend Issues (4 total)

### 1. Implement WebSocket for streaming agent responses
**Labels**: `backend`, `enhancement`, `priority:high`

Add WebSocket support for real-time streaming of agent execution steps.

---

### 2. Add rate limiting middleware
**Labels**: `backend`, `enhancement`, `priority:high`

Implement rate limiting to prevent API abuse.

---

### 3. Create comprehensive logging system
**Labels**: `backend`, `infrastructure`, `priority:medium`

Set up structured logging with different log levels and external logging service integration.

---

### 4. Create custom LangChain tools
**Labels**: `backend`, `enhancement`, `priority:medium`

Develop domain-specific tools for the agent (web search, file operations, etc.).

---

## Infrastructure Issues (3 total)

### 1. Set up monitoring with Prometheus and Grafana
**Labels**: `infrastructure`, `priority:high`

Implement application monitoring, metrics collection, and dashboards.

---

### 2. Configure horizontal pod autoscaling
**Labels**: `infrastructure`, `priority:medium`

Set up HPA based on CPU/memory metrics for automatic scaling.

---

### 3. Set up staging environment
**Labels**: `infrastructure`, `priority:medium`

Create separate staging environment for testing before production.

---

## Testing Issues (3 total)

### 1. Write E2E tests with Playwright/Cypress
**Labels**: `testing`, `priority:high`

Implement end-to-end tests covering critical user flows.

---

### 2. Increase backend test coverage to 80%
**Labels**: `testing`, `backend`, `priority:medium`

Write additional unit and integration tests for backend services.

---

### 3. Add frontend component tests
**Labels**: `testing`, `frontend`, `priority:medium`

Write tests for all Angular components using Jasmine/Karma.

---

## Documentation Issues (3 total)

### 1. Create API documentation with examples
**Labels**: `documentation`, `priority:medium`

Expand API documentation with code examples in multiple languages.

---

### 2. Write deployment runbook
**Labels**: `documentation`, `infrastructure`, `priority:medium`

Create detailed runbook for deployment procedures and troubleshooting.

---

### 3. Add contributing guidelines
**Labels**: `documentation`, `priority:low`

Create CONTRIBUTING.md with guidelines for contributors.

---

## Summary Statistics

- **Total Issues**: 24
- **Epics**: 7
- **Feature Issues**: 17
- **By Priority**:
  - High: 12
  - Medium: 11
  - Low: 1
- **By Component**:
  - Frontend: 4
  - Backend: 4
  - Infrastructure: 3
  - Testing: 3
  - Documentation: 3
  - Multiple components (epics): 7

## Recommended First Sprint

Focus on these high-priority issues first:

1. Epic: Infrastructure and DevOps Setup
2. Create image upload component
3. Set up monitoring
4. Write E2E tests
5. Implement rate limiting

## Project Board Structure

Recommended columns:
- **Backlog**: New issues not yet prioritized
- **To Do**: Prioritized and ready to work on
- **In Progress**: Currently being worked on
- **In Review**: Pull requests under review
- **Done**: Completed issues

## Labels Reference

| Label | Color | Description |
|-------|-------|-------------|
| epic | #8B00FF | Epic tracking multiple features |
| frontend | #00D4FF | Frontend related |
| backend | #FF6B00 | Backend related |
| infrastructure | #FFD700 | Infrastructure and DevOps |
| documentation | #90EE90 | Documentation |
| testing | #FF69B4 | Testing related |
| priority:high | #FF0000 | High priority |
| priority:medium | #FFA500 | Medium priority |
| priority:low | #00FF00 | Low priority |
| enhancement | GitHub default | New feature |
| bug | GitHub default | Bug report |
