import { Component, Inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatRadioModule } from '@angular/material/radio';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { ProjectsService, ImageItem } from '../../../../core/services/projects.service';

export interface SubselectionConfig {
  mode: 'all' | 'random_count' | 'random_percent' | 'manual';
  count?: number;
  percent?: number;
  image_ids?: string[];
}

@Component({
  selector: 'app-subselection-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatRadioModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatChipsModule
  ],
  templateUrl: './subselection-dialog.component.html',
  styleUrl: './subselection-dialog.component.scss'
})
export class SubselectionDialogComponent implements OnInit {
  config: SubselectionConfig;
  datasetId: string;
  projectId: string;
  
  // Manual selection state
  images = signal<ImageItem[]>([]);
  loadingImages = signal(false);
  selectedImages = signal<Set<string>>(new Set());
  totalImages = 0;
  
  constructor(
    public dialogRef: MatDialogRef<SubselectionDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { config: SubselectionConfig, datasetId: string, projectId: string },
    private projectsService: ProjectsService
  ) {
    this.config = { ...data.config }; // Copy to avoid mutating original until save
    this.datasetId = data.datasetId;
    this.projectId = data.projectId;
    
    if (this.config.mode === 'manual' && this.config.image_ids) {
      this.selectedImages.set(new Set(this.config.image_ids));
    }
  }

  ngOnInit() {
    if (this.datasetId) {
      this.loadImages();
    }
  }

  loadImages() {
    this.loadingImages.set(true);
    // Ideally support pagination or infinite scroll for large datasets
    // For MVP, loading first 500 or so.
    this.projectsService.getImages(this.projectId, this.datasetId, 0, 500).subscribe({
      next: (images) => {
        this.images.set(images);
        this.totalImages = images.length; // Should get total from API ideally
        this.loadingImages.set(false);
      },
      error: (err) => {
        console.error('Failed to load images', err);
        this.loadingImages.set(false);
      }
    });
  }

  getImageUrl(image: ImageItem): string {
    return image.thumbnail_url || this.projectsService.getImageThumbnailUrl(this.projectId, this.datasetId, image.id);
  }

  toggleImageSelection(imageId: string) {
    const current = this.selectedImages();
    if (current.has(imageId)) {
      current.delete(imageId);
    } else {
      current.add(imageId);
    }
    this.selectedImages.set(new Set(current)); // Trigger signal update
  }

  selectAll() {
    const allIds = this.images().map(i => i.id);
    this.selectedImages.set(new Set(allIds));
  }

  deselectAll() {
    this.selectedImages.set(new Set());
  }

  isValid(): boolean {
    if (this.config.mode === 'random_count') {
      return (this.config.count || 0) > 0;
    }
    if (this.config.mode === 'random_percent') {
      return (this.config.percent || 0) > 0 && (this.config.percent || 0) <= 100;
    }
    if (this.config.mode === 'manual') {
      return this.selectedImages().size > 0;
    }
    return true; // 'all' is always valid
  }

  save() {
    if (this.config.mode === 'manual') {
      this.config.image_ids = Array.from(this.selectedImages());
    }
    this.dialogRef.close(this.config);
  }

  clear() {
    this.config = { mode: 'all' };
    this.dialogRef.close(this.config);
  }
}
