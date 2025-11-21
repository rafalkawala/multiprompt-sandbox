@echo off
REM Script to create GitHub issues and project for MultiPrompt Sandbox
REM Prerequisites: GitHub CLI installed and authenticated (gh auth login)

echo Creating GitHub issues and project for MultiPrompt Sandbox...

REM Check if gh is installed
where gh >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: GitHub CLI (gh) is not installed
    echo Install from: https://cli.github.com/
    exit /b 1
)

REM Check if authenticated
gh auth status >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Not authenticated with GitHub CLI
    echo Run: gh auth login
    exit /b 1
)

echo Creating labels...
gh label create "epic" --color "8B00FF" --description "Epic issue tracking multiple features" --force 2>nul
gh label create "frontend" --color "00D4FF" --description "Frontend related" --force 2>nul
gh label create "backend" --color "FF6B00" --description "Backend related" --force 2>nul
gh label create "infrastructure" --color "FFD700" --description "Infrastructure and DevOps" --force 2>nul
gh label create "documentation" --color "90EE90" --description "Documentation" --force 2>nul
gh label create "testing" --color "FF69B4" --description "Testing related" --force 2>nul
gh label create "priority:high" --color "FF0000" --description "High priority" --force 2>nul
gh label create "priority:medium" --color "FFA500" --description "Medium priority" --force 2>nul
gh label create "priority:low" --color "00FF00" --description "Low priority" --force 2>nul

echo Creating epic issues...

gh issue create --title "Epic: Infrastructure and DevOps Setup" --body "Goal: Set up complete infrastructure for development, testing, and deployment to Cloud Run. Tasks: Configure GCP, set up Terraform, set up CI/CD, configure monitoring." --label "epic,infrastructure,priority:high"

gh issue create --title "Epic: Image Analysis with Gemini Pro Vision" --body "Goal: Implement complete image analysis functionality using Gemini Pro Vision API. Tasks: Create upload UI, integrate Gemini, display results, add tests." --label "epic,frontend,backend,priority:high"

gh issue create --title "Epic: LangChain Agent Integration" --body "Goal: Build intelligent agent system using LangChain and Gemini Pro. Tasks: Implement agents, create tools, build chat UI, add streaming, write tests." --label "epic,backend,frontend,priority:high"

gh issue create --title "Epic: User Authentication and Authorization" --body "Goal: Implement secure user authentication and RBAC. Tasks: JWT auth, OAuth2, login UI, RBAC, security tests." --label "epic,backend,frontend,priority:medium"

gh issue create --title "Epic: Database and Data Persistence" --body "Goal: Add PostgreSQL for data persistence. Tasks: Set up Cloud SQL, create schema, implement models, add migrations, store history." --label "epic,backend,infrastructure,priority:medium"

echo Creating feature issues...

gh issue create --title "Create image upload component with drag-and-drop" --body "Implement Angular component for image upload with drag-and-drop support, preview, and validation." --label "frontend,enhancement,priority:high"

gh issue create --title "Build agent chat interface" --body "Create a chat-like interface for interacting with LangChain agents." --label "frontend,enhancement,priority:high"

gh issue create --title "Add loading states and animations" --body "Implement proper loading indicators and animations for better UX." --label "frontend,enhancement,priority:medium"

gh issue create --title "Implement responsive design for mobile" --body "Ensure all components work on mobile devices." --label "frontend,enhancement,priority:medium"

gh issue create --title "Implement WebSocket for streaming agent responses" --body "Add WebSocket support for real-time streaming." --label "backend,enhancement,priority:high"

gh issue create --title "Add rate limiting middleware" --body "Implement rate limiting to prevent API abuse." --label "backend,enhancement,priority:high"

gh issue create --title "Create comprehensive logging system" --body "Set up structured logging with external service integration." --label "backend,infrastructure,priority:medium"

gh issue create --title "Create custom LangChain tools" --body "Develop domain-specific tools for the agent." --label "backend,enhancement,priority:medium"

gh issue create --title "Set up monitoring with Prometheus and Grafana" --body "Implement monitoring, metrics, and dashboards." --label "infrastructure,priority:high"

gh issue create --title "Configure horizontal pod autoscaling" --body "Set up HPA for automatic scaling." --label "infrastructure,priority:medium"

gh issue create --title "Set up staging environment" --body "Create staging environment for testing." --label "infrastructure,priority:medium"

gh issue create --title "Write E2E tests with Playwright/Cypress" --body "Implement end-to-end tests." --label "testing,priority:high"

gh issue create --title "Increase backend test coverage to 80%%" --body "Write additional tests for backend." --label "testing,backend,priority:medium"

gh issue create --title "Add frontend component tests" --body "Write tests for Angular components." --label "testing,frontend,priority:medium"

gh issue create --title "Create API documentation with examples" --body "Expand API docs with code examples." --label "documentation,priority:medium"

gh issue create --title "Write deployment runbook" --body "Create deployment runbook and troubleshooting guide." --label "documentation,infrastructure,priority:medium"

gh issue create --title "Add contributing guidelines" --body "Create CONTRIBUTING.md file." --label "documentation,priority:low"

echo.
echo All issues created successfully!
echo.
echo Next steps:
echo 1. Create a GitHub Project at: https://github.com/YOUR_USERNAME?tab=projects
echo 2. Add the issues to your project board
echo 3. Organize into columns: Backlog, To Do, In Progress, Done
echo 4. Start working on high-priority issues!
