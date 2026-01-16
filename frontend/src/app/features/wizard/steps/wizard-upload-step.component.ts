import { Component, EventEmitter, Output, signal, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ProjectsService } from '../../../core/services/projects.service';
import { WizardService } from '../wizard.service';
import { interval, Subscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

@Component({
  selector: 'app-wizard-upload-step',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule
  ],
  template: `
    <div class="step-content">
      <h3>Upload your Images</h3>
      <p>Drag and drop images here, or browse your computer. We'll create a dataset for you.</p>

      <div class="upload-zone"
           (dragover)="onDragOver($event)"
           (dragleave)="onDragLeave($event)"
           (drop)="onDrop($event)"
           [class.drag-over]="isDragging">

        <mat-icon class="upload-icon">cloud_upload</mat-icon>
        <p>Drop images here</p>
        <button mat-stroked-button color="primary" (click)="fileInput.click()">
          Browse Files
        </button>
        <input #fileInput type="file" multiple accept="image/*" style="display:none" (change)="onFileSelect($event)">
      </div>

      @if (uploading()) {
        <div class="progress-section">
          <p>Uploading {{ uploadCount() }} files...</p>
          <mat-progress-bar mode="indeterminate"></mat-progress-bar>
        </div>
      }

      @if (processing()) {
        <div class="progress-section">
           <p>Processing images (thumbnails, validation)... {{ processedCount() }} / {{ uploadCount() }}</p>
           <mat-progress-bar mode="determinate" [value]="processedPercent()"></mat-progress-bar>
        </div>
      }

      @if (completedUpload()) {
        <div class="success-message">
          <mat-icon>check_circle</mat-icon>
          <span>Uploaded {{ uploadCount() }} images successfully.</span>
        </div>
        <div class="actions">
          <button mat-raised-button color="primary" (click)="onContinue()" data-testid="btn-upload-continue">
            Continue
            <mat-icon>arrow_forward</mat-icon>
          </button>
        </div>
      }

      @if (uploadError()) {
        <div class="error-message">
          <mat-icon>error</mat-icon>
          <span>{{ uploadError() }}</span>
          <button mat-stroked-button color="warn" (click)="reset()">
            Try Again
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    .step-content {
      max-width: 600px;
      margin: 0 auto;
      padding: 24px;
    }

    .upload-zone {
      border: 2px dashed #e0e0e0;
      border-radius: 8px;
      padding: 48px;
      text-align: center;
      margin: 24px 0;
      transition: all 0.2s;
      background: #fafafa;

      &.drag-over {
        border-color: #1967d2;
        background: #e8f0fe;
      }

      .upload-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        color: #9e9e9e;
        margin-bottom: 16px;
      }
    }

    .progress-section {
      margin-top: 24px;
      padding: 16px;
      background: #f5f5f5;
      border-radius: 8px;

      p { margin-top: 0; }
    }

    .success-message {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #137333;
      margin: 24px 0;
      font-weight: 500;
    }

    .actions {
      display: flex;
      justify-content: flex-end;
    }

    .error-message {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #c5221f;
      background: #fce8e6;
      padding: 16px;
      border-radius: 8px;
      margin: 24px 0;

      mat-icon { flex-shrink: 0; }
      span { flex: 1; }
    }
  `]
})
export class WizardUploadStepComponent implements OnDestroy {
  @Output() completed = new EventEmitter<void>();

  isDragging = false;
  uploading = signal(false);
  processing = signal(false);
  completedUpload = signal(false);
  uploadCount = signal(0);
  processedCount = signal(0);
  processedPercent = signal(0);
  uploadError = signal<string | null>(null);

  private pollSubscription?: Subscription;

  constructor(
    private wizardService: WizardService,
    private projectsService: ProjectsService,
    private snackBar: MatSnackBar
  ) {}

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFiles(Array.from(files));
    }
  }

  onFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFiles(Array.from(input.files));
    }
  }

  handleFiles(files: File[]) {
    const project = this.wizardService.project;
    if (!project) {
      this.uploadError.set('Error: Project not created yet. Please go back and create a project first.');
      return;
    }

    // Reset error state on new upload
    this.uploadError.set(null);
    this.uploading.set(true);
    this.uploadCount.set(files.length);

    // 1. Create Dataset
    this.projectsService.createDataset(project.id, 'Wizard Upload').subscribe({
      next: (dataset) => {
        this.wizardService.setDataset(dataset);

        // 2. Upload Files
        this.projectsService.uploadImagesBatch(project.id, dataset.id, files).subscribe({
          next: () => {
            this.uploading.set(false);
            this.processing.set(true);
            this.startPolling(project.id, dataset.id);
          },
          error: (err) => {
            console.error('Upload failed', err);
            this.uploading.set(false);
            this.uploadError.set('Upload failed. Please check your network connection and try again.');
          }
        });
      },
      error: (err) => {
        console.error('Dataset creation failed', err);
        this.uploading.set(false);
        this.uploadError.set('Failed to create dataset. Please try again.');
      }
    });
  }

  reset() {
    this.uploading.set(false);
    this.processing.set(false);
    this.completedUpload.set(false);
    this.uploadCount.set(0);
    this.processedCount.set(0);
    this.processedPercent.set(0);
    this.uploadError.set(null);
    this.pollSubscription?.unsubscribe();
  }

  startPolling(projectId: string, datasetId: string) {
    this.pollSubscription = interval(1000).pipe(
      switchMap(() => this.projectsService.getProcessingStatus(projectId, datasetId))
    ).subscribe((status) => {
      this.processedCount.set(status.processed_files);
      this.processedPercent.set(status.progress_percent);

      if (status.processing_status === 'completed' || status.processing_status === 'ready') {
        this.processing.set(false);
        this.completedUpload.set(true);
        this.pollSubscription?.unsubscribe();
      } else if (status.processing_status === 'failed') {
        this.processing.set(false);
        this.uploadError.set('Image processing failed. Some images may be corrupted or in an unsupported format.');
        this.pollSubscription?.unsubscribe();
      }
    });
  }

  onContinue() {
    this.completed.emit();
  }

  ngOnDestroy() {
    this.pollSubscription?.unsubscribe();
  }
}
