# Gemini CLI - Context Entry Point

## 🛑 STOP & READ
To save context window (tokens) and ensure you have the latest info, follow this procedure:

1.  **Read `docs/ai/00_START.md`** first. It contains the map to the rest of the documentation.
2.  **Only read specific files** in `docs/ai/` if you need them for your current task.
3.  **Update documentation** if you change patterns or structure, as per `docs/ai/05_MAINTENANCE.md`.

## Quick Start
*   **Environment:** `conda activate multiprompt-sandbox`
*   **Backend:** `cd backend`, `uvicorn main:app --reload`
*   **Frontend:** `cd frontend`, `pnpm start`
*   **Infra:** `cd infrastructure`, `terraform apply`

## Key Rules
*   **No Public IPs** for Cloud SQL.
*   **Use Alembic** for DB changes.
*   **Use Signals** in Angular.
*   **Service Layer** in Backend.

See `docs/ai/03_STANDARDS.md` for details.
