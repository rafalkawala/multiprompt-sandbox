import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTableModule } from '@angular/material/table';
import { MatExpansionModule } from '@angular/material/expansion';
import { EvaluationsService, EvaluationListItem, ModelConfigListItem, CreateEvaluation, EvaluationResult, Evaluation, PromptStep } from '../../core/services/evaluations.service';
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
    MatExpansionModule,
    MatTooltipModule
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

          <!-- Prompt Chain Builder -->
          @if (newEval.project_id) {
            <div class="prompts-section">
              <div class="section-header">
                <h3 class="section-title">Prompt Chain ({{ (newEval.prompt_chain || []).length }}/5 steps)</h3>
                <button mat-raised-button (click)="addStep()" [disabled]="!canAddStep()">
                  <mat-icon>add</mat-icon>
                  Add Step
                </button>
              </div>

              <!-- If no steps, show prompt -->
              @if (!newEval.prompt_chain || newEval.prompt_chain.length === 0) {
                <mat-card class="empty-chain">
                  <p>No prompt steps yet. Click "Add Step" to begin.</p>
                </mat-card>
              }

              <!-- Step Accordion -->
              @if (newEval.prompt_chain && newEval.prompt_chain.length > 0) {
                <mat-accordion multi>
                  @for (step of newEval.prompt_chain; track step.step_number; let i = $index) {
                    <mat-expansion-panel [expanded]="i === newEval.prompt_chain.length - 1">
                      <mat-expansion-panel-header>
                        <mat-panel-title>
                          Step {{ step.step_number }}
                          @if (step.prompt && step.prompt.length > 0) {
                            <span class="step-preview">: {{ step.prompt.substring(0, 50) }}{{ step.prompt.length > 50 ? '...' : '' }}</span>
                          }
                        </mat-panel-title>
                      </mat-expansion-panel-header>

                      <div class="step-content">
                        <!-- System Message -->
                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>System Message</mat-label>
                          <textarea matInput [(ngModel)]="step.system_message" rows="3"
                            placeholder="Instructions for the model"></textarea>
                          @if (step.step_number === 1) {
                            <mat-hint>This will be copied to subsequent steps</mat-hint>
                          } @else {
                            <mat-hint>Copied from Step 1 (editable)</mat-hint>
                          }
                        </mat-form-field>

                        <!-- Prompt -->
                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>Prompt</mat-label>
                          <textarea matInput [(ngModel)]="step.prompt" rows="2"
                            placeholder="Enter your prompt here"></textarea>
                          @if (step.step_number > 1 && getAvailableVariables(step.step_number).length > 0) {
                            <mat-hint>
                              Available variables:
                              @for (variable of getAvailableVariables(step.step_number); track variable) {
                                <code class="variable-hint">{{ variable }}</code>
                              }
                            </mat-hint>
                          }
                        </mat-form-field>

                        <!-- Remove Button -->
                        <div class="step-actions">
                          <button mat-stroked-button color="warn" (click)="removeStep(i)">
                            <mat-icon>delete</mat-icon>
                            Remove Step
                          </button>
                        </div>
                      </div>
                    </mat-expansion-panel>
                  }
                </mat-accordion>
              }
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

              <!-- Confusion Matrix for Binary Projects -->
              @if (isBinaryProject() && confusionMatrix()) {
                <div class="confusion-matrix-container">
                  <h4>Confusion Matrix</h4>
                  <table class="confusion-matrix">
                    <thead>
                      <tr>
                        <th></th>
                        <th colspan="2">Predicted</th>
                      </tr>
                      <tr>
                        <th>Actual</th>
                        <th>Yes</th>
                        <th>No</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td class="label">Yes</td>
                        <td class="tp">{{ confusionMatrix()!.tp }}</td>
                        <td class="fn">{{ confusionMatrix()!.fn }}</td>
                      </tr>
                      <tr>
                        <td class="label">No</td>
                        <td class="fp">{{ confusionMatrix()!.fp }}</td>
                        <td class="tn">{{ confusionMatrix()!.tn }}</td>
                      </tr>
                    </tbody>
                  </table>
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

              <!-- Filter Chips -->
              <div class="filters-row">
                <span class="filter-label">Filter Results:</span>
                <mat-chip-listbox aria-label="Result Filters">
                  @for (filter of filterOptions; track filter.value) {
                    <mat-chip-option 
                      [selected]="activeFilter() === filter.value"
                      (selectionChange)="setFilter(filter.value)">
                      {{ filter.label }}
                    </mat-chip-option>
                  }
                </mat-chip-listbox>
              </div>

              <!-- Results Section -->
              @if (showResults()) {
                <!-- Results Table Panel -->
                @if (results().length > 0 || hasMoreResults()) {
                  <mat-expansion-panel [expanded]="true">
                    <mat-expansion-panel-header>
                      <mat-panel-title>
                        <mat-icon>table_chart</mat-icon>
                        Results ({{ results().length }} loaded)
                      </mat-panel-title>
                    </mat-expansion-panel-header>
                    <div class="results-table">
                    <table mat-table [dataSource]="results()">
                      <ng-container matColumnDef="image">
                        <th mat-header-cell *matHeaderCellDef>Image</th>
                        <td mat-cell *matCellDef="let row" class="clickable-cell" (click)="openResultDetail(row)">
                          {{ row.image_filename }}
                        </td>
                      </ng-container>
                      <ng-container matColumnDef="response">
                        <th mat-header-cell *matHeaderCellDef>Response</th>
                        <td mat-cell *matCellDef="let row" [matTooltip]="row.model_response || ''" class="clickable-cell" (click)="openResultDetail(row)">
                          {{ row.parsed_answer?.value ?? '-' }}
                        </td>
                      </ng-container>
                      <ng-container matColumnDef="ground_truth">
                        <th mat-header-cell *matHeaderCellDef>Ground Truth</th>
                        <td mat-cell *matCellDef="let row" class="clickable-cell" (click)="openResultDetail(row)">
                          {{ row.ground_truth?.value ?? '-' }}
                        </td>
                      </ng-container>
                      <ng-container matColumnDef="correct">
                        <th mat-header-cell *matHeaderCellDef>Correct</th>
                        <td mat-cell *matCellDef="let row" class="clickable-cell" (click)="openResultDetail(row)">
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
                        <td mat-cell *matCellDef="let row" class="clickable-cell" (click)="openResultDetail(row)">
                          {{ row.latency_ms ? row.latency_ms + 'ms' : '-' }}
                        </td>
                      </ng-container>
                      <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
                      <tr mat-row *matRowDef="let row; columns: displayedColumns;" class="clickable-row"></tr>
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
                } @else if (!loadingResults()) {
                  <div class="no-results">No results match the selected filter.</div>
                }
              } @else {
                <!-- Unhide Results Button -->
                <div class="unhide-results-container">
                  <button mat-raised-button color="primary" (click)="showResults.set(true); loadMoreResults()">
                    <mat-icon>visibility</mat-icon>
                    Show Results
                  </button>
                </div>
              }
            }
          </mat-card>
        }
      }
    </div>

    <!-- Image Overlay Modal -->
    @if (selectedResult()) {
      <div class="image-overlay-modal" (click)="closeResultDetail()">
        <div class="overlay-content" (click)="$event.stopPropagation()">
          <div class="overlay-header">
            <h2>{{ selectedResult()!.image_filename }}</h2>
            <button mat-icon-button (click)="closeResultDetail()">
              <mat-icon>close</mat-icon>
            </button>
          </div>
          
          <div class="overlay-body">
            <div class="image-container">
              @if (selectedImageUrl()) {
                <img [src]="selectedImageUrl()" [alt]="selectedResult()!.image_filename">
              } @else {
                <mat-spinner></mat-spinner>
              }
            </div>
            
            <div class="details-container">
              <div class="detail-item" [class.correct]="selectedResult()!.is_correct" [class.incorrect]="selectedResult()!.is_correct === false">
                <span class="label">Status:</span>
                <span class="value">
                  @if (selectedResult()!.is_correct === true) {
                    <mat-icon class="inline-icon">check_circle</mat-icon> Correct
                  } @else if (selectedResult()!.is_correct === false) {
                    <mat-icon class="inline-icon">cancel</mat-icon> Incorrect
                  } @else {
                    Unknown
                  }
                </span>
              </div>

              <div class="detail-item">
                <span class="label">Ground Truth:</span>
                <span class="value">{{ selectedResult()!.ground_truth?.value ?? 'N/A' }}</span>
              </div>

              <div class="detail-item">
                <span class="label">Model Prediction:</span>
                <span class="value">{{ selectedResult()!.parsed_answer?.value ?? 'N/A' }}</span>
              </div>

              <div class="detail-item">
                <span class="label">Full Response:</span>
                <pre class="response-text">{{ selectedResult()!.model_response }}</pre>
              </div>
              
              <div class="detail-item">
                <span class="label">Latency:</span>
                <span class="value">{{ selectedResult()!.latency_ms }} ms</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    }
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
    
    .clickable-row {
      cursor: pointer;
      transition: background-color 0.2s;
      &:hover {
        background-color: #f5f5f5;
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
    
    .confusion-matrix-container {
      margin: 16px 0;
      padding: 16px;
      background: #f8f9fa;
      border-radius: 8px;
      border: 1px solid #e0e0e0;

      h4 {
        margin: 0 0 12px 0;
        font-size: 14px;
        font-weight: 500;
        color: #202124;
      }
    }

    .confusion-matrix {
      border-collapse: separate;
      border-spacing: 4px;
      margin: 0;

      th {
        font-weight: 500;
        font-size: 12px;
        color: #5f6368;
        text-align: center;
        padding: 8px 12px;

        &:first-child {
          text-align: left;
        }
      }

      td {
        text-align: center;
        padding: 12px 16px;
        font-size: 16px;
        font-weight: 500;
        border-radius: 4px;

        &.label {
          font-size: 12px;
          font-weight: 500;
          color: #5f6368;
          background: transparent;
          text-align: left;
          padding-left: 0;
        }

        &.tp {
          background-color: #e6f4ea;
          color: #137333;
        }

        &.tn {
          background-color: #e6f4ea;
          color: #137333;
        }

        &.fp {
          background-color: #fce8e6;
          color: #c5221f;
        }

        &.fn {
          background-color: #fce8e6;
          color: #c5221f;
        }
      }
    }

    mat-panel-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    /* Filter Styles */
    .filters-row {
      display: flex;
      align-items: center;
      gap: 16px;
      margin: 16px 0;
      
      .filter-label {
        font-weight: 500;
        color: #5f6368;
      }
    }
    
    .no-results {
      padding: 32px;
      text-align: center;
      color: #5f6368;
      background: #f8f9fa;
      border-radius: 4px;
      margin-top: 16px;
    }

    .unhide-results-container {
      display: flex;
      justify-content: center;
      padding: 24px;
      margin-top: 16px;
    }
    
    /* Overlay Modal Styles */
    .image-overlay-modal {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.8);
      z-index: 1000;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 24px;
    }
    
    .overlay-content {
      background: white;
      border-radius: 8px;
      width: 100%;
      max-width: 1200px;
      height: 90vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
    }
    
    .overlay-header {
      padding: 16px 24px;
      border-bottom: 1px solid #e0e0e0;
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      h2 {
        margin: 0;
        font-size: 18px;
      }
    }
    
    .overlay-body {
      flex: 1;
      display: flex;
      overflow: hidden;
    }
    
    .image-container {
      flex: 2;
      background: #000;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 16px;
      
      img {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
      }
    }
    
    .details-container {
      flex: 1;
      padding: 24px;
      overflow-y: auto;
      border-left: 1px solid #e0e0e0;
      background: #f8f9fa;
      min-width: 300px;
      max-width: 400px;
    }
    
    .detail-item {
      margin-bottom: 24px;
      
      .label {
        display: block;
        font-size: 12px;
        text-transform: uppercase;
        color: #5f6368;
        margin-bottom: 8px;
        font-weight: 500;
      }
      
      .value {
        font-size: 16px;
        color: #202124;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      
      .response-text {
        background: white;
        padding: 12px;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        white-space: pre-wrap;
        font-size: 14px;
        margin: 0;
      }
      
      .inline-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
      
      &.correct .value { color: #34a853; }
      &.incorrect .value { color: #ea4335; }
    }

    /* Multi-phase prompting styles */
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .empty-chain {
      padding: 24px;
      text-align: center;
      color: #5f6368;
      background: #f8f9fa;
      margin-bottom: 16px;
    }

    .step-content {
      padding: 16px 0;
    }

    .step-preview {
      color: #5f6368;
      font-size: 14px;
      margin-left: 8px;
    }

    .step-actions {
      display: flex;
      justify-content: flex-end;
      margin-top: 8px;
    }

    .variable-hint {
      background: #e8f0fe;
      color: #1967d2;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 12px;
      margin-right: 4px;
      font-family: 'Courier New', monospace;
    }

    mat-accordion {
      margin-bottom: 16px;
    }

    mat-expansion-panel {
      margin-bottom: 8px !important;
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
  activeFilter = signal<string>('all');
  showResults = signal(false);
  readonly RESULTS_PAGE_SIZE = 50;
  
  // Overlay State
  selectedResult = signal<EvaluationResult | null>(null);
  selectedImageUrl = signal<string | null>(null);
  
  loading = signal(true);
  selectedEvaluationId: string | null = null;

  displayedColumns = ['image', 'response', 'ground_truth', 'correct', 'latency'];

  newEval: CreateEvaluation = {
    name: '',
    project_id: '',
    dataset_id: '',
    model_config_id: '',
    prompt_chain: []  // Multi-phase prompting
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

    // Listen for ESC key to close overlay
    window.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && this.selectedResult()) {
        this.closeResultDetail();
      }
    });
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
          // Initialize with first step if prompt_chain is empty
          if (!this.newEval.prompt_chain || this.newEval.prompt_chain.length === 0) {
            this.newEval.prompt_chain = [{
              step_number: 1,
              system_message: this.getSystemPrompt(project.question_type, project.question_options),
              prompt: project.question_text
            }];
          }
        },
        error: (err) => console.error('Failed to load project:', err)
      });
    }
  }

  // Multi-phase prompting methods
  addStep() {
    if (!this.newEval.prompt_chain) {
      this.newEval.prompt_chain = [];
    }

    const stepNum = this.newEval.prompt_chain.length + 1;
    const step: PromptStep = {
      step_number: stepNum,
      // Auto-copy system message from step 1 if exists
      system_message: stepNum === 1 ? '' : (this.newEval.prompt_chain[0]?.system_message || ''),
      prompt: ''
    };
    this.newEval.prompt_chain.push(step);
  }

  removeStep(index: number) {
    if (!this.newEval.prompt_chain) return;

    this.newEval.prompt_chain.splice(index, 1);
    // Renumber remaining steps
    this.newEval.prompt_chain.forEach((step, i) => {
      step.step_number = i + 1;
    });
  }

  canAddStep(): boolean {
    return !this.newEval.prompt_chain || this.newEval.prompt_chain.length < 5;
  }

  getAvailableVariables(stepNum: number): string[] {
    const vars: string[] = [];
    for (let i = 1; i < stepNum; i++) {
      vars.push(`{output${i}}`);
    }
    return vars;
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
    const basicFieldsValid = !!(this.newEval.name && this.newEval.project_id && this.newEval.dataset_id && this.newEval.model_config_id);
    const hasPromptChain = !!(this.newEval.prompt_chain && this.newEval.prompt_chain.length > 0);
    return basicFieldsValid && hasPromptChain;
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
      this.showResults.set(false);
      return;
    }

    this.selectedEvaluationId = evaluation.id;
    this.currentResultOffset = 0;
    this.activeFilter.set('all'); // Reset filter
    this.results.set([]);
    this.showResults.set(false); // Don't show results initially

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
        // Don't load results automatically - wait for user to click filter or unhide button
      },
      error: (err) => {
        console.error('Failed to load evaluation details:', err);
      }
    });
  }

  loadMoreResults() {
    if (!this.selectedEvaluationId || this.loadingResults()) return;
    
    this.loadingResults.set(true);
    
    // Pass filter to backend (implemented in next step, currently handled by service)
    this.evaluationsService.getEvaluationResults(
      this.selectedEvaluationId, 
      this.currentResultOffset, 
      this.RESULTS_PAGE_SIZE,
      this.activeFilter() 
    ).subscribe({
      next: (results) => {
        if (this.currentResultOffset === 0) {
          this.results.set(results);
        } else {
          this.results.set([...this.results(), ...results]);
        }
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

  setFilter(filter: string) {
    if (this.activeFilter() === filter) return;

    this.activeFilter.set(filter);
    this.currentResultOffset = 0;
    this.results.set([]); // Clear current results
    this.showResults.set(true); // Show results when filter is clicked
    this.loadMoreResults(); // Reload with new filter
  }

  openResultDetail(result: EvaluationResult) {
    this.selectedResult.set(result);
    if (this.selectedEvaluation) {
       // Get full image URL (using proxy)
       this.selectedImageUrl.set(`${this.projectsService['API_URL']}/projects/${this.selectedEvaluation.project_id}/datasets/${this.selectedEvaluation.dataset_id}/images/${result.image_id}/file`);
    }
  }

  closeResultDetail() {
    this.selectedResult.set(null);
    this.selectedImageUrl.set(null);
  }

  isBinaryProject(): boolean {
    const project = this.projects().find(p => p.id === this.selectedEvaluation?.project_id);
    return project?.question_type === 'binary';
  }

  // Helper for template
  get filterOptions() {
    return [
      { label: 'All', value: 'all' },
      { label: 'Correct', value: 'correct' },
      { label: 'Incorrect', value: 'incorrect' },
      { label: 'False Positive', value: 'fp' },
      { label: 'False Negative', value: 'fn' },
      { label: 'True Positive', value: 'tp' },
      { label: 'True Negative', value: 'tn' }
    ];
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