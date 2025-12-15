import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType, HttpParams } from '@angular/common/http';
import { Observable, from } from 'rxjs';
import { mergeMap, map, catchError } from 'rxjs/operators';
import { BaseApiService } from './base-api.service';

export interface ProjectListItem {
  id: string;
  name: string;
  description: string | null;
  question_type: string;
  created_at: string;
  updated_at: string;
  dataset_count: number;
}

export interface Dataset {
  id: string;
  name: string;
  created_at: string;
  image_count: number;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  question_text: string;
  question_type: string;
  question_options: string[] | null;
  created_by_id: string;
  created_at: string;
  updated_at: string;
  dataset_count: number;
  datasets: Dataset[] | null;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  question_text: string;
  question_type: string;
  question_options?: string[];
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  question_text?: string;
  question_type?: string;
  question_options?: string[];
}

export interface ImageItem {
  id: string;
  filename: string;
  file_size: number;
  uploaded_at: string;
  thumbnail_url?: string;
  is_annotated?: boolean;
  annotation_value?: any;
  is_skipped?: boolean;
  is_flagged?: boolean;
}

export interface DatasetDetail {
  id: string;
  name: string;
  project_id: string;
  created_at: string;
  image_count: number;
  images?: ImageItem[];
  processing_status?: string; // 'ready', 'uploading', 'processing', 'completed', 'failed'
  total_files?: number;
  processed_files?: number;
  failed_files?: number;
  processing_started_at?: string;
  processing_completed_at?: string;
}

export interface BatchUploadResponse {
  dataset_id: string;
  uploaded_count: number;
  failed_count: number;
  processing_status: string;
  errors?: string[];
  message: string;
}

export interface ProcessingStatus {
  dataset_id: string;
  processing_status: string; // 'ready', 'uploading', 'processing', 'completed', 'failed'
  total_files: number;
  processed_files: number;
  failed_files: number;
  progress_percent: number;
  processing_started_at?: string;
  processing_completed_at?: string;
  errors?: string[];
}

@Injectable({
  providedIn: 'root'
})
export class ProjectsService extends BaseApiService {

  constructor(http: HttpClient) {
    super(http);
  }

  getProjects() {
    return this.get<ProjectListItem[]>('/projects');
  }

  getProject(projectId: string) {
    return this.get<Project>(`/projects/${projectId}`);
  }

  createProject(data: CreateProjectRequest) {
    return this.post<Project>('/projects', data);
  }

  updateProject(projectId: string, data: UpdateProjectRequest) {
    return this.patch<Project>(`/projects/${projectId}`, data);
  }

  deleteProject(projectId: string) {
    return this.delete(`/projects/${projectId}`);
  }

  // Dataset methods
  getDatasets(projectId: string) {
    return this.get<DatasetDetail[]>(`/projects/${projectId}/datasets`);
  }

  createDataset(projectId: string, name: string) {
    return this.post<DatasetDetail>(`/projects/${projectId}/datasets`, { name });
  }

  deleteDataset(projectId: string, datasetId: string) {
    return this.delete(`/projects/${projectId}/datasets/${datasetId}`);
  }

  // Image methods
  getImages(projectId: string, datasetId: string, skip: number = 0, limit: number = 50) {
    return this.get<ImageItem[]>(`/projects/${projectId}/datasets/${datasetId}/images`, {
      skip: skip,
      limit: limit,
      include_thumbnails: 'true'
    });
  }

  uploadImages(projectId: string, datasetId: string, files: File[]) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    return this.post<ImageItem[]>(`/projects/${projectId}/datasets/${datasetId}/images`, formData);
  }

  // Upload single file with progress tracking
  uploadSingleImage(projectId: string, datasetId: string, file: File): Observable<{
    progress?: number;
    result?: ImageItem[];
    error?: string;
    errors?: string[];
    summary?: string;
    filename: string;
  }> {
    const formData = new FormData();
    formData.append('files', file);

    return this.http.post<{images: ImageItem[], errors?: string[], summary?: string}>(
      `${this.API_URL}/projects/${projectId}/datasets/${datasetId}/images`,
      formData,
      {
        reportProgress: true,
        observe: 'events'
      }
    ).pipe(
      map((event: any) => {
        switch (event.type) {
          case HttpEventType.UploadProgress:
            const progress = event.total ? Math.round(100 * event.loaded / event.total) : 0;
            return { progress, filename: file.name };
          case HttpEventType.Response:
            const body = event.body;
            return {
              result: body?.images || [],
              errors: body?.errors,
              summary: body?.summary,
              filename: file.name
            };
          default:
            return { filename: file.name };
        }
      }),
      catchError(err => {
        console.error(`Upload failed for ${file.name}:`, err);
        const errorDetail = err.error?.detail || err.message || 'Upload failed';
        return [{ error: errorDetail, filename: file.name }];
      })
    );
  }

  // Upload multiple files in parallel (default 3 concurrent)
  uploadImagesInParallel(
    projectId: string,
    datasetId: string,
    files: File[],
    concurrency: number = 3
  ): Observable<{
    progress?: number;
    result?: ImageItem[];
    error?: string;
    errors?: string[];
    summary?: string;
    filename: string;
  }> {
    return from(files).pipe(
      mergeMap(
        file => this.uploadSingleImage(projectId, datasetId, file),
        concurrency
      )
    );
  }

  deleteImage(projectId: string, datasetId: string, imageId: string) {
    return this.delete(`/projects/${projectId}/datasets/${datasetId}/images/${imageId}`);
  }

  getImageUrl(projectId: string, datasetId: string, imageId: string) {
    return `${this.API_URL}/projects/${projectId}/datasets/${datasetId}/images/${imageId}/file`;
  }

  // Get signed URL for direct GCS access (cloud) or proxy URL (local)
  getImageSignedUrl(projectId: string, datasetId: string, imageId: string) {
    return this.get<{url: string; type: string}>(
      `/projects/${projectId}/datasets/${datasetId}/images/${imageId}/url`
    );
  }

  // Get thumbnail URL (256x256 JPEG from database, no expiry)
  getImageThumbnailUrl(projectId: string, datasetId: string, imageId: string) {
    return `${this.API_URL}/projects/${projectId}/datasets/${datasetId}/images/${imageId}/thumbnail`;
  }

  // Two-phase batch upload: Upload to GCS + enqueue background processing
  uploadImagesBatch(projectId: string, datasetId: string, files: File[]) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    return this.post<BatchUploadResponse>(
      `/projects/${projectId}/datasets/${datasetId}/images/batch-upload`,
      formData
    );
  }

  // Get processing status for polling during Phase 2 (thumbnail generation)
  getProcessingStatus(projectId: string, datasetId: string) {
    return this.get<ProcessingStatus>(
      `/projects/${projectId}/datasets/${datasetId}/processing-status`
    );
  }
}
