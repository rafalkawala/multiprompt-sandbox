import { Component, Inject, signal, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { EvaluationsService, ImportJobResponse } from '../../../core/services/evaluations.service';
import { interval, Subscription } from 'rxjs';
import { exhaustMap } from 'rxjs/operators';

@Component({
  selector: 'app-annotation-import-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatListModule,
    MatProgressSpinnerModule,
    MatSnackBarModule
  ],
  templateUrl: './annotation-import-dialog.component.html',
  styleUrls: ['./annotation-import-dialog.component.scss']
})
export class AnnotationImportDialogComponent implements OnDestroy {
  currentStep = signal(0);
  selectedFile = signal<File | null>(null);
  loading = signal(false);
  isDragOver = signal(false);
  
  jobId = signal<string | null>(null);
  jobStatus = signal<ImportJobResponse | null>(null);
  
  private pollSubscription: Subscription | null = null;

  constructor(
    private dialogRef: MatDialogRef<AnnotationImportDialogComponent>,
    private evaluationsService: EvaluationsService,
    private snackBar: MatSnackBar,
    @Inject(MAT_DIALOG_DATA) public data: { projectId: string, datasetId: string }
  ) {}

  ngOnDestroy() {
    this.stopPolling();
  }

  // File Handling
  onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(true);
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);

    if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
      const file = event.dataTransfer.files[0];
      if (file.type === 'text/csv' || file.name.toLowerCase().endsWith('.csv')) {
        this.selectedFile.set(file);
      } else {
        this.snackBar.open('Please upload a valid CSV file', 'Close', { duration: 3000 });
      }
    }
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.selectedFile.set(file);
    }
  }

  clearFile(event: Event) {
    event.stopPropagation();
    this.selectedFile.set(null);
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  // Import Process
  startImport() {
    const file = this.selectedFile();
    if (!file) return;

    this.loading.set(true);

    this.evaluationsService.startImportJob(
      this.data.projectId,
      this.data.datasetId,
      file
    ).subscribe({
      next: (res) => {
        this.jobId.set(res.job_id);
        this.currentStep.set(1); // Move to processing step
        this.startPolling(res.job_id);
        this.loading.set(false);
      },
      error: (err) => {
        console.error("Import failed to start", err);
        const errorMsg = err.error?.detail || err.message || 'Unknown error';
        this.snackBar.open(`Failed to upload file: ${errorMsg}`, 'Close', { duration: 5000 });
        this.loading.set(false);
      }
    });
  }

  startPolling(jobId: string) {
    // Use exhaustMap to wait for the request to complete before sending the next one
    this.pollSubscription = interval(1000).pipe(
      exhaustMap(() => this.evaluationsService.getImportJobStatus(
        this.data.projectId,
        this.data.datasetId,
        jobId
      ))
    ).subscribe({
      next: (status) => {
        this.jobStatus.set(status);

        if (status.status === 'completed' || status.status === 'failed') {
          this.stopPolling();
        }
      },
      error: (err) => {
        console.error("Polling error", err);
        // Don't stop polling on transient network errors
      }
    });
  }

  stopPolling() {
    if (this.pollSubscription) {
      this.pollSubscription.unsubscribe();
      this.pollSubscription = null;
    }
  }

  getProgressPercent(): number {
    const status = this.jobStatus();
    if (!status || !status.total_rows) return 0;
    // Prevent division by zero
    if (status.total_rows === 0) return 0;

    return Math.min(100, (status.processed_rows / status.total_rows) * 100);
  }

  isCompleted(): boolean {
    const s = this.jobStatus()?.status;
    return s === 'completed' || s === 'failed';
  }

  // Error Reporting
  downloadErrorReport() {
    const status = this.jobStatus();
    if (!status || !status.errors || status.errors.length === 0) return;

    // Create CSV content
    const headers = ['Row', 'Error'];
    const rows = status.errors.map(err => `${err.row},"${err.error.replace(/"/g, '""')}"`);
    const csvContent = [headers.join(','), ...rows].join('\n');

    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `import_errors_${this.data.datasetId}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}
