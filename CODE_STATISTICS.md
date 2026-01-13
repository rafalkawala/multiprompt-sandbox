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
| **TOTAL** | **166** | **46,252** | **38,606** | **2,611** | **5,035** |

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

## Key Insights & "Aha!" Moments

1.  **Configuration as Data**: While the high JSON line count is primarily driven by `package-lock.json`, the project explicitly centralizes critical business logic in external JSON files rather than hardcoding it. This makes the platform adaptable to new AI models and pricing changes without code deploys.
2.  **Bleeding Edge Angular**: The adoption of Angular Signals (86+ occurrences) is very high. This isn't a legacy Angular app being maintained; it's being actively developed with the newest 2024 patterns, completely bypassing the "RxJS everywhere" complexity that plagued older Angular apps.
3.  **Production-Ready AI Resilience**: The specific implementation of `retry_utils` handling `ResourceExhausted` indicates the team has likely faced and solved real-world "quota exceeded" issues with Vertex AI. This isn't just a prototype; it's built to survive API flakes.
4.  **Backend/Frontend Disconnect**: While the backend uses sophisticated `structlog` for observability, the frontend relies on raw `console.log`. This creates a blind spot for debugging issues that happen on the client side in production.

---

## Verification of Insights: Configuration as Data

The insight regarding "Configuration as Data" was verified by analyzing the JSON files.

*   **Observation**: 14.5k lines of JSON.
*   **Reality Check**: ~14.1k lines are `frontend/package-lock.json`.
*   **The Real Gem**: `backend/config/models.json` contains the actual business logic configuration.

**Example from `backend/config/models.json`**:
Instead of hardcoding pricing per model in Python, the system loads it at runtime. This allows business stakeholders to potentially update pricing or add new models just by editing a file.

```json
{
  "id": "openai-gpt-4o-mini",
  "provider": "openai",
  "pricing_config": {
    "mode": "token_based",
    "input_price_per_1m": 0.15,
    "output_price_per_1m": 0.60
  }
}
```

This pattern confirms the application is designed for **extensibility**—adding a new LLM provider or changing a price is a configuration change, not a code refactor.

---

## Suggested Pattern Enhancements

1.  **OpenAPI Client Generation**
    *   **Why**: Currently, frontend services extend `BaseApiService` and manually define endpoints. This is error-prone and redundant.
    *   **What to add**: Use `openapi-generator-cli` to auto-generate the Angular client code from FastAPI's `openapi.json`.
    *   **Where**: `frontend/src/app/core/api/generated/` (Replace manual services in `frontend/src/app/core/services/`).

2.  **Frontend Logging Service**
    *   **Why**: 75+ `console.error` calls mean errors are lost if the user doesn't check the console.
    *   **What to add**: A `LoggerService` that wraps console calls and can optionally send critical errors to the backend (or a tool like Sentry).
    *   **Where**: `frontend/src/app/core/services/logger.service.ts`

3.  **Caching Layer (Redis)**
    *   **Why**: Embedding generation and LLM calls are expensive and slow.
    *   **What to add**: A distributed cache (Redis) with a decorator pattern to cache results of `EmbeddingService.embed_image` or `LLMService.generate`.
    *   **Where**: `backend/core/cache.py` (infrastructure) and applied in `backend/services/`.

4.  **Facade Pattern for AI Providers**
    *   **Why**: The `LLMService` handles multiple providers. As more are added (e.g., Anthropic, remote vs local), a Facade or strictly typed Strategy pattern would clean up the switching logic.
    *   **Where**: `backend/infrastructure/llm/provider_factory.py`
