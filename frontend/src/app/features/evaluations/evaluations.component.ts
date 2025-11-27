import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTableModule } from '@angular/material/table';
import { MatExpansionModule } from '@angular/material/expansion';
import { EvaluationsService, EvaluationListItem, ModelConfigListItem, CreateEvaluation, EvaluationResult, Evaluation } from '../../core/services/evaluations.service';
import { ProjectsService, ProjectListItem, DatasetDetail, Project } from '../../core/services/projects.service';

@Component({
  selector: 'app-evaluations',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatProgressBarModule,
    MatChipsModule,
    MatTableModule,
    MatExpansionModule
  ],
  template: `
    <div class="evaluations-container">
      <h1>Evaluations</h1>
      <p class="subtitle">Run benchmarks against LLM models</p>

      <!-- Create Evaluation -->
      <mat-card class="create-card">
        <mat-card-header>
          <mat-card-title>New Evaluation</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Name</mat-label>
              <input matInput [(ngModel)]="newEval.name" placeholder="GPT-4o vs Training Set">
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Project</mat-label>
              <mat-select [(ngModel)]="newEval.project_id" (selectionChange)="onProjectChange()">
                @for (project of projects(); track project.id) {
                  <mat-option [value]="project.id">{{ project.name }}</mat-option>
                }
              </mat-select>
            </mat-form-field>
          </div>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Dataset</mat-label>
              <mat-select [(ngModel)]="newEval.dataset_id" [disabled]="!newEval.project_id">
                @for (dataset of datasets(); track dataset.id) {
                  <mat-option [value]="dataset.id">{{ dataset.name }} ({{ dataset.image_count }} images)</mat-option>
                }
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Model</mat-label>
              <mat-select [(ngModel)]="newEval.model_config_id">
                @for (config of modelConfigs(); track config.id) {
                  <mat-option [value]="config.id">{{ config.name }} ({{ config.model_name }})</mat-option>
                }
              </mat-select>
            </mat-form-field>
          </div>

          <!-- Editable Prompts -->
          @if (newEval.project_id) {
            <div class="prompts-section">
              <h3 class="section-title">Evaluation Prompts (editable)</h3>
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>System Message</mat-label>
                <textarea matInput [(ngModel)]="newEval.system_message" rows="3"
                  placeholder="Instructions for the model"></textarea>
                <mat-hint>System-level instructions for the model</mat-hint>
              </mat-form-field>
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Question Text</mat-label>
                <input matInput [(ngModel)]="newEval.question_text"
                  placeholder="What question should the model answer?">
                <mat-hint>The question to ask about each image</mat-hint>
              </mat-form-field>
            </div>
          }
        </mat-card-content>
        <mat-card-actions>
          <button mat-raised-button color="primary" (click)="startEvaluation()" [disabled]="!isFormValid()">
            <mat-icon>play_arrow</mat-icon>
            Start Evaluation
          </button>
        </mat-card-actions>
      </mat-card>

      <!-- Evaluations List -->
      @if (loading()) {
        <div class="loading">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (evaluations().length === 0) {
        <mat-card class="empty-state">
          <mat-icon>science</mat-icon>
          <p>No evaluations yet. Start your first one above.</p>
        </mat-card>
      } @else {
        @for (evaluation of evaluations(); track evaluation.id) {
          <mat-card class="evaluation-card">
            <mat-card-header>
              <mat-card-title>{{ evaluation.name }}</mat-card-title>
              <mat-card-subtitle>
                {{ evaluation.project_name }} / {{ evaluation.dataset_name }} / {{ evaluation.model_name }}
              </mat-card-subtitle>
            </mat-card-header>
            <mat-card-content>
              <div class="status-row">
                <mat-chip [color]="getStatusColor(evaluation.status)" highlighted>
                  {{ evaluation.status }}
                </mat-chip>
                @if (evaluation.accuracy !== null) {
                  <span class="accuracy">Accuracy: {{ (evaluation.accuracy * 100).toFixed(1) }}%</span>
                }
                @if (evaluation.status === 'running' || evaluation.status === 'completed') {
                   <span class="count-text">
                     {{ evaluation.processed_images }} / {{ evaluation.total_images }} images
                   </span>
                }
              </div>
              @if (evaluation.status === 'running') {
                <mat-progress-bar mode="determinate" [value]="(evaluation.processed_images / evaluation.total_images) * 100"></mat-progress-bar>
                <div class="progress-info">
                  <span class="progress-text">{{ ((evaluation.processed_images / evaluation.total_images) * 100).toFixed(0) }}% complete</span>
                  <span class="eta-text">{{ getEta(evaluation) }}</span>
                </div>
              }
            </mat-card-content>
            <mat-card-actions>
              @if (evaluation.status === 'completed') {
                <button mat-button (click)="viewResults(evaluation)">
                  <mat-icon>visibility</mat-icon>
                  View Results
                </button>
              }
              <button mat-button color="warn" (click)="deleteEvaluation(evaluation)">
                <mat-icon>delete</mat-icon>
                Delete
              </button>
            </mat-card-actions>

            <!-- Results Panel -->
            @if (selectedEvaluationId === evaluation.id) {
              
              <!-- Confusion Matrix -->
              @if (confusionMatrix()) {
                <div class="matrix-container">
                  <h3 class="section-title">Confusion Matrix</h3>
                  <div class="confusion-matrix">
                    <div class="matrix-cell header"></div>
                    <div class="matrix-cell header">Pred: True</div>
                    <div class="matrix-cell header">Pred: False</div>
                    
                    <div class="matrix-cell header row-header">Actual: True</div>
                    <div class="matrix-cell tp" matTooltip="True Positive: Correctly identified as True">
                      <span class="value">{{ confusionMatrix().tp }}</span>
                      <span class="label">TP</span>
                    </div>
                    <div class="matrix-cell fn" matTooltip="False Negative: Incorrectly identified as False">
                      <span class="value">{{ confusionMatrix().fn }}</span>
                      <span class="label">FN</span>
                    </div>
                    
                    <div class="matrix-cell header row-header">Actual: False</div>
                    <div class="matrix-cell fp" matTooltip="False Positive: Incorrectly identified as True">
                      <span class="value">{{ confusionMatrix().fp }}</span>
                      <span class="label">FP</span>
                    </div>
                    <div class="matrix-cell tn" matTooltip="True Negative: Correctly identified as False">
                      <span class="value">{{ confusionMatrix().tn }}</span>
                      <span class="label">TN</span>
                    </div>
                  </div>
                </div>
              }

              <!-- Prompts Panel -->
              @if (selectedEvaluation) {
                <mat-expansion-panel class="prompts-panel">
                  <mat-expansion-panel-header>
                    <mat-panel-title>
                      <mat-icon>article</mat-icon>
                      Evaluation Prompts
                    </mat-panel-title>
                  </mat-expansion-panel-header>
                  <div class="prompt-content">
                    <div class="prompt-field">
                      <strong>System Message:</strong>
                      <pre>{{ selectedEvaluation.system_message || 'Not specified' }}</pre>
                    </div>
                    <div class="prompt-field">
                      <strong>Question Text:</strong>
                      <pre>{{ selectedEvaluation.question_text || 'Not specified' }}</pre>
                    </div>
                  </div>
                </mat-expansion-panel>
              }

              <!-- Results Table Panel -->
              @if (results().length > 0 || hasMoreResults()) {
                <mat-expansion-panel [expanded]="true">
                  <mat-expansion-panel-header>
                    <mat-panel-title>
                      <mat-icon>table_chart</mat-icon>
                      Results ({{ results().length }} of {{ evaluation.total_images }})
                    </mat-panel-title>
                  </mat-expansion-panel-header>
                  <div class="results-table">
                  <table mat-table [dataSource]="results()">
                    <ng-container matColumnDef="image">
                      <th mat-header-cell *matHeaderCellDef>Image</th>
                      <td mat-cell *matCellDef="let row">{{ row.image_filename }}</td>
                    </ng-container>
                    <ng-container matColumnDef="response">
                      <th mat-header-cell *matHeaderCellDef>Response</th>
                      <td mat-cell *matCellDef="let row" [matTooltip]="row.model_response || ''">{{ row.parsed_answer?.value ?? '-' }}</td>
                    </ng-container>
                    <ng-container matColumnDef="ground_truth">
                      <th mat-header-cell *matHeaderCellDef>Ground Truth</th>
                      <td mat-cell *matCellDef="let row">{{ row.ground_truth?.value ?? '-' }}</td>
                    </ng-container>
                    <ng-container matColumnDef="correct">
                      <th mat-header-cell *matHeaderCellDef>Correct</th>
                      <td mat-cell *matCellDef="let row">
                        @if (row.is_correct === true) {
                          <mat-icon class="correct">check_circle</mat-icon>
                        } @else if (row.is_correct === false) {
                          <mat-icon class="incorrect">cancel</mat-icon>
                        } @else {
                          -
                        }
                      </td>
                    </ng-container>
                    <ng-container matColumnDef="latency">
                      <th mat-header-cell *matHeaderCellDef>Latency</th>
                      <td mat-cell *matCellDef="let row">{{ row.latency_ms ? row.latency_ms + 'ms' : '-' }}</td>
                    </ng-container>
                    <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
                    <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
                  </table>
                  
                  @if (hasMoreResults()) {
                    <div class="load-more-container">
                      <button mat-stroked-button (click)="loadMoreResults()" [disabled]="loadingResults()">
                        @if (loadingResults()) {
                          <mat-icon><mat-spinner diameter="18"></mat-spinner></mat-icon>
                        } @else {
                          <mat-icon>expand_more</mat-icon>
                        }
                        Load More Results
                      </button>
                    </div>
                  }
                </div>
              </mat-expansion-panel>
              }
            }
          </mat-card>
        }
      }
    </div>
  `,
  styles: [`
    .evaluations-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    h1 {
      margin: 0 0 8px;
      color: #202124;
    }

    .subtitle {
      color: #5f6368;
      margin: 0 0 24px;
    }

    .create-card {
      margin-bottom: 24px;
    }

    .form-row {
      display: flex;
      gap: 16px;
      margin-bottom: 8px;

      mat-form-field {
        flex: 1;
      }
    }

    .prompts-section {
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid #e0e0e0;
    }

    .section-title {
      font-size: 14px;
      font-weight: 500;
      color: #5f6368;
      margin: 0 0 12px 0;
    }

    .full-width {
      width: 100%;
    }

    .loading {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px;
      color: #5f6368;

      mat-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        margin-bottom: 16px;
        opacity: 0.5;
      }
    }

    .evaluation-card {
      margin-bottom: 16px;
    }

    .status-row {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 8px;
    }

    .accuracy {
      font-weight: 500;
      color: #1967d2;
    }

    .progress-text {
      text-align: center;
      color: #5f6368;
      margin-top: 8px;
    }

    .progress-info {
      display: flex;
      justify-content: space-between;
      margin-top: 8px;
      font-size: 12px;
      color: #5f6368;
    }

    .eta-text {
      font-style: italic;
    }

    .count-text {
      color: #5f6368;
      font-size: 13px;
    }

    .results-table {
      overflow-x: auto;

      table {
        width: 100%;
      }
    }
    
    .load-more-container {
      display: flex;
      justify-content: center;
      padding: 16px;
    }

    .correct {
      color: #34a853;
    }

    .incorrect {
      color: #ea4335;
    }

    .prompts-panel {
      margin-top: 16px;
      margin-bottom: 8px;
    }

    .prompt-content {
      padding: 16px 0;
    }

    .prompt-field {
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }

      strong {
        display: block;
        margin-bottom: 8px;
        color: #202124;
      }

      pre {
        background: #f8f9fa;
        padding: 12px;
        border-radius: 4px;
        border: 1px solid #e0e0e0;
        white-space: pre-wrap;
        word-break: break-word;
        font-family: inherit;
        font-size: 14px;
        margin: 0;
        color: #5f6368;
      }
    }
    
    .matrix-container {
      padding: 16px;
      background: #fafafa;
      border-radius: 4px;
      margin-bottom: 16px;
      border: 1px solid #eee;
    }
    
    .confusion-matrix {
      display: grid;
      grid-template-columns: auto 1fr 1fr;
      gap: 8px;
      max-width: 400px;
      
      .matrix-cell {
        padding: 12px;
        border-radius: 4px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        
        &.header {
          font-weight: 500;
          color: #5f6368;
          background: transparent;
        }
        
        &.row-header {
          justify-content: flex-start;
          padding-left: 0;
        }
        
        &.tp { background-color: #e6f4ea; color: #137333; }
        &.tn { background-color: #e6f4ea; color: #137333; }
        &.fp { background-color: #fce8e6; color: #c5221f; }
        &.fn { background-color: #fce8e6; color: #c5221f; }
        
        .value {
          font-size: 18px;
          font-weight: bold;
        }
        
        .label {
          font-size: 10px;
          opacity: 0.7;
        }
      }
    }

    mat-panel-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  `]
})
export class EvaluationsComponent implements OnInit {
  evaluations = signal<EvaluationListItem[]>([]);
  projects = signal<ProjectListItem[]>([]);
  datasets = signal<DatasetDetail[]>([]);
  modelConfigs = signal<ModelConfigListItem[]>([]);
  
  // Results State
  results = signal<EvaluationResult[]>([]);
  currentResultOffset = 0;
  loadingResults = signal(false);
  hasMoreResults = signal(false);
  confusionMatrix = signal<any>(null);
  readonly RESULTS_PAGE_SIZE = 50;
  
  loading = signal(true);
  selectedEvaluationId: string | null = null;

  displayedColumns = ['image', 'response', 'ground_truth', 'correct', 'latency'];

  newEval: CreateEvaluation = {
    name: '',
    project_id: '',
    dataset_id: '',
    model_config_id: '',
    system_message: '',
    question_text: ''
  };

  selectedProject: Project | null = null;
  selectedEvaluation: Evaluation | null = null;

  private refreshInterval: any;

  constructor(
    private evaluationsService: EvaluationsService,
    private projectsService: ProjectsService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.loadData();
    // Auto-refresh for running evaluations
    this.refreshInterval = setInterval(() => {
      if (this.evaluations().some(e => e.status === 'running')) {
        this.loadEvaluations();
      }
    }, 3000);
  }

  ngOnDestroy() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  loadData() {
    this.loading.set(true);

    // Load evaluations
    this.evaluationsService.getEvaluations().subscribe({
      next: (evals) => this.evaluations.set(evals),
      error: (err) => console.error('Failed to load evaluations:', err)
    });

    // Load projects
    this.projectsService.getProjects().subscribe({
      next: (projects) => this.projects.set(projects),
      error: (err) => console.error('Failed to load projects:', err)
    });

    // Load model configs
    this.evaluationsService.getModelConfigs().subscribe({
      next: (configs) => {
        this.modelConfigs.set(configs);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load model configs:', err);
        this.loading.set(false);
      }
    });
  }

  loadEvaluations() {
    this.evaluationsService.getEvaluations().subscribe({
      next: (evals) => this.evaluations.set(evals),
      error: (err) => console.error('Failed to refresh evaluations:', err)
    });
  }

  onProjectChange() {
    if (this.newEval.project_id) {
      // Load datasets
      this.projectsService.getDatasets(this.newEval.project_id).subscribe({
        next: (datasets) => {
          this.datasets.set(datasets);
          this.newEval.dataset_id = '';
        },
        error: (err) => console.error('Failed to load datasets:', err)
      });

      // Load project details to pre-populate prompts
      this.projectsService.getProject(this.newEval.project_id).subscribe({
        next: (project) => {
          this.selectedProject = project;
          // Pre-populate system message and question text
          this.newEval.system_message = this.getSystemPrompt(project.question_type, project.question_options);
          this.newEval.question_text = project.question_text;
        },
        error: (err) => console.error('Failed to load project:', err)
      });
    }
  }

  getSystemPrompt(questionType: string, options: string[] | null = null): string {
    const prompts: Record<string, string> = {
      'binary': 'Reply only true or false, nothing else.',
      'multiple_choice': 'Reply only with one of these values: {options}',
      'text': 'Reply as short as you can with classification of what you see.',
      'count': 'Reply only with a number that is a count.',
      'default': 'Answer the question based on the image.'
    };

    let prompt = prompts[questionType] || prompts['default'];

    // Replace {options} placeholder for multiple choice
    if (questionType === 'multiple_choice' && options) {
      const optionsStr = options.join(', ');
      prompt = prompt.replace('{options}', optionsStr);
    }

    return prompt;
  }

  isFormValid(): boolean {
    return !!(this.newEval.name && this.newEval.project_id && this.newEval.dataset_id && this.newEval.model_config_id);
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'completed': return 'primary';
      case 'running': return 'accent';
      case 'failed': return 'warn';
      default: return '';
    }
  }

  getEta(evaluation: EvaluationListItem): string {
    if (evaluation.status !== 'running' || !evaluation.processed_images || !evaluation.total_images) {
      return '';
    }
    
    if (evaluation.processed_images < 2) {
      return 'Calculating ETA...';
    }

    const startTime = new Date(evaluation.created_at).getTime();
    const now = new Date().getTime();
    const elapsedMs = now - startTime;
    
    const msPerImage = elapsedMs / evaluation.processed_images;
    const remainingImages = evaluation.total_images - evaluation.processed_images;
    const remainingMs = remainingImages * msPerImage;

    if (remainingMs < 60000) {
      return `~${Math.ceil(remainingMs / 1000)}s remaining`;
    } else {
      return `~${Math.ceil(remainingMs / 60000)}m remaining`;
    }
  }

  startEvaluation() {
    if (!this.isFormValid()) return;

    this.evaluationsService.createEvaluation(this.newEval).subscribe({
      next: (evaluation) => {
        this.loadEvaluations();
        this.snackBar.open('Evaluation started', 'Close', { duration: 3000 });
        this.newEval = {
          name: '',
          project_id: '',
          dataset_id: '',
          model_config_id: '',
          system_message: '',
          question_text: ''
        };
        this.selectedProject = null;
      },
      error: (err) => {
        console.error('Failed to start evaluation:', err);
        this.snackBar.open('Failed to start evaluation', 'Close', { duration: 3000 });
      }
    });
  }

  viewResults(evaluation: EvaluationListItem) {
    if (this.selectedEvaluationId === evaluation.id) {
      this.selectedEvaluationId = null;
      this.selectedEvaluation = null;
      this.results.set([]);
      this.confusionMatrix.set(null);
      return;
    }

    this.selectedEvaluationId = evaluation.id;
    this.currentResultOffset = 0;
    this.results.set([]);

    // Load full evaluation details (including prompts)
    this.evaluationsService.getEvaluation(evaluation.id).subscribe({
      next: (evalDetails) => {
        this.selectedEvaluation = evalDetails;
        // Set confusion matrix if available
        if (evalDetails.results_summary?.confusion_matrix) {
          this.confusionMatrix.set(evalDetails.results_summary.confusion_matrix);
        } else {
          this.confusionMatrix.set(null);
        }
        this.loadMoreResults();
      },
      error: (err) => {
        console.error('Failed to load evaluation details:', err);
      }
    });
  }

  loadMoreResults() {
    if (!this.selectedEvaluationId || this.loadingResults()) return;
    
    this.loadingResults.set(true);
    
    this.evaluationsService.getEvaluationResults(
      this.selectedEvaluationId, 
      this.currentResultOffset, 
      this.RESULTS_PAGE_SIZE
    ).subscribe({
      next: (results) => {
        this.results.set([...this.results(), ...results]);
        this.currentResultOffset += results.length;
        this.hasMoreResults.set(results.length === this.RESULTS_PAGE_SIZE);
        this.loadingResults.set(false);
      },
      error: (err) => {
        console.error('Failed to load results:', err);
        this.snackBar.open('Failed to load results', 'Close', { duration: 3000 });
        this.loadingResults.set(false);
      }
    });
  }

  deleteEvaluation(evaluation: EvaluationListItem) {
    if (!confirm(`Delete evaluation "${evaluation.name}"?`)) return;

    this.evaluationsService.deleteEvaluation(evaluation.id).subscribe({
      next: () => {
        this.evaluations.set(this.evaluations().filter(e => e.id !== evaluation.id));
        this.snackBar.open('Evaluation deleted', 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Failed to delete evaluation:', err);
        this.snackBar.open('Failed to delete evaluation', 'Close', { duration: 3000 });
      }
    });
  }
}