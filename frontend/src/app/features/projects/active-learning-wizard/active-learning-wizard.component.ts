import { Component, Inject, OnInit, signal } from '@angular/core';
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
import { ProjectsService, DatasetSplit, CreateSplitRequest } from '../../core/services/projects.service';

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
    MatStepperModule
  ],
  template: `
    <h2 mat-dialog-title>Smart Annotation Wizard</h2>
    <mat-dialog-content>
      <div class="wizard-container">
        <!-- Mode Selection -->
        <div class="section">
          <h3>1. Choose Sampling Strategy</h3>
          <p class="description">Select a subset of images to annotate. This allows you to validate model performance on a small sample before running it on the entire dataset.</p>

          <mat-radio-group [(ngModel)]="samplingMode" class="radio-group">
            <mat-radio-button value="random_percent">Random Percentage</mat-radio-button>
            <mat-radio-button value="random_count">Fixed Count</mat-radio-button>
          </mat-radio-group>

          @if (samplingMode === 'random_percent') {
            <div class="input-row">
              <mat-label>Percentage: {{ percentValue }}%</mat-label>
              <mat-slider min="1" max="100" step="1" showTickMarks discrete>
                <input matSliderThumb [(ngModel)]="percentValue">
              </mat-slider>
            </div>
          }

          @if (samplingMode === 'random_count') {
            <mat-form-field appearance="outline">
              <mat-label>Number of Images</mat-label>
              <input matInput type="number" [(ngModel)]="countValue" min="1">
            </mat-form-field>
          }
        </div>

        <!-- Exclusion Logic (Next 5%) -->
        <div class="section">
          <h3>2. Exclude Previous Splits (Optional)</h3>
          <p class="description">Exclude images that were already included in previous splits (e.g., to create a "Next 5%" batch).</p>

          @if (loadingSplits()) {
            <mat-spinner diameter="30"></mat-spinner>
          } @else if (existingSplits().length > 0) {
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Exclude Splits</mat-label>
              <mat-select multiple [(ngModel)]="excludedSplitIds">
                @for (split of existingSplits(); track split.id) {
                  <mat-option [value]="split.id">{{ split.name }} ({{ split.image_ids.length }} images)</mat-option>
                }
              </mat-select>
            </mat-form-field>
          } @else {
            <p class="hint">No previous splits found.</p>
          }
        </div>

        <!-- Naming -->
        <div class="section">
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Split Name</mat-label>
            <input matInput [(ngModel)]="splitName" placeholder="e.g. Round 1 Sample">
          </mat-form-field>
        </div>

      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Cancel</button>
      <button mat-raised-button color="primary" (click)="createSplit()" [disabled]="creating() || !splitName">
        @if (creating()) {
          <mat-spinner diameter="20"></mat-spinner>
        } @else {
          Create & Start Annotating
        }
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    .wizard-container {
      padding: 16px 0;
      min-width: 500px;
    }
    .section {
      margin-bottom: 24px;

      h3 { margin-top: 0; margin-bottom: 8px; font-size: 16px; color: #202124; }
      .description { margin: 0 0 16px; color: #5f6368; font-size: 14px; }
      .hint { color: #5f6368; font-style: italic; }
    }
    .radio-group {
      display: flex;
      gap: 24px;
      margin-bottom: 16px;
    }
    .input-row {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .full-width {
      width: 100%;
    }
  `]
})
export class ActiveLearningWizardComponent implements OnInit {
  samplingMode = 'random_percent'; // 'random_percent' | 'random_count'
  percentValue = 5;
  countValue = 100;

  existingSplits = signal<DatasetSplit[]>([]);
  excludedSplitIds: string[] = [];

  splitName = 'New Sample';

  loadingSplits = signal(false);
  creating = signal(false);

  constructor(
    public dialogRef: MatDialogRef<ActiveLearningWizardComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { projectId: string, datasetId: string },
    private projectsService: ProjectsService
  ) {}

  ngOnInit() {
    this.loadSplits();
  }

  loadSplits() {
    this.loadingSplits.set(true);
    this.projectsService.getDatasetSplits(this.data.projectId, this.data.datasetId).subscribe({
      next: (splits) => {
        this.existingSplits.set(splits);
        this.loadingSplits.set(false);

        // Auto-generate name based on previous count
        this.splitName = `Sample Set ${splits.length + 1}`;
      },
      error: (e) => {
        console.error("Failed to load splits", e);
        this.loadingSplits.set(false);
      }
    });
  }

  createSplit() {
    this.creating.set(true);

    const request: CreateSplitRequest = {
      name: this.splitName,
      split_type: this.samplingMode,
      split_value: this.samplingMode === 'random_percent' ? this.percentValue : this.countValue,
      excluded_split_ids: this.excludedSplitIds.length > 0 ? this.excludedSplitIds : undefined
    };

    this.projectsService.createDatasetSplit(this.data.projectId, this.data.datasetId, request).subscribe({
      next: (split) => {
        this.creating.set(false);
        this.dialogRef.close(split);
      },
      error: (e) => {
        console.error("Failed to create split", e);
        this.creating.set(false);
        // Show error?
      }
    });
  }
}
