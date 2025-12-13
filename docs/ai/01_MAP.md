# Project Map

This document outlines the high-level structure of the repository.

## Root Directory

*   `backend/`: FastAPI Python application.
*   `frontend/`: Angular application.
*   `infrastructure/`: Terraform configurations for GCP.
*   `docs/`: Project documentation.
*   `docs/ai/`: Context and instructions for AI assistants.

## Backend Structure (`backend/`)

*   `main.py`: Application entry point.
*   `api/`: API Routers and Controllers.
*   `config/`: Configuration files (e.g., `models.json`).
*   `core/`: Core utilities (HTTP client, config loaders).
*   `infrastructure/`: External service adapters (LLM, Storage, DB).
*   `models/`: SQLAlchemy ORM models and Pydantic schemas.
*   `scripts/`: Utility scripts (seed data, validation, tests).
    *   `seed_admin.py`: Create initial admin user.
    *   `validate_model_costs.py`: Check model pricing logic.
*   `services/`: Business logic layer (Service Pattern).
*   `tests/`: `pytest` suite.
*   `alembic/`: Database migration scripts.

## Frontend Structure (`frontend/`)

*   `src/app/core/`: Singleton services, guards, interceptors.
*   `src/app/shared/`: Reusable components (Dumb components), pipes, directives.
*   `src/app/features/`: Feature modules (Smart components/Pages).

## Key Configuration Files

*   `backend/requirements.txt`: Python dependencies.
*   `backend/config/models.json`: AI Model definitions and pricing.
*   `frontend/package.json`: JS/TS dependencies.
*   `infrastructure/main.tf`: Terraform entry point.
*   `CLAUDE.md` / `GEMINI.md`: AI Assistant entry points.
