# Project Map

This document outlines the high-level structure of the repository.

## Root Directory

*   `backend/`: FastAPI Python application.
*   `frontend/`: Angular application.
*   `infrastructure/`: Terraform configurations for GCP.
*   `docs/`: Project documentation.
*   `docs/ai/`: Context and instructions for AI assistants.

## Backend Structure (`backend/`)

*   `app/` or `src/`: (Verify actual structure: currently seems flat or `backend/` root is the app root).
*   `core/`: Core utilities (HTTP client, config).
*   `infrastructure/`: External service adapters (LLM, Storage, DB).
*   `domain/`: Domain models (if Clean Architecture is strictly followed).
*   `api/`: API Routers/Controllers.
*   `tests/`: `pytest` suite.

## Frontend Structure (`frontend/`)

*   `src/app/core/`: Singleton services, guards, interceptors.
*   `src/app/shared/`: Reusable components (Dumb components), pipes, directives.
*   `src/app/features/`: Feature modules (Smart components/Pages).

## Key Configuration Files

*   `backend/requirements.txt`: Python dependencies.
*   `frontend/package.json`: JS/TS dependencies.
*   `infrastructure/main.tf`: Terraform entry point.
*   `CLAUDE.md` / `GEMINI.md`: AI Assistant entry points.
