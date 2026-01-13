# Codebase Statistics & Analysis

## Overview

This document provides a comprehensive statistical analysis of the project's codebase, covering quantitative metrics (lines of code, files), technology choices, and architectural patterns.

## Quantitative Statistics

### Summary by Language

| Language | Files | Total Lines | Code Lines | Comment Lines | Blank Lines |
|----------|-------|-------------|------------|---------------|-------------|
| Python | 86 | 13,459 | 8,880 | 2,271 | 2,308 |
| TypeScript | 32 | 8,833 | 7,556 | 243 | 1,034 |
| CSS/SCSS | 9 | 2,033 | 1,666 | 46 | 321 |
| HTML | 8 | 1,216 | 1,068 | 51 | 97 |
| JSON | 8 | 14,572 | 14,572 | 0 | 0 |
| Markdown | 23 | 6,139 | 4,864 | 0 | 1,275 |

### Additional Metrics

*   **Total Files**: 166 (across monitored extensions)
*   **Total Characters (Python)**: ~480k
*   **Total Characters (TypeScript)**: ~272k
*   **Functions/Methods**:
    *   Python: ~250
    *   TypeScript: ~370

---

## Technology Stack

### Backend
*   **Framework**: FastAPI (Async Python)
*   **Database**: PostgreSQL with `pgvector` extension for vector similarity search.
*   **ORM**: SQLAlchemy 2.0 (Async) + Alembic for migrations.
*   **AI/ML**:
    *   `langchain`, `langchain-google-genai` for LLM orchestration.
    *   `google-generativeai`, `google-cloud-aiplatform` for Vertex AI integration.
    *   `Pillow` for image processing.
    *   `tiktoken` for tokenization.
*   **Utilities**:
    *   `pydantic` & `pydantic-settings` for validation and configuration.
    *   `structlog` for structured JSON logging.
    *   `tenacity` for retry logic.
    *   `celery`/`google-cloud-tasks` (implied by service names) for background tasks.

### Frontend
*   **Framework**: Angular 17
*   **UI Library**: Angular Material (`@angular/material`)
*   **State Management**: Angular Signals (Heavy usage detected) + RxJS.
*   **HTTP Client**: Angular `HttpClient` wrapped in a custom Repository pattern.
*   **Build Tool**: `pnpm` (implied by `pnpm-lock.yaml`).

---

## Design Patterns

### Backend Patterns
1.  **Service Layer Pattern**:
    *   Business logic is encapsulated in dedicated services (`backend/services/`), separating it from API controllers (`backend/api/`).
    *   Examples: `ProjectService`, `EvaluationService`, `ImageProcessingService`, `LLMService`.
2.  **Singleton Pattern**:
    *   `HttpClient` in `backend/core/http_client.py` ensures a single `httpx.AsyncClient` per event loop to manage connection pooling effectively.
3.  **Dependency Injection**:
    *   Extensive use of FastAPI's `Depends` system for injecting database sessions (`get_db`) and services into routes.
4.  **Retry Pattern**:
    *   Implemented via `tenacity` in `backend/core/retry_utils.py` to handle transient failures (e.g., rate limits) for external API calls.
5.  **Adapter/Provider Pattern**:
    *   Abstraction over external AI providers (e.g., `LLMService` abstracting Vertex/OpenAI calls).
6.  **Data Transfer Object (DTO)**:
    *   Pydantic models in `backend/schemas/` are used to define the shape of data entering and leaving the API, decoupling the internal DB models from the external API contract.

### Frontend Patterns
1.  **Repository Pattern**:
    *   `BaseApiService` provides a generic abstract class for API interactions, which specific services (e.g., `ProjectsService`) extend. This centralizes error handling and HTTP configuration.
2.  **Smart vs. Dumb Components**:
    *   Evidence of separation between container components (handling logic/state) and presentational components.
3.  **Signals for State**:
    *   Modern Angular approach using `signal` and `computed` for reactive state management, replacing some traditional RxJS `BehaviorSubject` patterns.
4.  **Interceptors**:
    *   Global error handling (e.g., 401 Unauthorized) via HTTP interceptors.

---

## Logging Patterns

### Backend
*   **Structured Logging**:
    *   Uses `structlog` to output logs in JSON format, making them machine-parsable (ideal for cloud monitoring like Cloud Logging).
    *   Pattern: `logger = structlog.get_logger(__name__)`
    *   Contextual logging (binding values like `project_id` or `request_id`) is likely used given the library choice.

### Frontend
*   **Console Logging**:
    *   Direct use of `console.error` (75 occurrences), `console.log` (26 occurrences), and `console.warn` (7 occurrences).
    *   No centralized logging service wrapper was explicitly detected in the grep scan, though `BaseApiService` likely handles API error logging.

---

## Interesting Observations

1.  **High Configuration Volume**:
    *   The project contains a significant amount of JSON (~14.5k lines), suggesting heavy reliance on configuration files, fixtures, or stored serialized data (possibly embeddings or test data).
2.  **Modern Angular Practices**:
    *   The high usage of `signal` (86 hits) indicates the frontend is using the very latest Angular features, moving away from `Zone.js` reliance where possible.
3.  **Vector Search Integration**:
    *   Explicit `pgvector` setup and `EmbeddingService` indicate this is a RAG (Retrieval-Augmented Generation) or semantic search capable application.
4.  **Robust Error Handling**:
    *   The presence of `retry_utils.py` and specific handling for `ResourceExhausted` (Google Cloud 429) shows a focus on production reliability against AI model rate limits.
