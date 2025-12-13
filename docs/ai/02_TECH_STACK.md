# Tech Stack

## Backend
*   **Language:** Python 3.12+
*   **Framework:** FastAPI
*   **Database ORM:** SQLAlchemy (Async)
*   **Migrations:** Alembic
*   **Validation:** Pydantic
*   **AI/LLM:** Vertex AI (Gemini models), Google Cloud Auth
*   **HTTP Client:** `httpx` (Async)
*   **Testing:** `pytest`, `pytest-asyncio`, `pytest-mock`

## Frontend
*   **Framework:** Angular 17+
*   **UI Library:** Angular Material
*   **State Management:** Angular Signals (Avoid NgRx/Redux unless complex global state is needed)
*   **Package Manager:** pnpm
*   **Build Tool:** Angular CLI

## Infrastructure
*   **Cloud Provider:** Google Cloud Platform (GCP)
*   **IaC:** Terraform
*   **Compute:** Cloud Run
*   **Database:** Cloud SQL (PostgreSQL)
*   **Storage:** Google Cloud Storage (GCS)

## Development Environment
*   **OS:** Windows (Terminal/Bash) / Linux (CI)
*   **Containerization:** Docker (for local DB), Dockerfile (for deployment)
