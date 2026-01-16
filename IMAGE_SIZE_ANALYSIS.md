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

---

### Deep Dive: Optimizing Google Cloud AI Platform

**Q: Can we go deeper and remove parts of `google-cloud-aiplatform`?**

**Analysis:**
Yes, significant savings are possible because the `google-cloud-aiplatform` package is monolithic, containing clients for *every* Vertex AI service (Training, Prediction, Pipelines, Feature Store, etc.), while the application currently uses only a tiny fraction (Embedding generation via `vertexai.vision_models` and raw REST calls for LLMs).

**Findings:**
- **Total Installed Size:** ~112 MB (including `vertexai`).
- **Used Components:**
    - `vertexai.vision_models` (~136 KB code, but pulls in shared deps).
    - `google.auth` (Required for authentication).
- **Unused Heavy Components:**
    - `google/cloud/aiplatform_v1` (~44 MB): Generated gRPC clients for all services.
    - `google/cloud/aiplatform_v1beta1` (~56 MB): Beta clients.
    - `vertexai/preview` (~396 KB).
    - `vertexai/evaluation` (~468 KB).

**Recommendation:**
In the `Dockerfile`, after `pip install`, we can explicitly remove unused directories to save ~80-90 MB.

**Implementation Strategy (Dockerfile post-install command):**
```dockerfile
# Prune unused google cloud libraries
RUN rm -rf /usr/local/lib/python3.11/site-packages/google/cloud/aiplatform_v1beta1 && \
    rm -rf /usr/local/lib/python3.11/site-packages/google/cloud/aiplatform_v1/services/featurestore_service && \
    rm -rf /usr/local/lib/python3.11/site-packages/google/cloud/aiplatform_v1/services/pipeline_service && \
    rm -rf /usr/local/lib/python3.11/site-packages/google/cloud/aiplatform_v1/services/tensorboard_service
# ... and other specific unused services
```
*Risk Level:* Medium. Requires careful verification that imported modules don't implicitly depend on deleted files.

---

### Deep Dive: K-Means at Scale (Alternatives to Sklearn/Numpy)

**Q: Are there executable alternatives? How to run K-Means at scale with reliability?**

Since `scikit-learn` is used *only* for K-Means clustering in `ClusteringService`, replacing it can save ~50 MB (Sklearn) + ~76 MB (Numpy, if also removed).

#### 1. Standalone Executable (Recommended for "Lite" Image)
Instead of a heavy Python library, we can include a small, pre-compiled binary for K-Means.
- **Implementation:** A simple Go or Rust program that accepts a JSON/binary stream of vectors, computes centroids, and returns assignments.
- **Size:** ~2-5 MB.
- **Pros:** Extremely lightweight, fast, no Python dependencies.
- **Cons:** Adds a build step (multi-stage Docker build to compile the tool) or requires checking in a binary.

#### 2. Google Cloud Vertex AI (Vector Search)
For "proper reliability at scale," Vertex AI Vector Search (formerly Matching Engine) is the managed solution.
- **Mechanism:** Upload vectors to a GCS bucket -> Create Index -> Deploy IndexEndpoint.
- **Pros:** Massive scale (billions of vectors), managed reliability, low latency.
- **Cons:**
    - **Overkill:** Designed for nearest neighbor search, not ad-hoc K-Means clustering of small datasets.
    - **Cost & Latency:** High deployment time (minutes to hours) and minimum node costs ($$).
    - **Functionality Mismatch:** It builds an approximate index for *search*, it doesn't strictly output "Cluster IDs" for a dataset in the way `KMeans` does.

#### 3. BigQuery ML (Best for Scale & Simplicity)
If the data can be loaded into BigQuery, BQML provides native K-Means.
- **SQL:** `CREATE MODEL my_model OPTIONS(model_type='kmeans', num_clusters=5) AS SELECT embedding FROM images`
- **Pros:** Serverless, handles massive scale, standard SQL interface.
- **Cons:** Requires moving data to BQ (latency). Best for offline/batch jobs, not real-time user interactions.

#### 4. PostgreSQL Extensions (Cloud SQL Constraints)
The user asked: *"Is there a way to actually use a PostgreSQL extension in Cloud SQL?"*

**Answer:** Yes, but with strict limitations.
- **Supported Extensions:** Cloud SQL for PostgreSQL supports a *fixed list* of extensions (e.g., `pgvector`, `postgis`, `fuzzystrmatch`). You can enable them via `CREATE EXTENSION`.
- **Custom Extensions:** You **cannot** install arbitrary C-based extensions like `postgresql-kmeans` on Cloud SQL. You are limited to what Google provides.

**Feasible Cloud SQL Approaches for K-Means:**
1.  **pgvector (Supported):** `pgvector` is supported (since Postgres 11+). While it optimizes nearest neighbor search (IVFFlat index), it does **not** expose a public `kmeans()` function for arbitrary clustering of data.
2.  **PL/pgSQL Implementation:** You can implement the K-Means algorithm purely in SQL/PLpgSQL.
    - *Pros:* Zero external dependencies, runs on standard Cloud SQL.
    - *Cons:* Performance is significantly slower than C/Python for large datasets.
3.  **PL/Python (Supported):** Cloud SQL supports `plpython3u`.
    - *Strategy:* You can write a PostgreSQL function in Python that imports `scikit-learn` or `numpy` *if* those libraries are available in the Cloud SQL instance environment.
    - *Blocker:* Cloud SQL's managed environment likely does not include `scikit-learn` pre-installed, and you cannot pip install packages into the managed database instance.
    - *Verdict:* Not a viable path for adding libraries.

### Final Recommendation

1.  **For Immediate Image Reduction (~80MB):** Implement the `rm -rf` pruning strategy for `google-cloud-aiplatform` in the Dockerfile.
2.  **For K-Means (Small Scale):** Replace `scikit-learn` with a **custom Numpy implementation** (keeping Numpy) or a **standalone executable** (dropping Numpy).
3.  **For K-Means (Large Scale):** Use **BigQuery ML** if dataset grows beyond memory limits, as it offers the best balance of scale and reliability without managing infrastructure.
4.  **Database-Side Clustering:** Since `postgresql-kmeans` is not supported on Cloud SQL, implementing K-Means in **pure PL/pgSQL** is the only database-native option, but likely too slow for production vector workloads.
