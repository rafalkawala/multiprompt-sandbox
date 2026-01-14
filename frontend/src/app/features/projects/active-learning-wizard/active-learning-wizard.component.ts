import { Component, Inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatRadioModule } from '@angular/material/radio';
import { MatSliderModule } from '@angular/material/slider';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatStepperModule } from '@angular/material/stepper';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatCheckboxModule } from '@angular/material/checkbox';
import {
  ProjectsService,
  DatasetSplit,
  CreateSplitRequest,
  SampleSizeCalculation,
  ClusteringStatus
} from '../../core/services/projects.service';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-active-learning-wizard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatRadioModule,
    MatSliderModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatStepperModule,
    MatExpansionModule,
    MatChipsModule,
    MatTooltipModule,
    MatCheckboxModule
  ],
  template: `
    <h2 mat-dialog-title>Smart Annotation Wizard</h2>
    <mat-dialog-content>
      <mat-stepper #stepper linear>

        <!-- Step 1: Annotation Set -->
        <mat-step [completed]="annotationSetCreated()">
          <ng-template matStepLabel>Create Annotation Set</ng-template>
          <div class="step-content">
            <p class="step-description">
              Select a subset of images to annotate manually. This creates your "ground truth" data.
            </p>

            <!-- Sampling Strategy -->
            <div class="section">
              <h4>Sampling Strategy</h4>
              <mat-radio-group [(ngModel)]="samplingMode" class="radio-group">
                <mat-radio-button value="random_percent">
                  🎲 Random Sampling
                </mat-radio-button>
                <mat-radio-button value="k_means_centroid" [disabled]="!clusteringStatus()?.is_clustered">
                  🎯 Diversity Sampling
                  @if (!clusteringStatus()?.is_clustered) {
                    <mat-icon matTooltip="Run clustering first to enable diversity sampling" class="info-icon">info</mat-icon>
                  }
                </mat-radio-button>
              </mat-radio-group>

              @if (!clusteringStatus()?.is_clustered && samplingMode === 'random_percent') {
                <div class="info-banner">
                  <mat-icon>lightbulb</mat-icon>
                  <span>Want to select the most diverse images? Run clustering first!</span>
                  <button mat-stroked-button (click)="runClustering()" [disabled]="clustering()">
                    @if (clustering()) {
                      <mat-spinner diameter="16"></mat-spinner>
                    } @else {
                      Run Clustering
                    }
                  </button>
                </div>
              }
            </div>

            <!-- Sample Size -->
            <div class="section">
              <h4>Sample Size</h4>

              @if (samplingMode === 'random_percent') {
                <div class="slider-container">
                  <mat-label>Percentage: {{ percentValue }}%</mat-label>
                  <mat-slider min="1" max="100" step="1" showTickMarks discrete>
                    <input matSliderThumb [(ngModel)]="percentValue">
                  </mat-slider>
                </div>
              }

              <!-- Statistical Calculator -->
              <mat-expansion-panel class="calculator-panel">
                <mat-expansion-panel-header>
                  <mat-panel-title>
                    <mat-icon>calculate</mat-icon>
                    Statistical Recommendation
                  </mat-panel-title>
                </mat-expansion-panel-header>

                @if (loadingCalculation()) {
                  <mat-spinner diameter="30"></mat-spinner>
                } @else if (sampleCalculation()) {
                  <div class="calculation-result">
                    <div class="result-box">
                      <div class="result-number">{{ sampleCalculation()!.recommended_size }}</div>
                      <div class="result-label">Recommended Samples</div>
                      <div class="result-percentage">({{ sampleCalculation()!.percentage }}%)</div>
                    </div>

                    <p class="formula-explanation">{{ sampleCalculation()!.formula_explanation }}</p>

                    <div class="advanced-params">
                      <mat-form-field appearance="outline">
                        <mat-label>Confidence Level</mat-label>
                        <mat-select [(ngModel)]="confidenceLevel" (ngModelChange)="recalculateSampleSize()">
                          <mat-option [value]="0.90">90%</mat-option>
                          <mat-option [value]="0.95">95% (Recommended)</mat-option>
                          <mat-option [value]="0.99">99%</mat-option>
                        </mat-select>
                      </mat-form-field>

                      <mat-form-field appearance="outline">
                        <mat-label>Margin of Error</mat-label>
                        <mat-select [(ngModel)]="marginOfError" (ngModelChange)="recalculateSampleSize()">
                          <mat-option [value]="0.01">±1%</mat-option>
                          <mat-option [value]="0.03">±3%</mat-option>
                          <mat-option [value]="0.05">±5% (Recommended)</mat-option>
                          <mat-option [value]="0.10">±10%</mat-option>
                        </mat-select>
                      </mat-form-field>

                      <button mat-raised-button color="accent" (click)="applyRecommendedSize()">
                        Apply Recommended Size
                      </button>
                    </div>
                  </div>
                }
              </mat-expansion-panel>
            </div>

            <!-- Exclude Previous Splits -->
            @if (existingSplits().length > 0) {
              <div class="section">
                <h4>Exclude Previous Splits (Optional)</h4>
                <p class="hint">Select splits to exclude (for "Next 5%" workflow)</p>
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Exclude Splits</mat-label>
                  <mat-select multiple [(ngModel)]="excludedSplitIds">
                    @for (split of nonPoolSplits(); track split.id) {
                      <mat-option [value]="split.id">
                        {{ split.name }} ({{ split.image_ids.length }} images)
                        @if (split.purpose === 'test') {
                          <mat-chip class="purpose-chip">Test</mat-chip>
                        }
                      </mat-option>
                    }
                  </mat-select>
                </mat-form-field>
              </div>
            }

            <!-- Split Name -->
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Annotation Set Name</mat-label>
              <input matInput [(ngModel)]="annotationSetName" placeholder="e.g. Round 1 Annotation">
            </mat-form-field>

            <div class="step-actions">
              <button mat-raised-button color="primary" (click)="createAnnotationSet()" [disabled]="creatingAnnotation()">
                @if (creatingAnnotation()) {
                  <mat-spinner diameter="20"></mat-spinner>
                } @else {
                  Create Annotation Set
                }
              </button>
            </div>
          </div>
        </mat-step>

        <!-- Step 2: Test Set (Optional) -->
        <mat-step [completed]="testSetCreated() || testSetSkipped()" [optional]="true">
          <ng-template matStepLabel>Create Test Set (Optional)</ng-template>
          <div class="step-content">
            <p class="step-description">
              Create a small test set to validate your prompts/models. This is separate from the annotation set.
            </p>

            <div class="section">
              <mat-checkbox [(ngModel)]="createTestSetEnabled">
                Create a test set
              </mat-checkbox>

              @if (createTestSetEnabled) {
                <div class="test-set-config">
                  <mat-form-field appearance="outline">
                    <mat-label>Test Set Size</mat-label>
                    <input matInput type="number" [(ngModel)]="testSetSize" min="10" max="100">
                    <mat-hint>Recommended: 20-50 images</mat-hint>
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Test Set Name</mat-label>
                    <input matInput [(ngModel)]="testSetName" placeholder="e.g. Validation Test Set">
                  </mat-form-field>
                </div>
              }
            </div>

            <div class="step-actions">
              @if (createTestSetEnabled) {
                <button mat-raised-button color="primary" (click)="createTestSet()" [disabled]="creatingTest()">
                  @if (creatingTest()) {
                    <mat-spinner diameter="20"></mat-spinner>
                  } @else {
                    Create Test Set
                  }
                </button>
              } @else {
                <button mat-raised-button (click)="skipTestSet()">
                  Skip Test Set
                </button>
              }
            </div>
          </div>
        </mat-step>

        <!-- Step 3: Summary & Unlabeled Pool -->
        <mat-step>
          <ng-template matStepLabel>Review & Finish</ng-template>
          <div class="step-content">
            <p class="step-description">
              Review your dataset splits and create the unlabeled pool.
            </p>

            <div class="summary-section">
              <h4>Split Summary</h4>

              @if (createdAnnotationSplit()) {
                <div class="split-summary-card">
                  <mat-icon class="card-icon">label</mat-icon>
                  <div class="card-content">
                    <div class="card-title">{{ createdAnnotationSplit()!.name }}</div>
                    <div class="card-subtitle">Annotation Set</div>
                    <div class="card-stats">{{ createdAnnotationSplit()!.image_ids.length }} images</div>
                  </div>
                </div>
              }

              @if (createdTestSplit()) {
                <div class="split-summary-card">
                  <mat-icon class="card-icon">verified</mat-icon>
                  <div class="card-content">
                    <div class="card-title">{{ createdTestSplit()!.name }}</div>
                    <div class="card-subtitle">Test Set</div>
                    <div class="card-stats">{{ createdTestSplit()!.image_ids.length }} images</div>
                  </div>
                </div>
              }

              @if (unlabeledPoolInfo()) {
                <div class="split-summary-card unlabeled">
                  <mat-icon class="card-icon">inventory_2</mat-icon>
                  <div class="card-content">
                    <div class="card-title">Unlabeled Pool</div>
                    <div class="card-subtitle">Remaining images for future iterations</div>
                    <div class="card-stats">{{ unlabeledPoolInfo()!.count }} images ({{ unlabeledPoolInfo()!.percentage }}%)</div>
                  </div>
                </div>
              }
            </div>

            <div class="section">
              <button mat-raised-button color="primary" (click)="createUnlabeledPoolAndFinish()" [disabled]="finishing()">
                @if (finishing()) {
                  <mat-spinner diameter="20"></mat-spinner>
                } @else {
                  Create Unlabeled Pool & Finish
                }
              </button>
            </div>
          </div>
        </mat-step>

      </mat-stepper>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="dialogRef.close()">
        @if (wizardCompleted()) { Done } @else { Cancel }
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    .step-content {
      padding: 24px 0;
      min-width: 600px;
    }
    .step-description {
      margin: 0 0 24px;
      color: #5f6368;
      font-size: 14px;
    }
    .section {
      margin-bottom: 24px;

      h4 {
        margin: 0 0 12px;
        font-size: 14px;
        font-weight: 600;
        color: #202124;
      }
    }
    .radio-group {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .info-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
      margin-left: 4px;
      vertical-align: middle;
      color: #5f6368;
    }
    .info-banner {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      background: #e8f0fe;
      border-radius: 8px;
      margin-top: 12px;

      mat-icon { color: #1a73e8; }
      span { flex: 1; font-size: 14px; }
    }
    .slider-container {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 16px;
    }
    .calculator-panel {
      margin-top: 16px;

      mat-panel-title {
        display: flex;
        align-items: center;
        gap: 8px;
      }
    }
    .calculation-result {
      padding: 16px 0;
    }
    .result-box {
      text-align: center;
      padding: 24px;
      background: #f1f3f4;
      border-radius: 8px;
      margin-bottom: 16px;

      .result-number {
        font-size: 48px;
        font-weight: 700;
        color: #1a73e8;
      }
      .result-label {
        font-size: 14px;
        color: #5f6368;
        margin-top: 4px;
      }
      .result-percentage {
        font-size: 18px;
        color: #5f6368;
        margin-top: 4px;
      }
    }
    .formula-explanation {
      font-size: 13px;
      color: #5f6368;
      line-height: 1.6;
      margin: 0 0 16px;
    }
    .advanced-params {
      display: flex;
      gap: 12px;
      align-items: flex-start;

      mat-form-field {
        flex: 1;
      }
    }
    .hint {
      color: #5f6368;
      font-size: 13px;
      font-style: italic;
      margin: 0 0 8px;
    }
    .full-width {
      width: 100%;
    }
    .purpose-chip {
      margin-left: 8px;
      font-size: 11px;
      padding: 2px 6px;
      height: 20px;
      background: #e8f0fe;
      color: #1a73e8;
    }
    .step-actions {
      margin-top: 24px;
      display: flex;
      gap: 12px;
    }
    .test-set-config {
      margin-top: 16px;
      padding-left: 32px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .summary-section {
      margin-bottom: 24px;

      h4 {
        margin-bottom: 16px;
      }
    }
    .split-summary-card {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 16px;
      border: 1px solid #dadce0;
      border-radius: 8px;
      margin-bottom: 12px;

      &.unlabeled {
        background: #f8f9fa;
        border-style: dashed;
      }

      .card-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
        color: #1a73e8;
      }
      .card-content {
        flex: 1;

        .card-title {
          font-size: 16px;
          font-weight: 600;
          color: #202124;
        }
        .card-subtitle {
          font-size: 13px;
          color: #5f6368;
          margin-top: 2px;
        }
        .card-stats {
          font-size: 14px;
          color: #5f6368;
          margin-top: 8px;
        }
      }
    }
  `]
})
export class ActiveLearningWizardComponent implements OnInit {
  // Signals
  existingSplits = signal<DatasetSplit[]>([]);
  clusteringStatus = signal<ClusteringStatus | null>(null);
  sampleCalculation = signal<SampleSizeCalculation | null>(null);

  createdAnnotationSplit = signal<DatasetSplit | null>(null);
  createdTestSplit = signal<DatasetSplit | null>(null);

  loadingSplits = signal(false);
  loadingCalculation = signal(false);
  clustering = signal(false);
  creatingAnnotation = signal(false);
  creatingTest = signal(false);
  finishing = signal(false);

  annotationSetCreated = signal(false);
  testSetCreated = signal(false);
  testSetSkipped = signal(false);
  wizardCompleted = signal(false);

  // Computed
  nonPoolSplits = computed(() =>
    this.existingSplits().filter(s => s.purpose !== 'unlabeled_pool')
  );

  unlabeledPoolInfo = computed(() => {
    const annotation = this.createdAnnotationSplit();
    const test = this.createdTestSplit();

    if (!annotation) return null;

    const annotationCount = annotation.image_ids.length;
    const testCount = test ? test.image_ids.length : 0;
    const total = this.totalDatasetImages;
    const unlabeled = total - annotationCount - testCount;
    const percentage = ((unlabeled / total) * 100).toFixed(1);

    return { count: unlabeled, percentage };
  });

  // Form data
  samplingMode = 'random_percent';
  percentValue = 5;
  countValue = 100;
  excludedSplitIds: string[] = [];
  annotationSetName = '';

  createTestSetEnabled = false;
  testSetSize = 30;
  testSetName = '';

  confidenceLevel = 0.95;
  marginOfError = 0.05;

  totalDatasetImages = 0;

  constructor(
    public dialogRef: MatDialogRef<ActiveLearningWizardComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { projectId: string, datasetId: string },
    private projectsService: ProjectsService
  ) {}

  ngOnInit() {
    this.loadInitialData();
  }

  loadInitialData() {
    this.loadingSplits.set(true);

    forkJoin({
      splits: this.projectsService.getDatasetSplits(this.data.projectId, this.data.datasetId),
      clusteringStatus: this.projectsService.getClusteringStatus(this.data.projectId, this.data.datasetId),
      dataset: this.projectsService.getDataset(this.data.projectId, this.data.datasetId)
    }).subscribe({
      next: (result) => {
        this.existingSplits.set(result.splits);
        this.clusteringStatus.set(result.clusteringStatus);
        this.totalDatasetImages = result.dataset.image_count || 0;

        // Auto-generate names
        const annotationCount = result.splits.filter(s => s.purpose === 'annotation').length;
        this.annotationSetName = `Annotation Set ${annotationCount + 1}`;
        this.testSetName = `Test Set ${annotationCount + 1}`;

        // Calculate recommended sample size
        this.calculateSampleSize();

        this.loadingSplits.set(false);
      },
      error: (e) => {
        console.error("Failed to load initial data", e);
        this.loadingSplits.set(false);
      }
    });
  }

  calculateSampleSize() {
    this.loadingCalculation.set(true);

    this.projectsService.calculateSampleSize(
      this.data.projectId,
      this.data.datasetId,
      this.confidenceLevel,
      this.marginOfError
    ).subscribe({
      next: (result) => {
        this.sampleCalculation.set(result);
        this.loadingCalculation.set(false);
      },
      error: (e) => {
        console.error("Failed to calculate sample size", e);
        this.loadingCalculation.set(false);
      }
    });
  }

  recalculateSampleSize() {
    this.calculateSampleSize();
  }

  applyRecommendedSize() {
    const calc = this.sampleCalculation();
    if (calc) {
      this.percentValue = Math.ceil(calc.percentage);
    }
  }

  runClustering() {
    this.clustering.set(true);

    this.projectsService.performClustering(
      this.data.projectId,
      this.data.datasetId
    ).subscribe({
      next: (result) => {
        console.log("Clustering completed", result);

        // Refresh clustering status
        this.projectsService.getClusteringStatus(this.data.projectId, this.data.datasetId).subscribe({
          next: (status) => {
            this.clusteringStatus.set(status);
            this.clustering.set(false);
          }
        });
      },
      error: (e) => {
        console.error("Clustering failed", e);
        this.clustering.set(false);
        alert(`Clustering failed: ${e.error?.detail || e.message}`);
      }
    });
  }

  createAnnotationSet() {
    this.creatingAnnotation.set(true);

    const request: CreateSplitRequest = {
      name: this.annotationSetName,
      split_type: this.samplingMode,
      split_value: this.samplingMode === 'random_percent' ? this.percentValue : this.countValue,
      purpose: 'annotation',
      excluded_split_ids: this.excludedSplitIds.length > 0 ? this.excludedSplitIds : undefined
    };

    this.projectsService.createDatasetSplit(this.data.projectId, this.data.datasetId, request).subscribe({
      next: (split) => {
        this.createdAnnotationSplit.set(split);
        this.annotationSetCreated.set(true);
        this.creatingAnnotation.set(false);
      },
      error: (e) => {
        console.error("Failed to create annotation set", e);
        this.creatingAnnotation.set(false);
        alert(`Failed to create annotation set: ${e.error?.detail || e.message}`);
      }
    });
  }

  createTestSet() {
    this.creatingTest.set(true);

    const excludeIds = [...this.excludedSplitIds];
    if (this.createdAnnotationSplit()) {
      excludeIds.push(this.createdAnnotationSplit()!.id);
    }

    const request: CreateSplitRequest = {
      name: this.testSetName,
      split_type: 'random_count',
      split_value: this.testSetSize,
      purpose: 'test',
      excluded_split_ids: excludeIds.length > 0 ? excludeIds : undefined
    };

    this.projectsService.createDatasetSplit(this.data.projectId, this.data.datasetId, request).subscribe({
      next: (split) => {
        this.createdTestSplit.set(split);
        this.testSetCreated.set(true);
        this.creatingTest.set(false);
      },
      error: (e) => {
        console.error("Failed to create test set", e);
        this.creatingTest.set(false);
        alert(`Failed to create test set: ${e.error?.detail || e.message}`);
      }
    });
  }

  skipTestSet() {
    this.testSetSkipped.set(true);
  }

  createUnlabeledPoolAndFinish() {
    this.finishing.set(true);

    this.projectsService.createUnlabeledPool(this.data.projectId, this.data.datasetId).subscribe({
      next: (pool) => {
        console.log("Unlabeled pool created", pool);
        this.wizardCompleted.set(true);
        this.finishing.set(false);

        // Return all created splits
        const result = {
          annotationSplit: this.createdAnnotationSplit(),
          testSplit: this.createdTestSplit(),
          unlabeledPool: pool
        };

        this.dialogRef.close(result);
      },
      error: (e) => {
        console.error("Failed to create unlabeled pool", e);
        this.finishing.set(false);

        // If no unlabeled images, that's okay - just finish
        if (e.status === 404) {
          this.wizardCompleted.set(true);
          const result = {
            annotationSplit: this.createdAnnotationSplit(),
            testSplit: this.createdTestSplit(),
            unlabeledPool: null
          };
          this.dialogRef.close(result);
        } else {
          alert(`Failed to create unlabeled pool: ${e.error?.detail || e.message}`);
        }
      }
    });
  }
}
