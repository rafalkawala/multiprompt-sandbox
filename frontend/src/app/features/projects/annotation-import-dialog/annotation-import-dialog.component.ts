import { Component, Inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Subject, interval, takeUntil, switchMap, takeWhile } from 'rxjs';
import { EvaluationsService, ImportJobResponse, ImportJobError } from '../../../core/services/evaluations.service';

export interface AnnotationImportDialogData {
  projectId: string;
  datasetId: string;
}

type DialogState = 'upload' | 'processing' | 'summary';

@Component({
  selector: 'app-annotation-import-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatProgressBarModule,
    MatIconModule,
    MatTableModule,
    MatCardModule
  ],
  templateUrl: './annotation-import-dialog.component.html',
  styleUrls: ['./annotation-import-dialog.component.scss']
})
export class AnnotationImportDialogComponent implements OnDestroy {
  state: DialogState = 'upload';
  selectedFile: File | null = null;
  jobId: string | null = null;
  jobStatus: ImportJobResponse | null = null;
  isPolling = false;
  isDragOver = false;
  
  // Stats for display
  progressPercent = 0;
  
  // Error table columns
  displayedColumns: string[] = ['row', 'error'];
  
  private destroy$ = new Subject<void>();

  constructor(
    public dialogRef: MatDialogRef<AnnotationImportDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: AnnotationImportDialogData,
    private evaluationsService: EvaluationsService,
    private snackBar: MatSnackBar
  ) {}

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.validateAndSelectFile(files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.validateAndSelectFile(input.files[0]);
    }
  }

  private validateAndSelectFile(file: File): void {
    if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
      this.snackBar.open('Please select a CSV file', 'Close', { duration: 3000 });
      return;
    }
    this.selectedFile = file;
  }

  startImport(): void {
    if (!this.selectedFile) return;

    this.state = 'processing';
    this.evaluationsService.startImportJob(
      this.data.projectId,
      this.data.datasetId,
      this.selectedFile
    ).subscribe({
      next: (res) => {
        this.jobId = res.job_id;
        this.startPolling();
      },
      error: (err: any) => {
        console.error('Failed to start import', err);
        this.state = 'upload';
        const msg = err.error?.detail || err.message || 'Unknown error';
        this.snackBar.open('Failed to start import: ' + msg, 'Close', { duration: 5000 });
      }
    });
  }

  startPolling(): void {
    if (!this.jobId) return;
    this.isPolling = true;

    // Poll every 1 second
    interval(1000)
      .pipe(
        takeUntil(this.destroy$),
        takeWhile(() => this.isPolling),
        switchMap(() => this.evaluationsService.getImportJobStatus(
          this.data.projectId,
          this.data.datasetId,
          this.jobId!
        ))
      )
      .subscribe({
        next: (status) => {
          this.jobStatus = status;
          this.updateProgress(status);

          if (status.status === 'completed' || status.status === 'failed') {
            this.isPolling = false;
            this.state = 'summary';
          }
        },
        error: (err: any) => {
          console.error('Polling error', err);
          this.isPolling = false;
          // Don't change state immediately on transient error, but maybe warn?
        }
      });
  }

  updateProgress(status: ImportJobResponse): void {
    if (status.total_rows > 0) {
      this.progressPercent = Math.round((status.processed_rows / status.total_rows) * 100);
    } else if (status.status === 'processing') {
      // Indeterminate state if we don't know total yet
      this.progressPercent = 0;
    } else if (status.status === 'completed') {
      this.progressPercent = 100;
    }
  }

  close(): void {
    this.dialogRef.close(this.jobStatus?.status === 'completed');
  }

  downloadErrors(): void {
    if (!this.jobStatus?.errors) return;

    const csvContent = "data:text/csv;charset=utf-8," 
      + "Row,Error\n"
      + this.jobStatus.errors.map((e: ImportJobError) => `${e.row},"${e.error.replace(/"/g, '""')}"`).join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `import_errors_${this.jobId}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
