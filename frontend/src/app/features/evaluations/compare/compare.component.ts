import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar } from '@angular/material/snack-bar';
import { SelectionModel } from '@angular/cdk/collections';
import { forkJoin, map, switchMap, of, catchError } from 'rxjs';

import { EvaluationsService, EvaluationListItem, Evaluation, ModelConfig } from '../../../core/services/evaluations.service';
import { ConfusionMatrixComponent } from '../../../shared/components/confusion-matrix/confusion-matrix.component';

interface ComparisonItem {
  evaluation: Evaluation;
  modelConfig: ModelConfig | null;
}

@Component({
  selector: 'app-compare',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatCheckboxModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    ConfusionMatrixComponent
  ],
  templateUrl: './compare.component.html',
  styleUrl: './compare.component.scss'
})
export class CompareComponent implements OnInit {
  // Selection State
  evaluations = signal<EvaluationListItem[]>([]);
  loadingList = signal(true);
  selection = new SelectionModel<EvaluationListItem>(true, []);
  displayedColumns = ['select', 'name', 'model_name', 'project_name', 'accuracy', 'created_at'];

  // Comparison State
  comparisonData = signal<ComparisonItem[]>([]);
  loadingComparison = signal(false);
  showComparison = signal(false);

  readonly MAX_SELECTION = 6;

  constructor(
    private evaluationsService: EvaluationsService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.loadEvaluations();
  }

  loadEvaluations() {
    this.loadingList.set(true);
    this.evaluationsService.getEvaluations().subscribe({
      next: (data) => {
        this.evaluations.set(data);
        this.loadingList.set(false);
      },
      error: (err) => {
        console.error('Failed to load evaluations', err);
        this.snackBar.open('Failed to load evaluations', 'Close', { duration: 3000 });
        this.loadingList.set(false);
      }
    });
  }

  toggleSelection(row: EvaluationListItem) {
    if (this.selection.isSelected(row)) {
      this.selection.deselect(row);
    } else {
      if (this.selection.selected.length < this.MAX_SELECTION) {
        this.selection.select(row);
      } else {
        this.snackBar.open(`Maximum ${this.MAX_SELECTION} evaluations can be compared`, 'Close', { duration: 2000 });
      }
    }
  }

  isRowDisabled(row: EvaluationListItem): boolean {
    return !this.selection.isSelected(row) && this.selection.selected.length >= this.MAX_SELECTION;
  }

  runComparison() {
    const selected = this.selection.selected;
    if (selected.length < 2) return;

    this.loadingComparison.set(true);
    this.showComparison.set(true);

    // For each selected item, fetch Evaluation and ModelConfig
    const tasks = selected.map(item => 
      this.evaluationsService.getEvaluation(item.id).pipe(
        switchMap(evaluation => {
          // Fetch ModelConfig using the ID from evaluation
          return this.evaluationsService.getModelConfig(evaluation.model_config_id).pipe(
            map(modelConfig => ({ evaluation, modelConfig })),
            catchError(err => {
              console.error(`Failed to load model config for eval ${evaluation.id}`, err);
              return of({ evaluation, modelConfig: null });
            })
          );
        }),
        catchError(err => {
          console.error(`Failed to load evaluation ${item.id}`, err);
          return of(null);
        })
      )
    );

    forkJoin(tasks).subscribe({
      next: (results) => {
        // Filter out any failed requests (nulls)
        const validResults = results.filter((r): r is ComparisonItem => r !== null);
        this.comparisonData.set(validResults);
        this.loadingComparison.set(false);
      },
      error: (err) => {
        console.error('Comparison failed', err);
        this.snackBar.open('Failed to load comparison data', 'Close', { duration: 3000 });
        this.loadingComparison.set(false);
        this.showComparison.set(false);
      }
    });
  }

  backToSelection() {
    this.showComparison.set(false);
    this.comparisonData.set([]);
  }

  formatAccuracy(acc: number | null): string {
    if (acc === null || acc === undefined) return '-';
    return (acc * 100).toFixed(1) + '%';
  }
}
