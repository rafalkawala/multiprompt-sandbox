# Backend Refactoring Proposal

This document outlines a refactoring plan to improve the modularity, repeatability (DRY), and maintainability of the backend codebase.

## 1. Modularize API Controllers (Fat Controller Refactoring)

**Problem:** API endpoints (e.g., `backend/api/v1/datasets.py`, `backend/api/v1/projects.py`) contain significant business logic, database queries, and direct storage operations. This violates the Single Responsibility Principle and makes testing/reuse difficult.

**Proposal:** Move business logic to dedicated Service classes.

### A. Dataset Service
*   **File:** `backend/api/v1/datasets.py` -> `backend/services/dataset_service.py`
*   **Pattern:** Service Layer Pattern
*   **Changes:**
    *   Extract logic for `create_dataset`, `delete_dataset`, `list_datasets` into `DatasetService`.
    *   Extract `upload_images` and `batch_upload_images` logic into `DatasetService` or `ImageUploadService`.
    *   The API controller should only handle request parsing, dependency injection, calling the service, and error mapping.

### B. Project Service
*   **File:** `backend/api/v1/projects.py` -> `backend/services/project_service.py`
*   **Pattern:** Service Layer Pattern
*   **Changes:**
    *   Extract CRUD operations for projects into `ProjectService`.
    *   Encapsulate authorization checks (ownership verification) within the service or a dedicated dependency.

## 2. Unify Resource Verification & Authorization

**Problem:** `datasets.py` and `projects.py` (and potentially others) repeat the logic for verifying if a project exists and if the user has access.
```python
# Repeated in multiple endpoints
project = db.query(Project).filter(
    Project.id == project_id,
    Project.created_by_id == current_user.id
).first()
if not project: raise ...
```

**Proposal:** Create reusable dependencies or mixins for resource retrieval and authorization.

*   **File:** `backend/api/deps.py` (New file) or `backend/api/v1/dependencies.py`
*   **Pattern:** Dependency Injection / Chain of Responsibility
*   **Changes:**
    *   Create `get_project_or_404` dependency.
    *   Create `verify_project_ownership` dependency.
    *   Create `verify_project_write_access` dependency.
    *   Replace manual queries in controllers with these dependencies.

## 3. Centralize Pydantic Schemas

**Problem:** Pydantic models (DTOs) are defined directly within API controller files (e.g., `DatasetCreate`, `ImageResponse` in `datasets.py`). This prevents reuse and clutters the controller files.

**Proposal:** Move all schemas to a dedicated `schemas` package.

*   **File:** `backend/schemas/` (New directory)
    *   `backend/schemas/dataset.py`
    *   `backend/schemas/project.py`
    *   `backend/schemas/image.py`
    *   `backend/schemas/common.py` (for generic responses like error messages)
*   **Pattern:** Data Transfer Object (DTO)
*   **Changes:**
    *   Move `DatasetCreate`, `DatasetResponse`, `ImageResponse`, etc., to their respective schema files.
    *   Update imports in API files.

## 4. Decouple Image Upload & Processing

**Problem:** The `upload_images` function in `datasets.py` is monolithic. It handles validation, unique filename generation, thumbnail generation, storage upload, and DB creation.

**Proposal:** Break down the upload pipeline.

*   **File:** `backend/services/image_upload_service.py` (New or refactor `ImageProcessingService`)
*   **Pattern:** Pipeline / Facade
*   **Changes:**
    *   **Validation:** Extract `is_valid_image_file` and extension checking to a `FileValidator` class or `core/validation.py`.
    *   **Naming:** Extract path generation logic (`projects/{proj}/datasets/{dataset}/{uuid}`) to a `StoragePathStrategy` or method on `Dataset` model.
    *   **Processing:** Ensure `ImageProcessingService` is consistently used for thumbnail generation, rather than inline calls in the controller.

## 5. Centralize Configuration & Constants

**Problem:** Constants like `ALLOWED_IMAGE_EXTENSIONS` are defined in `datasets.py`. Magic strings/numbers (e.g., max upload size logic) are scattered.

**Proposal:** Centralize configuration.

*   **File:** `backend/core/config.py` or `backend/core/constants.py`
*   **Pattern:** Configuration Object
*   **Changes:**
    *   Move `ALLOWED_IMAGE_EXTENSIONS` to constants.
    *   Ensure limits (file size) are loaded from `settings`.

## 6. Standardize Error Handling

**Problem:** `HTTPException` is raised directly deep within logic in some places.

**Proposal:** Use custom exceptions and a global exception handler.

*   **File:** `backend/core/exceptions.py` & `backend/main.py`
*   **Pattern:** Custom Exceptions
*   **Changes:**
    *   Define `ResourceNotFoundException`, `AccessDeniedException`, `FileValidationException`.
    *   Services raise these exceptions.
    *   `main.py` includes an `exception_handler` to map these to appropriate HTTP status codes (404, 403, 400).

## Summary of New File Structure

```
backend/
  api/
    deps.py              <-- New: Reusable dependencies
    v1/
      datasets.py        <-- Refactored: Lean controller
      projects.py        <-- Refactored: Lean controller
  schemas/               <-- New: Centralized Pydantic models
    dataset.py
    project.py
    image.py
  services/
    dataset_service.py   <-- New: Business logic for datasets
    project_service.py   <-- New: Business logic for projects
    image_upload_service.py
  core/
    constants.py         <-- New: Shared constants
    exceptions.py        <-- New: Custom exceptions
```
