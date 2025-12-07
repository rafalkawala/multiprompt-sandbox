# Implementation Plan: Evaluation Comparison & Visualization (Issues #18 & #19)

## Overview
This plan addresses the need for detailed evaluation analysis (Issue #18) and side-by-side comparison of multiple evaluations (Issue #19). We will introduce a new "Comparison" view accessible from the main navigation.

## 1. Frontend Architecture Changes

### Navigation
*   **File:** `frontend/src/app/app.component.ts`
*   **Change:** Add a new item to `menuItems`:
    ```typescript
    { icon: 'compare_arrows', label: 'Comparison', route: '/evaluations/compare', adminOnly: false }
    ```

### Routing
*   **File:** `frontend/src/app/app.routes.ts`
*   **Change:** Add route for the new component:
    ```typescript
    { path: 'evaluations/compare', loadComponent: () => import('./features/evaluations/compare/compare.component').then(m => m.CompareComponent) }
    ```

### New Component: `CompareComponent`
*   **Location:** `frontend/src/app/features/evaluations/compare/compare.component.ts` (and `.html`, `.scss`)
*   **Responsibilities:**
    1.  **Selection Mode:**
        *   Display a list of available evaluations (reuse logic from `EvaluationsComponent` but with selection checkboxes).
        *   Allow filtering by Project/Dataset.
        *   **Constraint:** Limit selection to a maximum of **6** evaluations to ensure UI readability.
        *   "Compare" button (disabled if selection count is < 2 or > 6).
    2.  **Comparison Mode:**
        *   **Header:** Show selected evaluation names as column headers.
        *   **Metrics Row:** Accuracy, Total Images, Processed, Failed.
        *   **Confusion Matrix Row:** Visual comparison of True Positives, False Positives, etc. (using simple bar charts or colored numbers).
        *   **Config Row:** Show Model used, Prompt details (truncated with expand option), Temperature.
    3.  **Visualization (Single & Multi):**
        *   Use simple HTML/CSS bar charts for "Accuracy" comparison.
        *   Use a grid layout for the Confusion Matrix (2x2 grid per evaluation).

### Enhancing Single Evaluation View (Issue #18)
*   **File:** `frontend/src/app/features/evaluations/evaluations.component.ts` (or specific detail view if separated)
*   **Change:** The current `EvaluationsComponent` seems to handle both list and detail. We should ensure the "Detail" view (when an evaluation is expanded or selected) includes:
    *   **Confusion Matrix:** 2x2 grid showing TP/TN/FP/FN counts.
    *   **Accuracy Card:** Already exists, ensure it's prominent.
    *   **Error Analysis:** List of "Incorrect" results (already exists), add "False Positives" vs "False Negatives" filter tabs.

## 2. Backend Strategy
*   **No new endpoints required initially.**
*   The frontend will fetch the list of evaluations using `GET /api/v1/evaluations`.
*   For the comparison, the frontend will fetch details for *each* selected evaluation using `GET /api/v1/evaluations/{id}` in parallel (using `forkJoin`).
    *   *Reasoning:* The `Evaluation` object from the ID endpoint contains `results_summary` which has the pre-calculated metrics (accuracy, confusion matrix). The list endpoint might not have the full summary or config details.

## 3. Detailed Component Design (`CompareComponent`)

### State Management
*   `evaluations`: List of all available evaluations.
*   `selectedIds`: Set/Array of selected IDs.
*   `comparisonData`: Array of detailed `Evaluation` objects (loaded after "Compare" click).
*   `loading`: Boolean.

### Layout (Draft)

**Selection View:**
```html
<mat-card>
  <div class="selection-header">
    <h3>Select Evaluations to Compare</h3>
    <span class="hint">(Select 2 to 6 items)</span>
  </div>
  
  <table mat-table [dataSource]="evaluations">
    <!-- Checkbox Column -->
    <ng-container matColumnDef="select">
      <th mat-header-cell *matHeaderCellDef>
        <!-- Master toggle removed or limited to selecting first 6 -->
      </th>
      <td mat-cell *matCellDef="let row">
        <mat-checkbox 
          (click)="$event.stopPropagation()" 
          (change)="$event ? toggleSelection(row) : null"
          [checked]="selection.isSelected(row)"
          [disabled]="!selection.isSelected(row) && selection.selected.length >= 6">
        </mat-checkbox>
      </td>
    </ng-container>
    ... (Name, Project, Dataset, Created At columns)
  </table>
  <button mat-raised-button color="primary" 
          (click)="loadComparison()" 
          [disabled]="selection.selected.length < 2">
    Compare ({{selection.selected.length}})
  </button>
</mat-card>
```

**Comparison View:**
```html
<div class="comparison-grid">
  <!-- Headers -->
  <div class="row header">
    <div class="cell label">Metric</div>
    <div class="cell" *ngFor="let eval of comparisonData">{{ eval.name }}</div>
  </div>
  
  <!-- Accuracy -->
  <div class="row">
    <div class="cell label">Accuracy</div>
    <div class="cell" *ngFor="let eval of comparisonData">
      <div class="bar-chart-container">
        <div class="bar" [style.height.%]="eval.results_summary.accuracy * 100"></div>
        <span>{{ eval.results_summary.accuracy | percent }}</span>
      </div>
    </div>
  </div>

  <!-- Model Config -->
  <div class="row">
    <div class="cell label">Model</div>
    <div class="cell" *ngFor="let eval of comparisonData">
      {{ eval.model_config.model_id }}
      <span class="tag">{{ eval.model_config.provider }}</span>
    </div>
  </div>
  
  <!-- Confusion Matrix (Binary only) -->
  <div class="row">
    <div class="cell label">Confusion Matrix</div>
    <div class="cell" *ngFor="let eval of comparisonData">
      <!-- 2x2 Grid Component -->
      <app-confusion-matrix [matrix]="eval.results_summary.confusion_matrix"></app-confusion-matrix>
    </div>
  </div>
</div>
```

## 4. Execution Steps
1.  **Scaffold:** Create `frontend/src/app/features/evaluations/compare/` directory and component files.
2.  **Route:** Register the route in `app.routes.ts`.
3.  **Nav:** Add "Comparison" to `app.component.ts`.
4.  **Implement Selection:** Build the table with checkboxes in `CompareComponent` and enforce the 6-item limit.
5.  **Implement Logic:** Add `loadComparison()` using `forkJoin` from `EvaluationsService`.
6.  **Implement Comparison View:** Build the grid layout and visualizations.
7.  **Refine Single View:** Update `EvaluationsComponent` (or `EvaluationDetailComponent`) to include the Confusion Matrix visualization (Issue #18).

## 5. Future Considerations (Not in this MVP)
*   **Backend Aggregation:** If comparing 10+ evaluations becomes slow, creating a bulk fetch endpoint `POST /evaluations/batch` accepting a list of IDs would be better.
*   **Export:** CSV export of the comparison table.
