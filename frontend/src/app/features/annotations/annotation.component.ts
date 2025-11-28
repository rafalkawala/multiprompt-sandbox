import { Component, OnInit, signal, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatRadioModule } from '@angular/material/radio';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { EvaluationsService, AnnotationStats } from '../../core/services/evaluations.service';
import { ProjectsService, Project, ImageItem } from '../../core/services/projects.service';

@Component({
  selector: 'app-annotation',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatRadioModule,
    MatCheckboxModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatProgressBarModule,
    MatTooltipModule
  ],
  template: `
    <div class="annotation-container">
      @if (loading()) {
        <div class="loading">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else {
        <!-- Header -->
        <div class="header">
          <div class="header-left">
            <button mat-icon-button [routerLink]="['/projects', projectId]" matTooltip="Back to Project">
              <mat-icon>arrow_back</mat-icon>
            </button>
            <button mat-stroked-button (click)="skipToUnannotated()" matTooltip="Jump to first unannotated image">
              <mat-icon>fast_forward</mat-icon>
              Skip to Unannotated
            </button>
          </div>
          <div class="title">
            <h2>{{ project()?.name }} - Annotation</h2>
            <p>{{ datasetName }}</p>
          </div>
        </div>

        <!-- Progress -->
        <mat-card class="progress-card">
          <div class="stats">
            <span><strong>{{ stats()?.annotated || 0 }}</strong> annotated</span>
            <span><strong>{{ stats()?.skipped || 0 }}</strong> skipped</span>
            <span><strong>{{ stats()?.remaining || 0 }}</strong> remaining</span>
          </div>
          @if (stats()?.total_images) {
            <mat-progress-bar mode="determinate" [value]="getProgress()"></mat-progress-bar>
          }
        </mat-card>

        <!-- Keyboard Shortcuts Help -->
        <div class="shortcuts-help">
          <span class="shortcut-hint" matTooltip="Keyboard shortcuts available">
            <mat-icon>keyboard</mat-icon>
            @if (project()?.question_type === 'binary') {
              <span>Y/N</span>
            }
            <span>Enter • Esc • ← →</span>
          </span>
        </div>

        <!-- Main Content -->
        @if (!currentImage()) {
          <mat-card class="empty-state">
            <mat-icon>check_circle</mat-icon>
            <h3>All Done!</h3>
            <p>All images in this dataset have been annotated.</p>
            <button mat-raised-button color="primary" [routerLink]="['/projects', projectId]">
              Back to Project
            </button>
          </mat-card>
        } @else {
          <div class="annotation-content">
            <!-- Image Display -->
            <mat-card class="image-card">
              <img [src]="getImageUrl()" [alt]="currentImage()?.filename">
              <p class="image-name">{{ currentImage()?.filename }}</p>
            </mat-card>

            <!-- Question & Answer -->
            <mat-card class="answer-card">
              <mat-card-header>
                <mat-card-title>{{ project()?.question_text }}</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <!-- Binary (Yes/No) -->
                @if (project()?.question_type === 'binary') {
                  <mat-radio-group [(ngModel)]="answer" class="binary-group">
                    <mat-radio-button [value]="true">Yes</mat-radio-button>
                    <mat-radio-button [value]="false">No</mat-radio-button>
                  </mat-radio-group>
                }

                <!-- Multiple Choice -->
                @if (project()?.question_type === 'multiple_choice') {
                  <mat-radio-group [(ngModel)]="answer" class="choice-group">
                    @for (option of project()?.question_options || []; track option) {
                      <mat-radio-button [value]="option">{{ option }}</mat-radio-button>
                    }
                  </mat-radio-group>
                }

                <!-- Count -->
                @if (project()?.question_type === 'count') {
                  <mat-form-field appearance="outline" class="count-field">
                    <mat-label>Count</mat-label>
                    <input matInput type="number" [(ngModel)]="answer" min="0">
                  </mat-form-field>
                }

                <!-- Text -->
                @if (project()?.question_type === 'text') {
                  <mat-form-field appearance="outline" class="text-field">
                    <mat-label>Answer</mat-label>
                    <textarea matInput [(ngModel)]="answer" rows="3"></textarea>
                  </mat-form-field>
                }

                <!-- Flag option -->
                <div class="flag-section">
                  <mat-checkbox [(ngModel)]="isFlagged">Flag this image</mat-checkbox>
                  @if (isFlagged) {
                    <mat-form-field appearance="outline" class="flag-reason">
                      <mat-label>Reason (optional)</mat-label>
                      <input matInput [(ngModel)]="flagReason">
                    </mat-form-field>
                  }
                </div>
              </mat-card-content>
              <mat-card-actions>
                <button mat-button (click)="skip()" [disabled]="saving()">
                  <mat-icon>skip_next</mat-icon>
                  Skip
                </button>
                <button mat-raised-button color="primary" (click)="save()" [disabled]="!canSave() || saving()">
                  @if (saving()) {
                    <mat-spinner diameter="20"></mat-spinner>
                  } @else {
                    <mat-icon>save</mat-icon>
                    Save & Next
                  }
                </button>
              </mat-card-actions>
            </mat-card>
          </div>

          <!-- Navigation -->
          <div class="navigation">
            <button mat-button (click)="loadPreviousImage()" [disabled]="imageIndex === 0">
              <mat-icon>arrow_back</mat-icon>
              Previous
            </button>
            <span>{{ imageIndex + 1 }} / {{ allImages().length }}</span>
            <button mat-button (click)="loadNextImage()" [disabled]="imageIndex >= allImages().length - 1">
              Next
              <mat-icon>arrow_forward</mat-icon>
            </button>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .annotation-container {
      padding: 24px;
      max-width: 1200px;
      margin: 0 auto;
    }

    .loading {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    .header {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;

      .header-left {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .title {
        h2 {
          margin: 0;
          color: #202124;
        }
        p {
          margin: 4px 0 0;
          color: #5f6368;
        }
      }
    }

    .progress-card {
      padding: 16px;
      margin-bottom: 16px;

      .stats {
        display: flex;
        gap: 24px;
        margin-bottom: 12px;

        span {
          color: #5f6368;

          strong {
            color: #202124;
          }
        }
      }
    }

    .shortcuts-help {
      display: flex;
      justify-content: center;
      margin-bottom: 16px;

      .shortcut-hint {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: #f1f3f4;
        border-radius: 16px;
        font-size: 13px;
        color: #5f6368;
        cursor: help;

        mat-icon {
          font-size: 18px;
          width: 18px;
          height: 18px;
        }

        span {
          font-family: 'Courier New', monospace;
          font-weight: 500;
        }
      }
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px;
      text-align: center;

      mat-icon {
        font-size: 64px;
        width: 64px;
        height: 64px;
        color: #34a853;
        margin-bottom: 16px;
      }

      h3 {
        margin: 0 0 8px;
        color: #202124;
      }

      p {
        margin: 0 0 24px;
        color: #5f6368;
      }
    }

    .annotation-content {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-bottom: 16px;

      @media (max-width: 768px) {
        grid-template-columns: 1fr;
      }
    }

    .image-card {
      padding: 16px;

      img {
        width: 100%;
        max-height: 400px;
        object-fit: contain;
        border-radius: 8px;
        background: #f5f5f5;
      }

      .image-name {
        text-align: center;
        margin: 8px 0 0;
        color: #5f6368;
        font-size: 12px;
      }
    }

    .answer-card {
      .binary-group, .choice-group {
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin: 16px 0;
      }

      .binary-group {
        flex-direction: row;
        gap: 24px;
      }

      .count-field, .text-field {
        width: 100%;
        margin: 16px 0;
      }

      .flag-section {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid #e0e0e0;

        .flag-reason {
          width: 100%;
          margin-top: 8px;
        }
      }

      mat-card-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
      }
    }

    .navigation {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 16px;
      color: #5f6368;
    }
  `]
})
export class AnnotationComponent implements OnInit {
  project = signal<Project | null>(null);
  stats = signal<AnnotationStats | null>(null);
  currentImage = signal<ImageItem | null>(null);
  allImages = signal<ImageItem[]>([]);
  loading = signal(true);
  saving = signal(false);
  imageUrl = signal<string>('');

  projectId = '';
  datasetId = '';
  datasetName = '';
  imageIndex = 0;

  answer: any = null;
  isFlagged = false;
  flagReason = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private evaluationsService: EvaluationsService,
    private projectsService: ProjectsService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.projectId = this.route.snapshot.paramMap.get('projectId') || '';
    this.datasetId = this.route.snapshot.paramMap.get('datasetId') || '';

    if (this.projectId && this.datasetId) {
      this.loadData();
    } else {
      this.router.navigate(['/projects']);
    }
  }

  loadData() {
    this.loading.set(true);

    // Load project, stats, datasets first
    Promise.all([
      this.projectsService.getProject(this.projectId).toPromise(),
      this.evaluationsService.getAnnotationStats(this.projectId, this.datasetId).toPromise(),
      this.projectsService.getDatasets(this.projectId).toPromise()
    ]).then(([project, stats, datasets]) => {
      this.project.set(project || null);
      this.stats.set(stats || null);

      const dataset = datasets?.find(d => d.id === this.datasetId);
      this.datasetName = dataset?.name || '';
      const imageCount = stats?.total_images || 1000; // Use stats total, fallback to 1000

      // Load all images metadata at once (only metadata, images loaded lazily)
      this.projectsService.getImages(this.projectId, this.datasetId, 0, imageCount).toPromise()
        .then(images => {
          this.allImages.set(images || []);

          // Check if we should start at a specific unannotated image
          this.skipToUnannotated(false); // false = don't force reload if we have images

          this.loading.set(false);
        })
        .catch(err => {
          console.error('Failed to load images:', err);
          this.loading.set(false);
          this.snackBar.open('Failed to load images', 'Close', { duration: 3000 });
        });
    }).catch(err => {
      console.error('Failed to load data:', err);
      this.loading.set(false);
      this.snackBar.open('Failed to load data', 'Close', { duration: 3000 });
    });
  }

  skipToUnannotated(force: boolean = true) {
    this.evaluationsService.getNextUnannotated(this.projectId, this.datasetId).subscribe({
      next: (res: any) => {
        if (res.image) {
          // Check if image is already in our list
          const idx = this.allImages().findIndex(img => img.id === res.image!.id);
          if (idx !== -1) {
            this.imageIndex = idx;
            this.currentImage.set(this.allImages()[idx]);
            this.loadAnnotation();
          } else {
            // Image not in current batch, append it
            const newImageItem: ImageItem = {
                id: res.image.id,
                filename: res.image.filename,
                file_size: 0, // Placeholder
                uploaded_at: new Date().toISOString()
            };
            this.allImages.update(imgs => [...imgs, newImageItem]);
            this.imageIndex = this.allImages().length - 1;
            this.currentImage.set(newImageItem);
            this.loadAnnotation();
          }
        } else if (force) {
           this.snackBar.open(res['message'] || 'All images annotated!', 'Close', { duration: 3000 });
           if (!this.currentImage() && this.allImages().length > 0) {
               // Fallback to first image if nothing selected
               this.imageIndex = 0;
               this.currentImage.set(this.allImages()[0]);
               this.loadAnnotation();
           }
        } else {
            // Default behavior on load: Start at 0 if no unannotated found or just fallback
            if (this.allImages().length > 0) {
                this.imageIndex = 0;
                this.currentImage.set(this.allImages()[0]);
                this.loadAnnotation();
            }
        }
      }
    });
  }

  loadAnnotation() {
    const img = this.currentImage();
    if (!img) return;

    // Use full image for annotation (via proxy, no expiry with JWT auth)
    this.imageUrl.set(this.projectsService.getImageUrl(this.projectId, this.datasetId, img.id));

    // Load annotation
    this.evaluationsService.getAnnotation(this.projectId, this.datasetId, img.id).subscribe({
      next: (data) => {
        if (data.annotation) {
          this.answer = data.annotation.answer_value?.value ?? null;
          this.isFlagged = data.annotation.is_flagged;
          this.flagReason = data.annotation.flag_reason || '';
        } else {
          this.resetForm();
        }
      },
      error: () => this.resetForm()
    });
  }

  getImageUrl(): string {
    return this.imageUrl();
  }

  getProgress(): number {
    const s = this.stats();
    if (!s || !s.total_images) return 0;
    return ((s.annotated + s.skipped) / s.total_images) * 100;
  }

  canSave(): boolean {
    return this.answer !== null && this.answer !== '';
  }

  save() {
    const img = this.currentImage();
    if (!img) return;

    this.saving.set(true);
    this.evaluationsService.saveAnnotation(this.projectId, this.datasetId, img.id, {
      answer_value: { value: this.answer },
      is_skipped: false,
      is_flagged: this.isFlagged,
      flag_reason: this.isFlagged ? this.flagReason : undefined
    }).subscribe({
      next: () => {
        this.saving.set(false);
        this.loadNextImage();
        this.refreshStats();
      },
      error: (err) => {
        console.error('Failed to save annotation:', err);
        this.saving.set(false);
        this.snackBar.open('Failed to save', 'Close', { duration: 3000 });
      }
    });
  }

  skip() {
    const img = this.currentImage();
    if (!img) return;

    this.saving.set(true);
    this.evaluationsService.saveAnnotation(this.projectId, this.datasetId, img.id, {
      is_skipped: true
    }).subscribe({
      next: () => {
        this.saving.set(false);
        this.loadNextImage();
        this.refreshStats();
      },
      error: (err) => {
        console.error('Failed to skip:', err);
        this.saving.set(false);
        this.snackBar.open('Failed to skip', 'Close', { duration: 3000 });
      }
    });
  }

  loadNextImage() {
    const images = this.allImages();
    if (this.imageIndex < images.length - 1) {
      this.imageIndex++;
      this.currentImage.set(images[this.imageIndex]);
      this.loadAnnotation();
    } else {
      // End of dataset - try to find next unannotated
      this.skipToUnannotated(true);
    }
  }

  loadPreviousImage() {
    const images = this.allImages();
    if (this.imageIndex > 0) {
      this.imageIndex--;
      this.currentImage.set(images[this.imageIndex]);
      this.loadAnnotation();
    }
  }

  refreshStats() {
    this.evaluationsService.getAnnotationStats(this.projectId, this.datasetId).subscribe({
      next: (stats) => this.stats.set(stats)
    });
  }

  resetForm() {
    this.answer = null;
    this.isFlagged = false;
    this.flagReason = '';
  }

  @HostListener('document:keydown', ['$event'])
  handleKeyboardEvent(event: KeyboardEvent) {
    // Ignore if user is typing in an input field
    const target = event.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
      return;
    }

    // Ignore if no current image or currently saving
    if (!this.currentImage() || this.saving()) {
      return;
    }

    const project = this.project();
    if (!project) return;

    switch (event.key.toLowerCase()) {
      case 'y':
        // Y = Yes (for binary questions)
        if (project.question_type === 'binary') {
          this.answer = true;
          event.preventDefault();
        }
        break;

      case 'n':
        // N = No (for binary questions)
        if (project.question_type === 'binary') {
          this.answer = false;
          event.preventDefault();
        }
        break;

      case 'enter':
        // Enter = Save & Next
        if (this.canSave() && !this.saving()) {
          this.save();
          event.preventDefault();
        }
        break;

      case 'escape':
        // Escape = Skip
        if (!this.saving()) {
          this.skip();
          event.preventDefault();
        }
        break;

      case 'arrowright':
        // Arrow Right = Next image
        this.loadNextImage();
        event.preventDefault();
        break;

      case 'arrowleft':
        // Arrow Left = Previous image
        this.loadPreviousImage();
        event.preventDefault();
        break;
    }
  }
}