# Claude Code - Context Entry Point

## 🛑 STOP & READ
**You are responsible for the project's memory.**

1.  **Read `docs/ai/00_START.md`** first. It contains the map to the rest of the documentation.
2.  **Only read specific files** in `docs/ai/` if you need them for your current task (save tokens!).
3.  **YOU MUST UPDATE DOCUMENTATION** if you change code, patterns, or structure.
    *   See `docs/ai/05_MAINTENANCE.md` for instructions.
    *   Failure to update docs = creating technical debt.

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
