import { Component, OnInit, signal, OnDestroy } from '@angular/core';
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
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { ProjectsService, Project, DatasetDetail, ImageItem, ProcessingStatus } from '../../core/services/projects.service';
import { EvaluationsService } from '../../core/services/evaluations.service';
import { interval, Subscription } from 'rxjs';
import { switchMap } from 'rxjs/operators';

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
    MatProgressBarModule,
    MatDialogModule
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
                <mat-card-title>Dataset: {{ dataset.name }}</mat-card-title>
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
                  <div class="upload-status">
                    <mat-progress-bar mode="indeterminate"></mat-progress-bar>
                    <p class="status-text">Uploading files to cloud storage...</p>
                  </div>
                }

                <!-- Processing Status (Phase 2: Thumbnail Generation) -->
                @if (processingStatus[dataset.id] && processingStatus[dataset.id]!.processing_status === 'processing') {
                  <div class="processing-status">
                    <div class="status-header">
                      <mat-icon>image</mat-icon>
                      <span>Generating thumbnails...</span>
                    </div>
                    <mat-progress-bar
                      mode="determinate"
                      [value]="processingStatus[dataset.id]!.progress_percent">
                    </mat-progress-bar>
                    <p class="status-text">
                      {{ processingStatus[dataset.id]!.processed_files }} / {{ processingStatus[dataset.id]!.total_files }} images
                      ({{ processingStatus[dataset.id]!.progress_percent }}%)
                    </p>
                  </div>
                }

                <!-- Image Grid -->
                @if (datasetImages[dataset.id]?.length) {
                  <div class="image-grid">
                    @for (image of datasetImages[dataset.id]; track image.id) {
                      <div class="image-item" (click)="openImageDetail(dataset.id, image)">
                        <img [src]="getImageUrl(dataset.id, image)" [alt]="image.filename">
                        <div class="image-overlay">
                          <span class="image-name">{{ image.filename }}</span>
                          <button mat-icon-button color="warn" (click)="deleteImage(dataset.id, image.id); $event.stopPropagation()"
                                  matTooltip="Delete">
                            <mat-icon>delete</mat-icon>
                          </button>
                        </div>
                        
                        <!-- Annotation Status Indicator -->
                        @if (image.is_annotated) {
                          <div class="annotation-status" [class.skipped]="image.is_skipped" [class.flagged]="image.is_flagged">
                            @if (image.is_skipped) {
                              <mat-icon>skip_next</mat-icon>
                              <span>Skipped</span>
                            } @else {
                              <mat-icon>check_circle</mat-icon>
                              <span [class.no-answer]="isNoAnswer(image.annotation_value)">{{ formatAnnotationValue(image.annotation_value) }}</span>
                            }
                            @if (image.is_flagged) {
                              <mat-icon class="flag-icon" matTooltip="Flagged">flag</mat-icon>
                            }
                          </div>
                        }
                      </div>
                    }
                  </div>
                  
                  <!-- Load More Button -->
                  @if (hasMoreImages[dataset.id]) {
                    <div class="load-more-container">
                      <button mat-stroked-button color="primary" 
                              (click)="loadMoreImages(dataset.id)" 
                              [disabled]="loadingImages[dataset.id]">
                        @if (loadingImages[dataset.id]) {
                          <mat-icon><mat-spinner diameter="18"></mat-spinner></mat-icon>
                        } @else {
                          <mat-icon>expand_more</mat-icon>
                        }
                        Load More Images
                      </button>
                    </div>
                  }
                }
              </mat-card-content>
              <mat-card-actions>
                <button mat-button [routerLink]="['/projects', projectId, 'datasets', dataset.id, 'annotate']">
                  <mat-icon>edit_note</mat-icon>
                  Annotate
                </button>
                <button mat-button [routerLink]="['/evaluations']" [queryParams]="{projectId: projectId, datasetId: dataset.id}">
                  <mat-icon>analytics</mat-icon>
                  Evaluate
                </button>
                <button mat-button (click)="refreshDataset(dataset.id)" [disabled]="loadingImages[dataset.id]">
                  <mat-icon>refresh</mat-icon>
                  Refresh
                </button>
                <button mat-button (click)="exportAnnotations(dataset.id)">
                  <mat-icon>download</mat-icon>
                  Export CSV
                </button>
                <button mat-button (click)="downloadTemplate(dataset.id)">
                  <mat-icon>description</mat-icon>
                  Template
                </button>
                <button mat-button (click)="importAnnotations(dataset.id)">
                  <mat-icon>publish</mat-icon>
                  Import CSV
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

    <!-- Image Overlay Modal -->
    @if (selectedImage()) {
      <div class="image-overlay-modal" (click)="closeImageDetail()">
        <div class="overlay-content" (click)="$event.stopPropagation()">
          <div class="overlay-header">
            <h2>{{ selectedImage()!.filename }}</h2>
            <button mat-icon-button (click)="closeImageDetail()">
              <mat-icon>close</mat-icon>
            </button>
          </div>
          
          <div class="overlay-body">
            <div class="image-container">
              @if (selectedImageUrl()) {
                <img [src]="selectedImageUrl()" [alt]="selectedImage()!.filename">
              } @else {
                <mat-spinner></mat-spinner>
              }
            </div>
            
            <div class="details-container">
              <div class="detail-item">
                <span class="label">Dataset:</span>
                <span class="value">{{ getDatasetName(selectedDatasetId()) }}</span>
              </div>

              <div class="detail-item">
                <span class="label">Status:</span>
                <span class="value status-value">
                  @if (selectedImage()!.is_annotated) {
                    @if (selectedImage()!.is_skipped) {
                      <mat-icon class="skipped">skip_next</mat-icon> Skipped
                    } @else {
                      <mat-icon class="annotated">check_circle</mat-icon> Annotated
                    }
                  } @else {
                    <mat-icon>radio_button_unchecked</mat-icon> Not Annotated
                  }
                </span>
              </div>

              @if (selectedImage()!.is_annotated && !selectedImage()!.is_skipped) {
                <div class="detail-item">
                  <span class="label">Answer:</span>
                  <span class="value answer-value" [class.no-answer]="isNoAnswer(selectedImage()!.annotation_value)">{{ formatAnnotationValue(selectedImage()!.annotation_value) }}</span>
                </div>
              }

              @if (selectedImage()!.is_flagged) {
                <div class="detail-item flagged-item">
                  <span class="label"><mat-icon>flag</mat-icon> Flagged</span>
                  <span class="value">This image was flagged during annotation.</span>
                </div>
              }
              
              <div class="actions">
                <button mat-raised-button color="primary" 
                        [routerLink]="['/projects', projectId, 'datasets', selectedDatasetId(), 'annotate']">
                  Go to Annotation
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    }
  `,
  styles: [
    `
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

    .upload-status, .processing-status {
      margin-bottom: 16px;
      padding: 16px;
      background-color: #f8f9fa;
      border-radius: 8px;

      .status-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        font-weight: 500;
        color: #1967d2;

        mat-icon {
          font-size: 20px;
          width: 20px;
          height: 20px;
        }
      }

      .status-text {
        font-size: 14px;
        color: #5f6368;
        margin: 8px 0 0 0;
        text-align: center;
      }

      mat-progress-bar {
        margin-bottom: 8px;
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
      background-color: #f5f5f5;
      cursor: pointer;
      transition: transform 0.2s;

      &:hover {
        transform: scale(1.02);
        z-index: 1;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
      }

      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      .image-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        padding: 4px;
        background: linear-gradient(rgba(0, 0, 0, 0.5), transparent);
        display: flex;
        justify-content: space-between;
        align-items: start;
        opacity: 0;
        transition: opacity 0.2s ease;

        .image-name {
          color: white;
          font-size: 11px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          flex: 1;
          margin: 0;
          padding: 4px;
        }

        button {
          color: white;
          width: 24px;
          height: 24px;
          line-height: 24px;
          .mat-icon { font-size: 18px; }
        }
      }

      &:hover .image-overlay {
        opacity: 1;
      }
      
      .annotation-status {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(255, 255, 255, 0.9);
        padding: 4px 8px;
        font-size: 11px;
        display: flex;
        align-items: center;
        gap: 4px;
        color: #1e8e3e;
        font-weight: 500;
        border-top: 1px solid rgba(0,0,0,0.05);
        
        mat-icon {
          font-size: 14px;
          width: 14px;
          height: 14px;
        }
        
        &.skipped {
          color: #5f6368;
          background: #f1f3f4;
        }
        
        &.flagged {
          background: #fce8e6;
        }
        
        .flag-icon {
          color: #d93025;
          margin-left: auto;
        }
        
        span {
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;

          &.no-answer {
            color: #d93025;
          }
        }
      }
    }

    .load-more-container {
      display: flex;
      justify-content: center;
      margin-top: 24px;
      margin-bottom: 8px;
      
      button {
        min-width: 200px;
      }
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
      
      .annotated { color: #137333; }
      .skipped { color: #5f6368; }
      
      .answer-value {
        font-size: 18px;
        font-weight: 500;

        &.no-answer {
          color: #d93025;
        }
      }

      &.flagged-item {
        color: #d93025;
        background: #fce8e6;
        padding: 12px;
        border-radius: 4px;
        .label { color: #d93025; }
      }
    }
    
    .actions {
      margin-top: 32px;
      display: flex;
      justify-content: center;
    }
  `]
})
export class ProjectDetailComponent implements OnInit, OnDestroy {
  project = signal<Project | null>(null);
  datasets = signal<DatasetDetail[]>([]);
  loading = signal(true);
  newDatasetName = '';
  dragOverDatasetId: string | null = null;
  uploadingDatasetId: string | null = null;
  datasetImages: Record<string, ImageItem[]> = {};
  loadingImages: Record<string, boolean> = {};

  // Pagination state
  datasetOffsets: Record<string, number> = {};
  hasMoreImages: Record<string, boolean> = {};
  readonly PAGE_SIZE = 50;

  // Overlay State
  selectedImage = signal<ImageItem | null>(null);
  selectedDatasetId = signal<string>('');
  selectedImageUrl = signal<string | null>(null);

  // Two-phase upload: Processing status tracking
  processingStatus: Record<string, ProcessingStatus | null> = {};
  pollingSubscriptions: Record<string, Subscription> = {};

  projectId = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private projectsService: ProjectsService,
    private evaluationsService: EvaluationsService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.projectId = this.route.snapshot.paramMap.get('id') || '';
    if (this.projectId) {
      this.loadProject();
    } else {
      this.router.navigate(['/projects']);
    }
    
    // Listen for ESC key to close overlay
    window.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && this.selectedImage()) {
        this.closeImageDetail();
      }
    });
  }

  ngOnDestroy() {
    // Clean up all polling subscriptions
    Object.values(this.pollingSubscriptions).forEach(sub => sub.unsubscribe());
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
        datasets.forEach(d => this.loadImages(d.id, true));
      },
      error: (err) => {
        console.error('Failed to load datasets:', err);
        this.loading.set(false);
      }
    });
  }

  loadImages(datasetId: string, reset: boolean = false) {
    if (this.loadingImages[datasetId]) return;

    this.loadingImages[datasetId] = true;
    
    if (reset) {
      this.datasetOffsets[datasetId] = 0;
      this.datasetImages[datasetId] = [];
      this.hasMoreImages[datasetId] = false;
    }

    const skip = this.datasetOffsets[datasetId] || 0;

    this.projectsService.getImages(this.projectId, datasetId, skip, this.PAGE_SIZE).subscribe({
      next: (images) => {
        if (reset) {
          this.datasetImages[datasetId] = images;
        } else {
          this.datasetImages[datasetId] = [...(this.datasetImages[datasetId] || []), ...images];
        }
        
        // Update offset and check if we have more
        this.datasetOffsets[datasetId] = skip + images.length;
        this.hasMoreImages[datasetId] = images.length === this.PAGE_SIZE;
        
        this.loadingImages[datasetId] = false;
      },
      error: (err) => {
        console.error(`Failed to load images for dataset ${datasetId}:`, err);
        this.loadingImages[datasetId] = false;
      }
    });
  }

  loadMoreImages(datasetId: string) {
    this.loadImages(datasetId, false);
  }

  refreshDataset(datasetId: string) {
    this.loadImages(datasetId, true);
  }

  // ... (createDataset, deleteDataset, upload logic same as before) 
  
  createDataset() {
    if (!this.newDatasetName) return;

    this.projectsService.createDataset(this.projectId, this.newDatasetName).subscribe({
      next: (dataset) => {
        this.datasets.set([...this.datasets(), dataset]);
        this.datasetImages[dataset.id] = [];
        this.datasetOffsets[dataset.id] = 0;
        this.hasMoreImages[dataset.id] = false;
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
        delete this.datasetOffsets[dataset.id];
        delete this.hasMoreImages[dataset.id];
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
    // Two-phase batch upload
    this.uploadingDatasetId = datasetId;

    // Phase 1: Upload to GCS
    this.projectsService.uploadImagesBatch(this.projectId, datasetId, files).subscribe({
      next: (response) => {
        this.uploadingDatasetId = null;

        // Show upload result
        let message = response.message;
        const duration = response.errors && response.errors.length > 0 ? 8000 : 3000;
        const snackBarRef = this.snackBar.open(
          message,
          response.errors && response.errors.length > 0 ? 'Show Errors' : 'Close',
          { duration }
        );

        if (response.errors && response.errors.length > 0) {
          snackBarRef.onAction().subscribe(() => {
            const errorMessage = 'Upload errors:\n\n' + response.errors!.join('\n');
            alert(errorMessage);
          });
        }

        // Phase 2: Start polling for thumbnail generation progress
        if (response.processing_status === 'processing') {
          this.startProcessingStatusPolling(datasetId);
        }
      },
      error: (err) => {
        console.error('Batch upload error:', err);
        this.uploadingDatasetId = null;
        const errorDetail = err.error?.detail || err.message || 'Upload failed';
        this.snackBar.open(errorDetail, 'Close', { duration: 5000 });
      }
    });
  }

  startProcessingStatusPolling(datasetId: string) {
    // Clear any existing subscription
    if (this.pollingSubscriptions[datasetId]) {
      this.pollingSubscriptions[datasetId].unsubscribe();
    }

    // Poll every 2 seconds
    this.pollingSubscriptions[datasetId] = interval(2000).pipe(
      switchMap(() => this.projectsService.getProcessingStatus(this.projectId, datasetId))
    ).subscribe({
      next: (status) => {
        this.processingStatus[datasetId] = status;

        // Stop polling when completed or failed
        if (status.processing_status === 'completed' || status.processing_status === 'failed') {
          if (this.pollingSubscriptions[datasetId]) {
            this.pollingSubscriptions[datasetId].unsubscribe();
            delete this.pollingSubscriptions[datasetId];
          }

          // Refresh images to show thumbnails
          this.loadImages(datasetId, true);

          // Show completion message
          if (status.processing_status === 'completed') {
            this.snackBar.open(
              `Processing complete: ${status.processed_files} images processed`,
              'Close',
              { duration: 3000 }
            );
          } else if (status.processing_status === 'failed') {
            const message = `Processing failed: ${status.failed_files} errors`;
            this.snackBar.open(message, status.errors ? 'Show Errors' : 'Close', { duration: 5000 })
              .onAction().subscribe(() => {
                if (status.errors) {
                  alert('Processing errors:\n\n' + status.errors.join('\n'));
                }
              });
          }
        }
      },
      error: (err) => {
        console.error('Error polling processing status:', err);
        if (this.pollingSubscriptions[datasetId]) {
          this.pollingSubscriptions[datasetId].unsubscribe();
          delete this.pollingSubscriptions[datasetId];
        }
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

  getImageUrl(datasetId: string, image: ImageItem) {
    if (image.thumbnail_url) {
      return image.thumbnail_url;
    }
    return this.projectsService.getImageThumbnailUrl(this.projectId, datasetId, image.id);
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
  
  formatAnnotationValue(value: any): string {
    if (value && typeof value === 'object' && 'value' in value) {
      value = value.value; // Handle nested object from backend
    }
    if (value === true) return 'Yes';
    if (value === false) return 'No';
    return String(value);
  }

  isNoAnswer(value: any): boolean {
    if (value && typeof value === 'object' && 'value' in value) {
      value = value.value; // Handle nested object from backend
    }
    return value === false;
  }

  getDatasetName(id: string): string {
    const dataset = this.datasets().find(d => d.id === id);
    return dataset ? dataset.name : 'Unknown';
  }

  // Import/Export handlers
  exportAnnotations(datasetId: string) {
    this.evaluationsService.exportAnnotations(this.projectId, datasetId);
    this.snackBar.open('Downloading annotations...', 'Close', { duration: 2000 });
  }

  downloadTemplate(datasetId: string) {
    this.evaluationsService.downloadTemplate(this.projectId, datasetId);
    this.snackBar.open('Downloading template...', 'Close', { duration: 2000 });
  }

  importAnnotations(datasetId: string) {
    // ... (Import logic same as before)
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.csv';

    fileInput.onchange = async (event: any) => {
      const file = event.target.files[0];
      if (!file) return;

      try {
        const preview = await this.evaluationsService.previewImport(this.projectId, datasetId, file).toPromise();
        if (!preview) return;

        const message = preview.errors > 0
          ? `Found ${preview.errors} errors. Cannot import.`
          : `Ready to import: ${preview.valid} valid annotations (${preview.create} new, ${preview.update} updates, ${preview.skip} skipped)`;

        const action = preview.errors > 0 ? 'OK' : 'Import';
        const snackBarRef = this.snackBar.open(message, action, {
          duration: preview.errors > 0 ? 5000 : 0
        });

        if (preview.errors === 0) {
          snackBarRef.onAction().subscribe(async () => {
            try {
              const result = await this.evaluationsService.confirmImport(this.projectId, datasetId, file).toPromise();
              this.snackBar.open(`Import complete! ${result?.total || 0} annotations imported.`, 'Close', { duration: 3000 });
              this.loadProject();
            } catch (error: any) {
              this.snackBar.open(`Import failed: ${error.error?.detail || error.message}`, 'Close', { duration: 5000 });
            }
          });
        }
      } catch (error: any) {
        this.snackBar.open(`Validation failed: ${error.error?.detail || error.message}`, 'Close', { duration: 5000 });
      }
    };
    fileInput.click();
  }
  
  openImageDetail(datasetId: string, image: ImageItem) {
    this.selectedDatasetId.set(datasetId);
    this.selectedImage.set(image);
    // Proxy URL for full image
    this.selectedImageUrl.set(`${this.projectsService['API_URL']}/projects/${this.projectId}/datasets/${datasetId}/images/${image.id}/file`);
  }
  
  closeImageDetail() {
    this.selectedImage.set(null);
    this.selectedImageUrl.set(null);
  }
}
