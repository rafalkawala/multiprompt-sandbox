import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { ProjectsService, Project, DatasetDetail, ImageItem } from '../../core/services/projects.service';

@Component({
  selector: 'app-project-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatCardModule,
    MatChipsModule,
    MatTooltipModule,
    MatInputModule,
    MatFormFieldModule,
    MatExpansionModule,
    MatProgressBarModule
  ],
  template: `
    <div class="project-detail-container">
      @if (loading()) {
        <div class="loading-container">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (project()) {
        <!-- Project Header -->
        <mat-card class="project-header">
          <mat-card-header>
            <mat-card-title>
              <button mat-icon-button routerLink="/projects" matTooltip="Back to Projects">
                <mat-icon>arrow_back</mat-icon>
              </button>
              {{ project()!.name }}
            </mat-card-title>
            <mat-card-subtitle>{{ project()!.description || 'No description' }}</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <div class="project-info">
              <div class="info-item">
                <mat-icon>help_outline</mat-icon>
                <span><strong>Question:</strong> {{ project()!.question_text }}</span>
              </div>
              <div class="info-item">
                <mat-icon>category</mat-icon>
                <span><strong>Type:</strong> {{ formatQuestionType(project()!.question_type) }}</span>
              </div>
              <div class="info-item">
                <mat-icon>folder</mat-icon>
                <span><strong>Datasets:</strong> {{ datasets().length }}</span>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Create Dataset -->
        <mat-card class="create-dataset-card">
          <div class="create-dataset-form">
            <mat-form-field appearance="outline" class="dataset-name-field">
              <mat-label>New Dataset Name</mat-label>
              <input matInput [(ngModel)]="newDatasetName" placeholder="Training Set">
            </mat-form-field>
            <button mat-raised-button color="primary" (click)="createDataset()" [disabled]="!newDatasetName">
              <mat-icon>add</mat-icon>
              Create Dataset
            </button>
          </div>
        </mat-card>

        <!-- Datasets List -->
        @if (datasets().length === 0) {
          <mat-card class="empty-state">
            <mat-icon>folder_open</mat-icon>
            <p>No datasets yet. Create your first dataset above.</p>
          </mat-card>
        } @else {
          @for (dataset of datasets(); track dataset.id) {
            <mat-card class="dataset-card">
              <mat-card-header>
                <mat-card-title>{{ dataset.name }}</mat-card-title>
                <mat-card-subtitle>{{ dataset.image_count }} images</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <!-- Image Upload Area -->
                <div class="upload-area"
                     (dragover)="onDragOver($event)"
                     (dragleave)="onDragLeave($event)"
                     (drop)="onDrop($event, dataset.id)"
                     [class.drag-over]="dragOverDatasetId === dataset.id">
                  <mat-icon>cloud_upload</mat-icon>
                  <p>Drag & drop images here or</p>
                  <input type="file" multiple accept="image/*"
                         [id]="'file-input-' + dataset.id"
                         (change)="onFileSelect($event, dataset.id)"
                         style="display: none">
                  <button mat-stroked-button (click)="triggerFileInput(dataset.id)">
                    Browse Files
                  </button>
                </div>

                <!-- Upload Progress -->
                @if (uploadingDatasetId === dataset.id) {
                  <mat-progress-bar mode="indeterminate"></mat-progress-bar>
                }

                <!-- Image Grid -->
                @if (datasetImages[dataset.id]?.length) {
                  <div class="image-grid">
                    @for (image of datasetImages[dataset.id]; track image.id) {
                      <div class="image-item">
                        <img [src]="getImageUrl(dataset.id, image.id)" [alt]="image.filename">
                        <div class="image-overlay">
                          <span class="image-name">{{ image.filename }}</span>
                          <button mat-icon-button color="warn" (click)="deleteImage(dataset.id, image.id)"
                                  matTooltip="Delete">
                            <mat-icon>delete</mat-icon>
                          </button>
                        </div>
                      </div>
                    }
                  </div>
                }
              </mat-card-content>
              <mat-card-actions>
                <button mat-button [routerLink]="['/projects', projectId, 'datasets', dataset.id, 'annotate']">
                  <mat-icon>edit_note</mat-icon>
                  Annotate
                </button>
                <button mat-button (click)="loadImages(dataset.id)" [disabled]="loadingImages[dataset.id]">
                  <mat-icon>refresh</mat-icon>
                  Refresh
                </button>
                <button mat-button color="warn" (click)="deleteDataset(dataset)">
                  <mat-icon>delete</mat-icon>
                  Delete Dataset
                </button>
              </mat-card-actions>
            </mat-card>
          }
        }
      }
    </div>
  `,
  styles: [`
    .project-detail-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    .project-header {
      margin-bottom: 16px;

      mat-card-title {
        display: flex;
        align-items: center;
        gap: 8px;
      }
    }

    .project-info {
      display: flex;
      flex-wrap: wrap;
      gap: 24px;
      margin-top: 16px;

      .info-item {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #5f6368;

        mat-icon {
          font-size: 20px;
          width: 20px;
          height: 20px;
        }
      }
    }

    .create-dataset-card {
      margin-bottom: 16px;
    }

    .create-dataset-form {
      display: flex;
      gap: 16px;
      align-items: center;
      padding: 8px 0;

      .dataset-name-field {
        flex: 1;
      }
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

    .dataset-card {
      margin-bottom: 16px;
    }

    .upload-area {
      border: 2px dashed #e0e0e0;
      border-radius: 8px;
      padding: 32px;
      text-align: center;
      margin-bottom: 16px;
      transition: all 0.2s ease;

      &.drag-over {
        border-color: #1967d2;
        background-color: #e8f0fe;
      }

      mat-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        color: #9e9e9e;
      }

      p {
        color: #5f6368;
        margin: 8px 0;
      }
    }

    .image-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
      gap: 12px;
      margin-top: 16px;
    }

    .image-item {
      position: relative;
      aspect-ratio: 1;
      border-radius: 8px;
      overflow: hidden;

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      .image-overlay {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
        padding: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        opacity: 0;
        transition: opacity 0.2s ease;

        .image-name {
          color: white;
          font-size: 11px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          flex: 1;
        }

        button {
          color: white;
        }
      }

      &:hover .image-overlay {
        opacity: 1;
      }
    }
  `]
})
export class ProjectDetailComponent implements OnInit {
  project = signal<Project | null>(null);
  datasets = signal<DatasetDetail[]>([]);
  loading = signal(true);
  newDatasetName = '';
  dragOverDatasetId: string | null = null;
  uploadingDatasetId: string | null = null;
  datasetImages: Record<string, ImageItem[]> = {};
  loadingImages: Record<string, boolean> = {};

  projectId = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private projectsService: ProjectsService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.projectId = this.route.snapshot.paramMap.get('id') || '';
    if (this.projectId) {
      this.loadProject();
    } else {
      this.router.navigate(['/projects']);
    }
  }

  loadProject() {
    this.loading.set(true);
    this.projectsService.getProject(this.projectId).subscribe({
      next: (project) => {
        this.project.set(project);
        this.loadDatasets();
      },
      error: (err) => {
        console.error('Failed to load project:', err);
        this.snackBar.open('Failed to load project', 'Close', { duration: 3000 });
        this.router.navigate(['/projects']);
      }
    });
  }

  loadDatasets() {
    this.projectsService.getDatasets(this.projectId).subscribe({
      next: (datasets) => {
        this.datasets.set(datasets);
        this.loading.set(false);
        // Load images for each dataset
        datasets.forEach(d => this.loadImages(d.id));
      },
      error: (err) => {
        console.error('Failed to load datasets:', err);
        this.loading.set(false);
      }
    });
  }

  loadImages(datasetId: string) {
    this.loadingImages[datasetId] = true;
    this.projectsService.getImages(this.projectId, datasetId).subscribe({
      next: (images) => {
        this.datasetImages[datasetId] = images;
        this.loadingImages[datasetId] = false;
      },
      error: () => {
        this.loadingImages[datasetId] = false;
      }
    });
  }

  createDataset() {
    if (!this.newDatasetName) return;

    this.projectsService.createDataset(this.projectId, this.newDatasetName).subscribe({
      next: (dataset) => {
        this.datasets.set([...this.datasets(), dataset]);
        this.datasetImages[dataset.id] = [];
        this.newDatasetName = '';
        this.snackBar.open(`Dataset "${dataset.name}" created`, 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Failed to create dataset:', err);
        this.snackBar.open('Failed to create dataset', 'Close', { duration: 3000 });
      }
    });
  }

  deleteDataset(dataset: DatasetDetail) {
    if (!confirm(`Delete dataset "${dataset.name}"? This will also delete all images.`)) {
      return;
    }

    this.projectsService.deleteDataset(this.projectId, dataset.id).subscribe({
      next: () => {
        this.datasets.set(this.datasets().filter(d => d.id !== dataset.id));
        delete this.datasetImages[dataset.id];
        this.snackBar.open(`Dataset "${dataset.name}" deleted`, 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Failed to delete dataset:', err);
        this.snackBar.open('Failed to delete dataset', 'Close', { duration: 3000 });
      }
    });
  }

  // Drag and drop handlers
  onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    const target = event.currentTarget as HTMLElement;
    const datasetId = target.querySelector('input')?.id.replace('file-input-', '');
    if (datasetId) this.dragOverDatasetId = datasetId;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.dragOverDatasetId = null;
  }

  onDrop(event: DragEvent, datasetId: string) {
    event.preventDefault();
    event.stopPropagation();
    this.dragOverDatasetId = null;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.uploadFiles(datasetId, Array.from(files));
    }
  }

  triggerFileInput(datasetId: string) {
    document.getElementById(`file-input-${datasetId}`)?.click();
  }

  onFileSelect(event: Event, datasetId: string) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.uploadFiles(datasetId, Array.from(input.files));
      input.value = '';
    }
  }

  uploadFiles(datasetId: string, files: File[]) {
    this.uploadingDatasetId = datasetId;

    const uploadedImages: ImageItem[] = [];
    let completedCount = 0;
    let errorCount = 0;

    this.projectsService.uploadImagesInParallel(this.projectId, datasetId, files, 3).subscribe({
      next: (status) => {
        if (status.result && status.result.length > 0) {
          // File upload completed
          uploadedImages.push(...status.result);
          completedCount++;
        } else if (status.error) {
          // File upload failed
          console.error(`Failed to upload ${status.filename}:`, status.error);
          errorCount++;
        }
        // Progress updates are logged but not shown in UI (could add progress bars here)
      },
      complete: () => {
        // All uploads processed
        this.uploadingDatasetId = null;

        if (uploadedImages.length > 0) {
          this.datasetImages[datasetId] = [...(this.datasetImages[datasetId] || []), ...uploadedImages];

          // Update dataset count
          const datasets = this.datasets();
          const idx = datasets.findIndex(d => d.id === datasetId);
          if (idx !== -1) {
            datasets[idx].image_count += uploadedImages.length;
            this.datasets.set([...datasets]);
          }
        }

        // Show summary
        let message = `${completedCount} of ${files.length} uploaded`;
        if (errorCount > 0) {
          message += ` (${errorCount} failed)`;
        }
        this.snackBar.open(message, 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Upload error:', err);
        this.uploadingDatasetId = null;
        this.snackBar.open('Upload failed', 'Close', { duration: 3000 });
      }
    });
  }

  deleteImage(datasetId: string, imageId: string) {
    this.projectsService.deleteImage(this.projectId, datasetId, imageId).subscribe({
      next: () => {
        this.datasetImages[datasetId] = this.datasetImages[datasetId].filter(i => i.id !== imageId);
        // Update dataset count
        const datasets = this.datasets();
        const idx = datasets.findIndex(d => d.id === datasetId);
        if (idx !== -1) {
          datasets[idx].image_count--;
          this.datasets.set([...datasets]);
        }
        this.snackBar.open('Image deleted', 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Failed to delete image:', err);
        this.snackBar.open('Failed to delete image', 'Close', { duration: 3000 });
      }
    });
  }

  getImageUrl(datasetId: string, imageId: string) {
    return this.projectsService.getImageUrl(this.projectId, datasetId, imageId);
  }

  formatQuestionType(type: string): string {
    const types: Record<string, string> = {
      'binary': 'Binary (Yes/No)',
      'multiple_choice': 'Multiple Choice',
      'text': 'Free Text',
      'count': 'Count'
    };
    return types[type] || type;
  }
}
