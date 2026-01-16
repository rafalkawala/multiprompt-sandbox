# Image Size Analysis: Testing vs. Lite Images

This document summarizes the analysis of potential savings from separating "testing" dependencies from "lite" (production) images for both Backend and Frontend.

## Executive Summary

- **Backend:** Separating testing libraries saves approximately **62 MB** (~10% of the total image size). The current `backend/Dockerfile` already implements this separation.
- **Frontend:** Separating the build/test environment (Node.js + `node_modules`) from the runtime environment (Nginx) saves approximately **725 MB** (~93% of the total image size). The current `frontend/Dockerfile` already implements this separation via multi-stage builds.

## Detailed Analysis

### Backend (`backend/`)

The backend uses Python 3.11. Dependencies are split between `requirements.txt` (Production) and `requirements-dev.txt` (Testing/Dev).

#### Statistics

| Component | Size (Approx.) | Description |
| :--- | :--- | :--- |
| **Production Libraries** | **431 MB** | Installed size of `requirements.txt` |
| **Testing Libraries** | **62 MB** | Installed size of `requirements-dev.txt` |
| **Base Image** | ~154 MB | `python:3.11-slim` (Debian Bookworm) |
| **Total "Lite" Image** | **~585 MB** | Base + Prod Libs |
| **Total "Testing" Image** | **~647 MB** | Base + Prod Libs + Test Libs |
| **Absolute Saving** | **62 MB** | |
| **Relative Saving** | **~10.6%** | (vs Total Testing Image) |

#### Top 5 Largest Packages

**Production (`requirements.txt`):**
1. **`google`** (116 MB): Includes `google-cloud-aiplatform`, `google-cloud-storage`, etc. Required for Vertex AI integration.
2. **`pandas`** (72 MB): Required for Annotation Import/Export services.
3. **`sklearn`** (50 MB): Required for Clustering Service (`KMeans`).
4. **`numpy`** (~76 MB): 39 MB package + 37 MB libs. Core dependency for Pandas/Sklearn.
5. **`langchain_community`** (24 MB): Required for LLM integration logic.

**Testing (`requirements-dev.txt`):**
1. **`mypy`** (~21.5 MB): Static type checking (includes `mypyc`).
2. **`pytest`** (~3 MB): Testing framework.
3. **`black`** (1.2 MB): Code formatting.
4. **`isort`** (0.9 MB): Import sorting.
5. **`flake8`** (0.5 MB): Linting.

*Note: While `pandas`, `numpy`, and `scikit-learn` are heavy, they are currently used in production services (Import/Export, Clustering) and cannot be moved to the testing image without refactoring the application architecture.*

---

### Frontend (`frontend/`)

The frontend uses Angular 17. The Dockerfile uses a multi-stage build to separate the **Build/Test Environment** from the **Runtime Environment**.

#### Statistics

| Component | Size (Approx.) | Description |
| :--- | :--- | :--- |
| **Build/Test Environment** | **~770 MB** | `node:18-alpine` (~170 MB) + `node_modules` (~600 MB) |
| **Runtime Environment** | **~45 MB** | `nginx:alpine` (~40 MB) + Compiled App (~5 MB) |
| **Absolute Saving** | **~725 MB** | |
| **Relative Saving** | **~94%** | |

#### Implementation

The separation is achieved via Docker multi-stage builds:
1.  **`builder` stage:** Installs all dependencies (including `devDependencies` like Karma, Jasmine, TypeScript) to compile the Angular app. This layer is discarded.
2.  **Final stage:** Copies only the compiled assets (`dist/`) to a lightweight `nginx:alpine` image.

## Conclusion

The project already follows best practices for image size optimization:
1.  **Backend:** The Dockerfile explicitly installs only `requirements.txt`, keeping the image "lite" by excluding the 62 MB of testing tools.
2.  **Frontend:** The multi-stage build process ensures that the heavy Node.js environment and `node_modules` (700+ MB) are never shipped to production, resulting in a tiny ~45 MB footprint.
