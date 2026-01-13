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

1.  **Configuration as Data**
    *   **Insight**: Critical business logic (AI pricing, provider details) is externalized in `backend/config/models.json` rather than hardcoded.
    *   **Pros**: Allows non-engineers to update pricing or add models; enables hot-reloading of business rules.
    *   **Cons**: No compile-time validation of configuration; risk of schema drift between code and JSON.

2.  **Bleeding Edge Angular**
    *   **Insight**: Heavy usage of Angular Signals (86+ occurrences) indicates a modern, reactive architecture.
    *   **Pros**: Simpler state management than RxJS/NgRx; finer-grained change detection improves performance.
    *   **Cons**: New paradigm for developers used to "Classic Angular"; tooling and best practices are still evolving.

3.  **Defensive Dependency Management**
    *   **Insight**: `backend/services/agent_service.py` wraps LangChain imports in `try-except` blocks.
    *   **Pros**: Allows the application to start in a "lite" mode without installing heavy ML libraries; simplifies local dev setup if you don't need agents.
    *   **Cons**: Can lead to "lazy failures" where errors only appear at runtime when a specific feature is accessed.

4.  **Prompt Engineering as Infrastructure**
    *   **Insight**: System prompts are stored in `backend/config/prompts.yaml`, not in Python code.
    *   **Pros**: Decouples prompt iteration from code deployment; enables version control of prompts independent of logic.
    *   **Cons**: "Magic strings" in YAML (e.g., `{options}`) must perfectly match code logic, or silent failures occur.

5.  **Backend/Frontend Disconnect**
    *   **Insight**: Sophisticated backend logging (`structlog`) vs. primitive frontend logging (`console.log`).
    *   **Pros**: Backend is production-ready for observability.
    *   **Cons**: Frontend client-side errors in production are invisible to the team, making debugging user reports difficult.

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

## 5 Deep Questions to the Codebase

1.  **Data Integrity & Versioning**: *How does the system ensure `models.json` and `prompts.yaml` stay in sync with the codebase?*
    *   *Context*: If a new model requires a new prompt parameter, or pricing logic changes structure, a static file update could break the app without CI checks.
2.  **State Management Scalability**: *With the heavy use of local Signals, is there a risk of "prop drilling" or duplicated state?*
    *   *Context*: While Signals are great for component state, complex global state (like a multi-step "Wizard" process) often needs a centralized store (like NgRx or a Global Signal Store) to prevent consistency bugs.
3.  **Vector Search Performance**: *Is the `pgvector` implementation optimized for scale (IVFFlat/HNSW indexing) or is it a raw scan?*
    *   *Context*: Raw vector scans work for <10k items but become unacceptably slow for larger datasets. The code needs to handle index creation and maintenance.
4.  **Test Isolation vs. Reality**: *Why does the unit test suite mock DB models instead of using a containerized test database?*
    *   *Context*: Mocking ORM models is notoriously brittle and often hides integration bugs (e.g., specific SQL dialect issues) that only appear in production.
5.  **Security of "Prompt Injection" via Config**: *Are the `{options}` injected into `prompts.yaml` sanitized?*
    *   *Context*: If a user can create a project question option that contains prompt-injection text, they could override the system prompt logic, as the variable substitution happens in a simple `.replace()`.

---

## Suggested Pattern Enhancements

1.  **OpenAPI Client Generation**
    *   **Why**: Eliminate manual `BaseApiService` boilerplate.
    *   **Pros**: Type safety from backend to frontend; zero manual sync effort; automatic breaking change detection.
    *   **Cons**: Requires a build step; generated code can be verbose/ugly.

2.  **Frontend Logging Service**
    *   **Why**: Capture client-side errors in production.
    *   **Pros**: Full observability; ability to alert on JS crashes.
    *   **Cons**: Adds a small amount of network traffic; requires a backend endpoint or 3rd party service (Sentry).

3.  **Caching Layer (Redis)**
    *   **Why**: Speed up repeated embedding/LLM calls.
    *   **Pros**: Massive performance/cost wins for repetitive workloads.
    *   **Cons**: Adds infrastructure complexity (managing Redis instance); cache invalidation is hard.

4.  **Facade Pattern for AI Providers**
    *   **Why**: Clean up `LLMService` complexity.
    *   **Pros**: Strictly typed interfaces for every provider; easier unit testing.
    *   **Cons**: More boilerplate code upfront.

### Top 3 Recommended Implementations

1.  **Frontend Logging Service**: (High Impact, Low Effort) - The current blind spot on the frontend is a critical production risk. Fixing this gives immediate visibility.
2.  **OpenAPI Client Generation**: (High Impact, Medium Effort) - Significantly improves developer velocity and prevents "backend changed, frontend broke" bugs.
3.  **Caching Layer**: (High Impact, High Effort) - Essential for scaling, but can be deferred until traffic increases.
