#!/bin/bash

# Script to create GitHub issues and project for MultiPrompt Sandbox
# Prerequisites: GitHub CLI installed and authenticated (gh auth login)

set -e

echo "Creating GitHub issues and project for MultiPrompt Sandbox..."

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed"
    echo "Install from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub CLI"
    echo "Run: gh auth login"
    exit 1
fi

# Create labels
echo "Creating labels..."
gh label create "epic" --color "8B00FF" --description "Epic issue tracking multiple features" --force 2>/dev/null || true
gh label create "frontend" --color "00D4FF" --description "Frontend related" --force 2>/dev/null || true
gh label create "backend" --color "FF6B00" --description "Backend related" --force 2>/dev/null || true
gh label create "infrastructure" --color "FFD700" --description "Infrastructure and DevOps" --force 2>/dev/null || true
gh label create "documentation" --color "90EE90" --description "Documentation" --force 2>/dev/null || true
gh label create "testing" --color "FF69B4" --description "Testing related" --force 2>/dev/null || true
gh label create "priority:high" --color "FF0000" --description "High priority" --force 2>/dev/null || true
gh label create "priority:medium" --color "FFA500" --description "Medium priority" --force 2>/dev/null || true
gh label create "priority:low" --color "00FF00" --description "Low priority" --force 2>/dev/null || true

echo "Creating epic issues..."

# Epic 1: Infrastructure
gh issue create --title "Epic: Infrastructure and DevOps Setup" \
  --body "## Goal
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

## Timeline
2-3 weeks" \
  --label "epic,infrastructure,priority:high"

# Epic 2: Image Analysis
gh issue create --title "Epic: Image Analysis with Gemini Pro Vision" \
  --body "## Goal
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
- [ ] Implement error handling
- [ ] Add loading states
- [ ] Write tests

## Success Criteria
- Users can upload images (JPEG, PNG, GIF, WebP)
- Analysis results are accurate
- Max file size: 10MB
- Response time < 5 seconds
- Mobile responsive

## Timeline
2-3 weeks" \
  --label "epic,frontend,backend,priority:high"

# Epic 3: LangChain Agents
gh issue create --title "Epic: LangChain Agent Integration" \
  --body "## Goal
Build an intelligent agent system using LangChain and Gemini Pro for multi-step task execution.

## User Story
As a user, I want to interact with an AI agent that can break down complex tasks, use tools, and provide step-by-step reasoning.

## Tasks
- [ ] Design agent architecture
- [ ] Implement core LangChain agent with Gemini
- [ ] Create custom tools
- [ ] Add image analysis integration
- [ ] Create chat interface
- [ ] Implement streaming responses
- [ ] Add conversation history
- [ ] Create execution visualization
- [ ] Implement context management
- [ ] Add agent settings
- [ ] Write tests

## Success Criteria
- Agent can execute multi-step tasks
- Tools work correctly
- Clear visualization
- Context maintained
- Streaming works

## Timeline
3-4 weeks" \
  --label "epic,backend,frontend,priority:high"

# Epic 4: Authentication
gh issue create --title "Epic: User Authentication and Authorization" \
  --body "## Goal
Implement secure user authentication and role-based access control.

## Tasks
- [ ] Design authentication flow
- [ ] Implement JWT token generation
- [ ] Create login/register components
- [ ] Add OAuth2 integration (Google)
- [ ] Implement password reset
- [ ] Create user profile management
- [ ] Add RBAC
- [ ] Implement API auth middleware
- [ ] Add rate limiting per user
- [ ] Create user management dashboard
- [ ] Write security tests

## Success Criteria
- Secure password storage
- JWT with refresh
- OAuth2 works
- Protected routes
- API auth required
- No vulnerabilities

## Timeline
2-3 weeks" \
  --label "epic,backend,frontend,priority:medium"

# Epic 5: Data Persistence
gh issue create --title "Epic: Database and Data Persistence" \
  --body "## Goal
Add PostgreSQL database for storing user data, analysis history, and agent conversations.

## Tasks
- [ ] Set up PostgreSQL (Cloud SQL)
- [ ] Design database schema
- [ ] Implement SQLAlchemy models
- [ ] Create Alembic migrations
- [ ] Add connection pooling
- [ ] Implement repository pattern
- [ ] Store analysis history
- [ ] Store conversation history
- [ ] Add pagination
- [ ] Implement data export
- [ ] Add backups
- [ ] Write tests

## Success Criteria
- Database configured
- Migrations work
- Data persisted
- Performance optimized
- Backups automated

## Timeline
2 weeks" \
  --label "epic,backend,infrastructure,priority:medium"

echo "Creating feature issues..."

# Frontend features
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

# Backend features
gh issue create --title "Implement WebSocket for streaming agent responses" \
  --body "Add WebSocket support for real-time streaming of agent execution steps." \
  --label "backend,enhancement,priority:high"

gh issue create --title "Add rate limiting middleware" \
  --body "Implement rate limiting to prevent API abuse." \
  --label "backend,enhancement,priority:high"

gh issue create --title "Create comprehensive logging system" \
  --body "Set up structured logging with different log levels and external service integration." \
  --label "backend,infrastructure,priority:medium"

gh issue create --title "Create custom LangChain tools" \
  --body "Develop domain-specific tools for the agent (web search, file operations, etc.)." \
  --label "backend,enhancement,priority:medium"

# Infrastructure
gh issue create --title "Set up monitoring with Prometheus and Grafana" \
  --body "Implement application monitoring, metrics collection, and dashboards." \
  --label "infrastructure,priority:high"

gh issue create --title "Configure horizontal pod autoscaling" \
  --body "Set up HPA based on CPU/memory metrics for automatic scaling." \
  --label "infrastructure,priority:medium"

gh issue create --title "Set up staging environment" \
  --body "Create separate staging environment for testing before production." \
  --label "infrastructure,priority:medium"

# Testing
gh issue create --title "Write E2E tests with Playwright/Cypress" \
  --body "Implement end-to-end tests covering critical user flows." \
  --label "testing,priority:high"

gh issue create --title "Increase backend test coverage to 80%" \
  --body "Write additional unit and integration tests for backend services." \
  --label "testing,backend,priority:medium"

gh issue create --title "Add frontend component tests" \
  --body "Write tests for all Angular components using Jasmine/Karma." \
  --label "testing,frontend,priority:medium"

# Documentation
gh issue create --title "Create API documentation with examples" \
  --body "Expand API documentation with code examples in multiple languages." \
  --label "documentation,priority:medium"

gh issue create --title "Write deployment runbook" \
  --body "Create detailed runbook for deployment procedures and troubleshooting." \
  --label "documentation,infrastructure,priority:medium"

gh issue create --title "Add contributing guidelines" \
  --body "Create CONTRIBUTING.md with guidelines for contributors." \
  --label "documentation,priority:low"

echo "All issues created successfully!"
echo ""
echo "Next steps:"
echo "1. Create a GitHub Project at: https://github.com/YOUR_USERNAME?tab=projects"
echo "2. Add the issues to your project board"
echo "3. Organize into columns: Backlog, To Do, In Progress, Done"
echo "4. Start working on high-priority issues!"
