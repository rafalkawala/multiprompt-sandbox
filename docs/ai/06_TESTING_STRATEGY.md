# Testing Strategy

This document outlines the testing strategy for the repository. All new features and bug fixes must be accompanied by relevant tests.

## Backend Testing (Python/FastAPI)

We use `pytest` as our primary test runner, with `pytest-asyncio` for async support and `pytest-mock` for mocking.

### Structure
Tests are located in `backend/tests/`:
*   `unit/`: Tests that run in isolation. Mock all external dependencies (DB, Vertex AI, GCS).
*   `integration/`: Tests that verify interaction between components or with the database (using a test DB container).

### Tools & Libraries
*   **Runner:** `pytest`
*   **Async:** `pytest-asyncio` (configured with `asyncio_mode = auto` in `pytest.ini`).
*   **Mocking:** `pytest-mock` (provides the `mocker` fixture).
*   **Coverage:** `pytest-cov` (automatically generates reports).

### Guidelines
1.  **Async Tests:** Mark async test functions with `async def`.
2.  **Database:**
    *   For **Unit Tests**, mock the database session.
    *   For **Integration Tests**, use the provided `db_session` fixture (check `conftest.py`) which typically rolls back transactions after each test.
3.  **External Services:** NEVER make real network calls to Vertex AI or GCS in unit tests. Always mock these interfaces.
4.  **Fixtures:** Place shared fixtures in `backend/tests/conftest.py`.

### Commands
```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run with coverage report
pytest --cov=app
```

## Frontend Testing (Angular)

We use the standard Angular testing stack: **Jasmine** for behavior specs and **Karma** for the test runner.

### Structure
*   Spec files (`*.spec.ts`) are co-located with their components/services.

### Guidelines
1.  **Components:** Test inputs, outputs, and rendering logic. Use `TestBed` to configure modules.
2.  **Services:** Test business logic and HTTP calls (use `HttpTestingController` to mock backend requests).
3.  **Signals:** specific tests for Signal updates and computed values.

### Commands
```bash
# Run unit tests
ng test
# or
pnpm test
```

## CI/CD Checks
Tests are run automatically on Pull Requests. Ensure `pytest` and `ng test` pass locally before pushing.
