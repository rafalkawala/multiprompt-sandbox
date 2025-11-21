# GitHub Project Setup Guide

## Prerequisites

### Install GitHub CLI
1. Download from: https://cli.github.com/
2. Install and restart terminal
3. Authenticate: `gh auth login`

## Step 1: Create GitHub Repository

```bash
cd C:\Users\rafal\Projects\MultiPromptSandbox

# Create repository
gh repo create multiprompt-sandbox --public --source=. --remote=origin

# Or if you prefer private
gh repo create multiprompt-sandbox --private --source=. --remote=origin

# Push code
git push -u origin main
```

## Step 2: Create GitHub Project

```bash
# Create a new project (beta)
gh project create --owner @me --title "MultiPrompt Sandbox Development"
```

Or create manually at: https://github.com/YOUR_USERNAME?tab=projects

## Step 3: Create Labels

```bash
# Create custom labels
gh label create "epic" --color "8B00FF" --description "Epic issue tracking multiple features"
gh label create "frontend" --color "00D4FF" --description "Frontend related"
gh label create "backend" --color "FF6B00" --description "Backend related"
gh label create "infrastructure" --color "FFD700" --description "Infrastructure and DevOps"
gh label create "documentation" --color "90EE90" --description "Documentation"
gh label create "testing" --color "FF69B4" --description "Testing related"
gh label create "priority:high" --color "FF0000" --description "High priority"
gh label create "priority:medium" --color "FFA500" --description "Medium priority"
gh label create "priority:low" --color "00FF00" --description "Low priority"
```

## Step 4: Create Issues

### Epic 1: Infrastructure Setup
```bash
gh issue create --title "Epic: Infrastructure and DevOps Setup" \
  --body "$(cat <<'EOF'
# Epic: Infrastructure and DevOps Setup

## Goal
Set up complete infrastructure for development, testing, and deployment to Cloud Run.

## Tasks
- [ ] Configure GCP project and enable APIs
- [ ] Set up Terraform for infrastructure as code
- [ ] Set up Artifact Registry for Docker images
- [ ] Configure GitHub Actions secrets
- [ ] Set up Google Cloud secrets for API keys
- [ ] Create separate dev/staging/prod environments
- [ ] Configure monitoring and logging

## Success Criteria
- CI/CD pipeline successfully deploys to Cloud Run
- Automated testing runs on every PR
- Secrets are properly managed
- Monitoring is in place

## Dependencies
- GCP account with billing enabled
- Gemini API access
- GitHub repository

## Estimated Timeline
2-3 weeks
EOF
)" \
  --label "epic,infrastructure,priority:high"
```

### Epic 2: Image Analysis Feature
```bash
gh issue create --title "Epic: Image Analysis with Gemini Pro Vision" \
  --body "$(cat <<'EOF'
# Epic: Image Analysis with Gemini Pro Vision

## Goal
Implement complete image analysis functionality using Gemini Pro Vision API.

## User Story
As a user, I want to upload images and receive AI-powered analysis including descriptions, object detection, and labels.

## Tasks
- [ ] Create image upload component in Angular
- [ ] Implement drag-and-drop functionality
- [ ] Add image preview before upload
- [ ] Create Gemini service integration
- [ ] Handle multiple image formats
- [ ] Display analysis results with labels
- [ ] Add export functionality for results
- [ ] Implement error handling for invalid images
- [ ] Add loading states and progress indicators
- [ ] Write unit and integration tests

## Success Criteria
- Users can upload images (JPEG, PNG, GIF, WebP)
- Analysis results are accurate and detailed
- Maximum file size: 10MB
- Response time < 5 seconds
- Proper error handling
- Mobile responsive

## API Endpoints
- `POST /api/v1/images/analyze`

## Estimated Timeline
2-3 weeks
EOF
)" \
  --label "epic,frontend,backend,priority:high"
```

### Epic 3: LangChain Agent System
```bash
gh issue create --title "Epic: LangChain Agent Integration" \
  --body "$(cat <<'EOF'
# Epic: LangChain Agent Integration

## Goal
Build an intelligent agent system using LangChain and Gemini Pro for multi-step task execution.

## User Story
As a user, I want to interact with an AI agent that can break down complex tasks, use tools, and provide step-by-step reasoning.

## Tasks
- [ ] Design agent architecture
- [ ] Implement core LangChain agent with Gemini
- [ ] Create custom tools (search, calculator, etc.)
- [ ] Add tool for image analysis integration
- [ ] Create chat interface in Angular
- [ ] Implement streaming responses
- [ ] Add conversation history
- [ ] Create agent execution visualization
- [ ] Implement context management
- [ ] Add agent settings configuration
- [ ] Write comprehensive tests

## Success Criteria
- Agent can execute multi-step tasks
- Tools work correctly
- Clear visualization of agent thinking
- Conversation context is maintained
- Proper error handling
- Response streaming works smoothly

## API Endpoints
- `POST /api/v1/agents/execute`
- `GET /api/v1/agents/status` (future)

## Estimated Timeline
3-4 weeks
EOF
)" \
  --label "epic,backend,frontend,priority:high"
```

### Epic 4: Authentication & Authorization
```bash
gh issue create --title "Epic: User Authentication and Authorization" \
  --body "$(cat <<'EOF'
# Epic: User Authentication and Authorization

## Goal
Implement secure user authentication and role-based access control.

## User Story
As a user, I want to securely log in and have my data protected with proper authorization.

## Tasks
- [ ] Design authentication flow
- [ ] Implement JWT token generation
- [ ] Create login/register components
- [ ] Add OAuth2 integration (Google)
- [ ] Implement password reset flow
- [ ] Create user profile management
- [ ] Add role-based access control (RBAC)
- [ ] Implement API authentication middleware
- [ ] Add rate limiting per user
- [ ] Create user management dashboard (admin)
- [ ] Write security tests

## Success Criteria
- Secure password storage (bcrypt)
- JWT tokens with refresh mechanism
- OAuth2 login works
- Protected routes in frontend
- API endpoints require authentication
- RBAC properly enforced
- No security vulnerabilities

## Estimated Timeline
2-3 weeks
EOF
)" \
  --label "epic,backend,frontend,priority:medium"
```

### Epic 5: Data Persistence
```bash
gh issue create --title "Epic: Database and Data Persistence" \
  --body "$(cat <<'EOF'
# Epic: Database and Data Persistence

## Goal
Add PostgreSQL database for storing user data, analysis history, and agent conversations.

## Tasks
- [ ] Set up PostgreSQL on Cloud SQL
- [ ] Design database schema
- [ ] Implement SQLAlchemy models
- [ ] Create Alembic migrations
- [ ] Add database connection pooling
- [ ] Implement repository pattern
- [ ] Store user analysis history
- [ ] Store agent conversation history
- [ ] Add pagination for history queries
- [ ] Implement data export functionality
- [ ] Add database backups
- [ ] Write database tests

## Success Criteria
- Database is properly configured
- Migrations work correctly
- Data is persisted across deployments
- Query performance is optimized
- Backups are automated

## Estimated Timeline
2 weeks
EOF
)" \
  --label "epic,backend,infrastructure,priority:medium"
```

## Step 5: Create Feature Issues

### Frontend Issues
```bash
gh issue create --title "Create image upload component with drag-and-drop" \
  --body "Implement Angular component for image upload with drag-and-drop support, preview, and validation." \
  --label "frontend,enhancement,priority:high"

gh issue create --title "Build agent chat interface" \
  --body "Create a chat-like interface for interacting with LangChain agents, showing messages and agent reasoning steps." \
  --label "frontend,enhancement,priority:high"

gh issue create --title "Add loading states and animations" \
  --body "Implement proper loading indicators, skeletons, and animations for better UX." \
  --label "frontend,enhancement,priority:medium"

gh issue create --title "Implement responsive design for mobile" \
  --body "Ensure all components work properly on mobile devices with responsive layouts." \
  --label "frontend,enhancement,priority:medium"

gh issue create --title "Add error boundary and error handling UI" \
  --body "Create error boundary component and user-friendly error messages." \
  --label "frontend,enhancement,priority:medium"
```

### Backend Issues
```bash
gh issue create --title "Implement WebSocket for streaming agent responses" \
  --body "Add WebSocket support for real-time streaming of agent execution steps." \
  --label "backend,enhancement,priority:high"

gh issue create --title "Add rate limiting middleware" \
  --body "Implement rate limiting to prevent API abuse." \
  --label "backend,enhancement,priority:high"

gh issue create --title "Create comprehensive logging system" \
  --body "Set up structured logging with different log levels and external logging service integration." \
  --label "backend,infrastructure,priority:medium"

gh issue create --title "Add API request/response caching" \
  --body "Implement Redis caching for frequently accessed data." \
  --label "backend,infrastructure,priority:medium"

gh issue create --title "Create custom LangChain tools" \
  --body "Develop domain-specific tools for the agent (web search, file operations, etc.)." \
  --label "backend,enhancement,priority:medium"
```

### Infrastructure Issues
```bash
gh issue create --title "Set up monitoring with Prometheus and Grafana" \
  --body "Implement application monitoring, metrics collection, and dashboards." \
  --label "infrastructure,priority:high"

gh issue create --title "Configure horizontal pod autoscaling" \
  --body "Set up HPA based on CPU/memory metrics for automatic scaling." \
  --label "infrastructure,priority:medium"

gh issue create --title "Implement centralized logging with ELK stack" \
  --body "Set up Elasticsearch, Logstash, Kibana for log aggregation." \
  --label "infrastructure,priority:medium"

gh issue create --title "Add health check endpoints and probes" \
  --body "Implement comprehensive health checks for all services." \
  --label "infrastructure,priority:high"

gh issue create --title "Set up staging environment" \
  --body "Create separate staging environment for testing before production." \
  --label "infrastructure,priority:medium"
```

### Testing Issues
```bash
gh issue create --title "Write E2E tests with Playwright/Cypress" \
  --body "Implement end-to-end tests covering critical user flows." \
  --label "testing,priority:high"

gh issue create --title "Increase backend test coverage to 80%" \
  --body "Write additional unit and integration tests for backend services." \
  --label "testing,backend,priority:medium"

gh issue create --title "Add frontend component tests" \
  --body "Write tests for all Angular components using Jasmine/Karma." \
  --label "testing,frontend,priority:medium"

gh issue create --title "Create load testing suite" \
  --body "Implement load tests to verify system performance under stress." \
  --label "testing,infrastructure,priority:low"
```

### Documentation Issues
```bash
gh issue create --title "Create API documentation with examples" \
  --body "Expand API documentation with code examples in multiple languages." \
  --label "documentation,priority:medium"

gh issue create --title "Write deployment runbook" \
  --body "Create detailed runbook for deployment procedures and troubleshooting." \
  --label "documentation,infrastructure,priority:medium"

gh issue create --title "Add contributing guidelines" \
  --body "Create CONTRIBUTING.md with guidelines for contributors." \
  --label "documentation,priority:low"

gh issue create --title "Create architecture decision records (ADRs)" \
  --body "Document architectural decisions and rationale." \
  --label "documentation,priority:low"
```

## Step 6: Organize Issues in Project

After creating issues, add them to your project:

```bash
# List all issues
gh issue list

# Add issues to project (replace PROJECT_ID)
gh project item-add PROJECT_ID --owner @me --url https://github.com/OWNER/REPO/issues/ISSUE_NUMBER
```

## Step 7: Create Milestones

```bash
gh api repos/:owner/:repo/milestones -f title="MVP Release" -f description="Minimum Viable Product" -f due_on="2024-12-31T23:59:59Z"
gh api repos/:owner/:repo/milestones -f title="Beta Release" -f description="Feature complete beta" -f due_on="2025-03-31T23:59:59Z"
gh api repos/:owner/:repo/milestones -f title="Production Release" -f description="Production ready release" -f due_on="2025-06-30T23:59:59Z"
```

## Alternative: Manual Setup

If you prefer to create issues manually:

1. Go to your repository on GitHub
2. Click "Issues" → "New Issue"
3. Copy content from the issue templates above
4. Add appropriate labels
5. Create a Project board at https://github.com/users/YOUR_USERNAME/projects
6. Add issues to the project board

## Project Board Setup

Recommended columns:
- **Backlog**: New issues not yet prioritized
- **To Do**: Prioritized and ready to work on
- **In Progress**: Currently being worked on
- **In Review**: Pull requests under review
- **Done**: Completed issues

## Tips

- Use issue templates for consistency
- Link PRs to issues with "Closes #X" or "Fixes #X"
- Use project automation rules
- Regular grooming and prioritization
- Keep issues focused and small
