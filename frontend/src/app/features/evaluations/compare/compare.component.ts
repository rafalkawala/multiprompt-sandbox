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
import { MatExpansionModule } from '@angular/material/expansion';
import { SelectionModel } from '@angular/cdk/collections';
import { forkJoin, map, switchMap, of, catchError } from 'rxjs';

import { EvaluationsService, EvaluationListItem, Evaluation, ModelConfig } from '../../../core/services/evaluations.service';
import { ConfusionMatrixComponent } from '../../../shared/components/confusion-matrix/confusion-matrix.component';

interface ComparisonItem {
  evaluation: Evaluation;
  modelConfig: ModelConfig | null;
}

interface DatasetGroup {
  datasetName: string;
  evaluations: EvaluationListItem[];
  lastModified: Date;
}

interface ProjectGroup {
  projectName: string;
  datasets: DatasetGroup[];
  lastModified: Date;
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
    MatExpansionModule,
    ConfusionMatrixComponent
  ],
  templateUrl: './compare.component.html',
  styleUrl: './compare.component.scss'
})
export class CompareComponent implements OnInit {
  // Selection State
  groupedEvaluations = signal<ProjectGroup[]>([]);
  loadingList = signal(true);
  selection = new SelectionModel<EvaluationListItem>(true, []);
  displayedColumns = ['select', 'name', 'model_name', 'accuracy', 'created_at'];

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
        this.groupEvaluations(data);
        this.loadingList.set(false);
        this.autoSelectLatestGroup();
      },
      error: (err) => {
        console.error('Failed to load evaluations', err);
        this.snackBar.open('Failed to load evaluations', 'Close', { duration: 3000 });
        this.loadingList.set(false);
      }
    });
  }

  groupEvaluations(evaluations: EvaluationListItem[]) {
    const groups: Record<string, Record<string, EvaluationListItem[]>> = {};

    evaluations.forEach(ev => {
      if (!groups[ev.project_name]) {
        groups[ev.project_name] = {};
      }
      if (!groups[ev.project_name][ev.dataset_name]) {
        groups[ev.project_name][ev.dataset_name] = [];
      }
      groups[ev.project_name][ev.dataset_name].push(ev);
    });

    const projectGroups: ProjectGroup[] = Object.keys(groups).map(projectName => {
      const datasetsObj = groups[projectName];
      const datasets: DatasetGroup[] = Object.keys(datasetsObj).map(datasetName => {
        const evals = datasetsObj[datasetName].sort((a, b) => 
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        return {
          datasetName,
          evaluations: evals,
          lastModified: new Date(evals[0].created_at) // Last modified is the newest eval
        };
      }).sort((a, b) => b.lastModified.getTime() - a.lastModified.getTime());

      return {
        projectName,
        datasets,
        lastModified: datasets.length > 0 ? datasets[0].lastModified : new Date(0)
      };
    }).sort((a, b) => b.lastModified.getTime() - a.lastModified.getTime());

    this.groupedEvaluations.set(projectGroups);
  }

  autoSelectLatestGroup() {
    const groups = this.groupedEvaluations();
    if (groups.length > 0 && groups[0].datasets.length > 0) {
      // Select the first (latest) dataset of the first (latest) project
      const latestDataset = groups[0].datasets[0];
      
      // Select up to MAX_SELECTION evaluations from this group
      const toSelect = latestDataset.evaluations.slice(0, this.MAX_SELECTION);
      this.selection.select(...toSelect);
    }
  }

  toggleSelection(row: EvaluationListItem) {
    if (this.selection.isSelected(row)) {
      this.selection.deselect(row);
    } else {
      // Check for project consistency
      if (this.selection.selected.length > 0) {
        const currentProject = this.selection.selected[0].project_name;
        if (row.project_name !== currentProject) {
          this.selection.clear();
          this.snackBar.open(`Cleared previous selection (comparisons limited to single project)`, 'Close', { duration: 3000 });
        }
      }

      if (this.selection.selected.length < this.MAX_SELECTION) {
        this.selection.select(row);
      } else {
        this.snackBar.open(`Maximum ${this.MAX_SELECTION} evaluations can be compared`, 'Close', { duration: 2000 });
      }
    }
  }

  toggleGroupSelection(datasetGroup: DatasetGroup, event: any) {
    event.stopPropagation();
    const allSelected = datasetGroup.evaluations.every(e => this.selection.isSelected(e));
    
    if (allSelected) {
      // Deselect all in this group
      this.selection.deselect(...datasetGroup.evaluations);
    } else {
      // Selecting a group: Clear everything else first to enforce focus and project constraint
      this.selection.clear();

      // Select up to MAX_SELECTION from this group
      const toSelect = datasetGroup.evaluations.slice(0, this.MAX_SELECTION);
      this.selection.select(...toSelect);
      
      if (datasetGroup.evaluations.length > this.MAX_SELECTION) {
        this.snackBar.open(`Selected top ${this.MAX_SELECTION} evaluations from group`, 'Close', { duration: 2000 });
      }
    }
  }

  isGroupSelected(datasetGroup: DatasetGroup): boolean {
    return datasetGroup.evaluations.length > 0 && 
           datasetGroup.evaluations.every(e => this.selection.isSelected(e));
  }

  isGroupIndeterminate(datasetGroup: DatasetGroup): boolean {
    const selectedCount = datasetGroup.evaluations.filter(e => this.selection.isSelected(e)).length;
    return selectedCount > 0 && selectedCount < datasetGroup.evaluations.length;
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
