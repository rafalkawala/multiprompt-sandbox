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
import { MatChipsModule } from '@angular/material/chips';
import { MatTableModule } from '@angular/material/table';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';

import { LabellingJobsService, LabellingJob, CreateLabellingJob, LabellingJobRun, LabellingResult } from '../../core/services/labelling-jobs.service';
import { ProjectsService, ProjectListItem } from '../../core/services/projects.service';
import { EvaluationsService, EvaluationListItem } from '../../core/services/evaluations.service';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-labelling-jobs',
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
    MatChipsModule,
    MatTableModule,
    MatExpansionModule,
    MatTooltipModule,
    MatSlideToggleModule,
    MatDialogModule
  ],
  templateUrl: './labelling-jobs.component.html',
  styleUrls: ['./labelling-jobs.component.scss']
})
export class LabellingJobsComponent implements OnInit {
  jobs = signal<LabellingJob[]>([]);
  projects = signal<ProjectListItem[]>([]);
  evaluations = signal<EvaluationListItem[]>([]);
  selectedJob = signal<LabellingJob | null>(null);
  jobRuns = signal<LabellingJobRun[]>([]);

  // Results viewer
  selectedRun = signal<LabellingJobRun | null>(null);
  jobResults = signal<LabellingResult[]>([]);
  loadingResults = signal(false);
  resultsOffset = 0;
  resultsLimit = 20;
  totalResults = 0;

  loading = signal(false);
  showCreateForm = signal(false);

  newJob: CreateLabellingJob = {
    name: '',
    project_id: '',
    evaluation_id: '',
    gcs_folder_path: '',
    frequency_minutes: 15,
    is_active: true
  };

  constructor(
    private labellingJobsService: LabellingJobsService,
    private projectsService: ProjectsService,
    private evaluationsService: EvaluationsService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.loadProjects();
    this.loadJobs();
  }

  loadProjects(): void {
    this.projectsService.getProjects().subscribe({
      next: (projects) => {
        this.projects.set(projects);
      },
      error: (error) => {
        this.snackBar.open('Failed to load projects', 'Close', { duration: 3000 });
        console.error('Error loading projects:', error);
      }
    });
  }

  loadJobs(): void {
    this.loading.set(true);
    this.labellingJobsService.getLabellingJobs().subscribe({
      next: (jobs) => {
        this.jobs.set(jobs);
        this.loading.set(false);
      },
      error: (error) => {
        this.loading.set(false);
        this.snackBar.open('Failed to load labelling jobs', 'Close', { duration: 3000 });
        console.error('Error loading jobs:', error);
      }
    });
  }

  onProjectChange(): void {
    if (this.newJob.project_id) {
      // Load evaluations for the selected project
      this.evaluationsService.getEvaluations(this.newJob.project_id).subscribe({
        next: (evaluations) => {
          this.evaluations.set(evaluations);
        },
        error: (error) => {
          this.snackBar.open('Failed to load evaluations', 'Close', { duration: 3000 });
          console.error('Error loading evaluations:', error);
        }
      });
    } else {
      this.evaluations.set([]);
    }
  }

  createJob(): void {
    if (!this.newJob.name || !this.newJob.project_id || !this.newJob.evaluation_id || !this.newJob.gcs_folder_path) {
      this.snackBar.open('Please fill in all required fields', 'Close', { duration: 3000 });
      return;
    }

    if (!this.newJob.gcs_folder_path.startsWith('gs://')) {
      this.snackBar.open('GCS path must start with gs://', 'Close', { duration: 3000 });
      return;
    }

    this.loading.set(true);
    this.labellingJobsService.createLabellingJob(this.newJob).subscribe({
      next: (job) => {
        this.loading.set(false);
        this.snackBar.open('Labelling job created successfully!', 'Close', { duration: 3000 });
        this.loadJobs();
        this.showCreateForm.set(false);
        this.resetForm();
      },
      error: (error) => {
        this.loading.set(false);
        this.snackBar.open(`Failed to create job: ${error.error?.detail || error.message}`, 'Close', { duration: 5000 });
        console.error('Error creating job:', error);
      }
    });
  }

  triggerJob(job: LabellingJob): void {
    if (job.status === 'running') {
      this.snackBar.open('Job is already running', 'Close', { duration: 3000 });
      return;
    }

    this.labellingJobsService.triggerJob(job.id).subscribe({
      next: () => {
        this.snackBar.open('Job execution started', 'Close', { duration: 3000 });
        setTimeout(() => this.loadJobs(), 2000);
      },
      error: (error) => {
        this.snackBar.open(`Failed to trigger job: ${error.error?.detail || error.message}`, 'Close', { duration: 5000 });
        console.error('Error triggering job:', error);
      }
    });
  }

  toggleJobActive(job: LabellingJob): void {
    this.labellingJobsService.updateLabellingJob(job.id, {
      is_active: !job.is_active
    }).subscribe({
      next: () => {
        this.snackBar.open(`Job ${job.is_active ? 'deactivated' : 'activated'}`, 'Close', { duration: 3000 });
        this.loadJobs();
      },
      error: (error) => {
        this.snackBar.open('Failed to update job', 'Close', { duration: 3000 });
        console.error('Error updating job:', error);
      }
    });
  }

  deleteJob(job: LabellingJob): void {
    if (!confirm(`Are you sure you want to delete "${job.name}"? This will also delete the associated dataset and all results.`)) {
      return;
    }

    this.labellingJobsService.deleteLabellingJob(job.id).subscribe({
      next: () => {
        this.snackBar.open('Job deleted successfully', 'Close', { duration: 3000 });
        this.loadJobs();
        if (this.selectedJob()?.id === job.id) {
          this.selectedJob.set(null);
        }
      },
      error: (error) => {
        this.snackBar.open('Failed to delete job', 'Close', { duration: 3000 });
        console.error('Error deleting job:', error);
      }
    });
  }

  editJobFrequency(job: LabellingJob): void {
    const newFrequency = prompt(
      `Edit schedule frequency for "${job.name}" (in minutes):`,
      job.frequency_minutes.toString()
    );

    if (newFrequency === null) {
      return; // User cancelled
    }

    const frequencyNum = parseInt(newFrequency, 10);
    if (isNaN(frequencyNum) || frequencyNum < 5 || frequencyNum > 1440) {
      this.snackBar.open('Please enter a valid frequency between 5 and 1440 minutes', 'Close', { duration: 5000 });
      return;
    }

    this.labellingJobsService.updateLabellingJob(job.id, {
      frequency_minutes: frequencyNum
    }).subscribe({
      next: () => {
        this.snackBar.open(`Frequency updated to ${frequencyNum} minutes`, 'Close', { duration: 3000 });
        this.loadJobs();
      },
      error: (error) => {
        this.snackBar.open('Failed to update frequency', 'Close', { duration: 3000 });
        console.error('Error updating job:', error);
      }
    });
  }

  viewJobDetails(job: LabellingJob): void {
    this.selectedJob.set(job);
    this.loadJobRuns(job.id);
  }

  loadJobRuns(jobId: string): void {
    this.labellingJobsService.getJobRuns(jobId, 50, 0).subscribe({
      next: (runs) => {
        this.jobRuns.set(runs);
      },
      error: (error) => {
        this.snackBar.open('Failed to load job runs', 'Close', { duration: 3000 });
        console.error('Error loading job runs:', error);
      }
    });
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'idle': return 'primary';
      case 'running': return 'accent';
      case 'error': return 'warn';
      default: return 'default';
    }
  }

  getRunStatusColor(status: string): string {
    switch (status) {
      case 'completed': return 'primary';
      case 'running': return 'accent';
      case 'failed': return 'warn';
      default: return 'default';
    }
  }

  resetForm(): void {
    this.newJob = {
      name: '',
      project_id: '',
      evaluation_id: '',
      gcs_folder_path: '',
      frequency_minutes: 15,
      is_active: true
    };
    this.evaluations.set([]);
  }

  formatDate(dateString: string | null): string {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleString();
  }

  formatDuration(seconds: number | null): string {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  }

  calculateSuccessRate(job: LabellingJob): number {
    if (job.total_images_processed === 0) return 0;
    return Math.round((job.total_images_labeled / job.total_images_processed) * 100);
  }

  viewRunResults(run: LabellingJobRun): void {
    this.selectedRun.set(run);
    this.jobResults.set([]);
    this.resultsOffset = 0;
    this.totalResults = run.images_labeled;
    this.loadResults();
  }

  loadResults(): void {
    if (!this.selectedRun() || !this.selectedJob()) return;

    this.loadingResults.set(true);
    this.labellingJobsService.getJobResults(
      this.selectedJob()!.id,
      this.selectedRun()!.id,
      this.resultsLimit,
      this.resultsOffset
    ).subscribe({
      next: (results) => {
        this.jobResults.set([...this.jobResults(), ...results]);
        this.loadingResults.set(false);
      },
      error: (error) => {
        this.snackBar.open('Failed to load results', 'Close', { duration: 3000 });
        console.error('Error loading results:', error);
        this.loadingResults.set(false);
      }
    });
  }

  loadMoreResults(): void {
    this.resultsOffset += this.resultsLimit;
    this.loadResults();
  }

  hasMoreResults(): boolean {
    return this.jobResults().length < this.totalResults;
  }

  getImageUrl(imageId: string): string {
    // Generate thumbnail URL
    return `${environment.apiUrl}/images/${imageId}/thumbnail`;
  }
}
