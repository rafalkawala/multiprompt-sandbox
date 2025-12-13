# Documentation Maintenance = Memory Management

**This documentation is the project's Long-Term Memory.**

As an AI assistant (Claude, Gemini, or others), you are responsible for maintaining this memory. If you change the code but do not update these docs, you are creating "technical debt" in the form of lost context.

## When to Update (Memory Triggers)
*   **New Feature:** Added a new module? Update `01_MAP.md`. Added a new library? Update `02_TECH_STACK.md`.
*   **Refactoring:** Changed how the DB works? Update `03_STANDARDS.md`.
*   **New Command:** Added a useful script? Update `04_COMMANDS.md`.
*   **Correction:** Found a lie in the docs? Fix it immediately.

## How to Update
1.  Read the relevant file.
2.  Edit the file with the new information.
3.  Include the documentation update in your commit/PR.

**Goal:** A new agent starting from zero should be able to read these files and understand the project state *without* reading the entire codebase.
