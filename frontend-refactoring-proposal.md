# Frontend Refactoring Proposal

This document outlines a proposal for refactoring the Angular frontend application to improve modularity, maintainability, and code reusability.

## 1. Architecture & Patterns

### 1.1 Base API Service (Repository Pattern)
Currently, `ProjectsService`, `EvaluationsService`, and others manually handle `environment.apiUrl` concatenation and often repeat error handling logic.

**Proposal:**
Create a generic `BaseApiService<T>` or just a core `ApiService` that wraps `HttpClient`.

**File:** `src/app/core/services/base-api.service.ts`

```typescript
// Proposed generic base service
export abstract class BaseApiService<T> {
  protected abstract resourcePath: string;

  constructor(protected http: HttpClient, protected config: ApiConfiguration) {}

  protected get url(): string {
    return `${this.config.apiUrl}/${this.resourcePath}`;
  }

  list(params?: any): Observable<T[]> {
    return this.http.get<T[]>(this.url, { params });
  }

  get(id: string): Observable<T> {
    return this.http.get<T>(`${this.url}/${id}`);
  }

  create(data: Partial<T>): Observable<T> {
    return this.http.post<T>(this.url, data);
  }

  // ... update, delete
}
```

### 1.2 Domain Model Isolation
Interfaces are currently defined inside service files (e.g., `evaluations.service.ts`, `projects.service.ts`). This makes circular dependencies likely and makes it harder to share types between features.

**Proposal:**
Move interfaces to `src/app/core/models/`.

**Structure:**
- `src/app/core/models/project.model.ts`
- `src/app/core/models/evaluation.model.ts`
- `src/app/core/models/model-config.model.ts`

### 1.3 Smart vs. Dumb Components (Presentational vs. Container)
The `ModelsComponent` (`src/app/features/models/models.component.ts`) is a "Smart" component that does everything: data fetching, form handling, state management, and rendering.

**Proposal:**
Split complex views into a Container (Smart) and Presentational (Dumb) components.

**Example for Models Feature:**
- `ModelsContainerComponent`: Injects service, manages `signals`, handles events (save, delete).
- `ModelListComponent`: Input: `models[]`. Output: `edit`, `delete`, `test`.
- `ModelFormComponent`: Input: `config?`. Output: `save`, `cancel`.
- `ModelTestComponent`: Input: `config`. Output: `runTest`.

### 1.4 Authentication Refactoring
**Current State:**
`AuthService` directly uses `HttpClient` and manages OAuth flow and state.

**Proposal:**
Refactor `AuthService` to use the new `BaseApiService` or `ApiService` wrapper. Ensure token management and error handling (401/403) are centralized in an HttpInterceptor or within the base service.

### 1.5 Testing Strategy (Critical)
**Current State:**
Almost zero unit tests exist (only `app.component.spec.ts`).

**Proposal:**
Introduce a strict testing requirement for all refactored components and services.
- **Dumb Components:** Test inputs/outputs and rendering.
- **Smart Components:** Test service integration and state changes.
- **Services:** Test HTTP calls and error handling using `HttpTestingController`.

## 2. Refactoring by File

### 2.1 `src/app/features/models/models.component.ts`

**Current State:**
- 300+ lines.
- Mixed inline template with complex conditional rendering (`@if`, `@else`).
- Handles creating, editing, testing, and listing in one file.

**Proposed Changes:**
Break down into sub-components.

1.  **`src/app/features/models/components/model-form/model-form.component.ts`**
    *   **Responsibility:** Renders the form for creating/editing.
    *   **Input:** `initialConfig` (optional).
    *   **Output:** `save` (payload), `cancel`.
    *   **Improvement:** Use `ReactiveFormsModule` with `FormGroup` instead of `[(ngModel)]` for better validation and dirty checking.

2.  **`src/app/features/models/components/model-list/model-list.component.ts`**
    *   **Responsibility:** Renders the grid/list of cards.
    *   **Input:** `configs: ModelConfigListItem[]`.
    *   **Output:** `edit`, `delete`, `test`.

3.  **`src/app/features/models/models.component.ts` (Container)**
    *   **Code Snippet:**
    ```typescript
    @Component({
      template: `
        <app-model-form
          *ngIf="editingConfig || isCreating"
          [config]="editingConfig"
          (save)="onSave($event)"
          (cancel)="onCancel()">
        </app-model-form>

        <app-model-list
          [configs]="configs()"
          (edit)="onEdit($event)"
          (delete)="onDelete($event)">
        </app-model-list>
      `
    })
    export class ModelsComponent {
      // Only logic related to data flow
    }
    ```

### 2.2 `src/app/features/projects/projects.component.ts`

**Current State:**
- Similar to Models, handles creation form and list in one place.
- CSS for mobile responsiveness is inline and complex.

**Proposed Changes:**
1.  Extract the creation form into a dialog or a collapsible component: `ProjectCreateComponent`.
2.  Move the table logic into `ProjectTableComponent` if it grows, or keep it in the container if it remains simple, but move the "Create" logic out.
3.  **Shared Constants:** Extract `question_type` mapping to a pipe or util helper.
    *   `src/app/shared/pipes/question-type-label.pipe.ts`

### 2.3 `src/app/core/services/*.service.ts`

**Current State:**
- Duplicate methods for uploading files (FormData creation).
- Duplicate URL construction.

**Proposed Changes:**
- **`FileUploadService`**: Create a shared service for handling `FormData` generation and progress events.
- **`projects.service.ts`**:
    *   Refactor `uploadSingleImage` and `uploadImagesInParallel` to use the shared `FileUploadService`.
    *   Move `Project`, `Dataset` interfaces to `core/models`.

### 2.4 Shared Utilities

**Current State:**
- Hardcoded strings for Providers ('gemini', 'openai') and labels.

**Proposed Changes:**
- `src/app/core/constants/providers.const.ts`
- `src/app/core/constants/question-types.const.ts`

## 3. Implementation Plan

1.  **Phase 1: Foundation**
    - Create `core/models` and move interfaces.
    - Create `BaseApiService` (optional, or just standardize existing services).
    - Create shared constants/enums.

2.  **Phase 2: Component Split (Models Feature)**
    - Refactor `models.component.ts` into Container + Presentational components.
    - Switch to Reactive Forms for the Model Config form.
    - **Test:** Add `model-form.component.spec.ts` and `model-list.component.spec.ts`.

3.  **Phase 3: Component Split (Projects Feature)**
    - Extract "Create Project" form.
    - Implement a reusable "Confirm Dialog" service instead of `confirm()` alert.
    - **Test:** Add tests for new components.

4.  **Phase 4: Expanding Scope**
    - Apply "Smart/Dumb" pattern to `evaluations`, `labelling-jobs`, and `annotations` modules.
    - Refactor `AuthService` to use `BaseApiService`.
    - Ensure `admin` module follows the new patterns.

5.  **Phase 5: Testing & Hardening**
    - Achieve at least 50% unit test coverage for all new shared services and "Dumb" components.
    - Run full regression testing manually on the refactored features.
    - Verify that no duplicate HTTP logic exists (e.g., all raw `HttpClient` calls should be via `BaseApiService` or wrapped).

## 4. Benefits

- **Testability:** Dumb components are easier to test because they don't depend on services.
- **Maintainability:** Smaller files are easier to read.
- **Reusability:** The `ModelFormComponent` could potentially be reused in a wizard or modal.
- **Consistency:** Centralized types and constants prevent typo bugs.
- **Reliability:** Added test coverage ensures that future changes don't break existing functionality.