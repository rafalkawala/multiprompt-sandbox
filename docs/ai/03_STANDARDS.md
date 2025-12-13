# Coding Standards & Patterns

## General
*   **Comments:** Write detailed in-code comments explaining the *rationale* behind implementation choices.
*   **DRY:** Don't Repeat Yourself. Modularize logic.

## Backend (Python/FastAPI)
*   **Service Layer Pattern:** Decouple business logic from API controllers. Controllers should only handle request/response parsing and delegate to Services.
*   **Async/Await:** Use `async def` and `await` for I/O bound operations (DB, API calls).
*   **Dependency Injection:** Use FastAPI's `Depends` for injecting services and database sessions.
*   **Database Sessions:**
    *   Use `SessionLocal` for background tasks to ensure thread safety.
    *   Avoid sharing sessions between requests and background threads.
    *   Convert ORM objects to DTOs/Pydantic models before passing to background tasks to prevent `DetachedInstanceError`.
*   **Vertex AI:**
    *   Use strict type casting (int/float) for parameters.
    *   Do NOT include the `role` field in `systemInstruction`.
    *   Handle `400 Invalid Argument` by checking parameter types and model names.

## Frontend (Angular)
*   **Smart vs Dumb Components:**
    *   **Smart (Container):** Handle data fetching, state, and business logic.
    *   **Dumb (Presentational):** purely receive inputs (`@Input`) and emit events (`@Output`). minimal logic.
*   **Signals:** Use Angular Signals for state management within components and services.
*   **API Interactions:** Use `BaseApiService` (Repository pattern) for standardized HTTP calls and error handling.

## Infrastructure (Terraform)
*   **Private IP:** Do not assign public IPs to Cloud SQL instances.
*   **State Management:** Use remote backend (GCS) if configured, otherwise be careful with local state.
