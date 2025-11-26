import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, from } from 'rxjs';
import { mergeMap, map, catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

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
}

export interface DatasetDetail {
  id: string;
  name: string;
  project_id: string;
  created_at: string;
  image_count: number;
  images?: ImageItem[];
}

@Injectable({
  providedIn: 'root'
})
export class ProjectsService {
  private readonly API_URL = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getProjects() {
    return this.http.get<ProjectListItem[]>(`${this.API_URL}/projects`);
  }

  getProject(projectId: string) {
    return this.http.get<Project>(`${this.API_URL}/projects/${projectId}`);
  }

  createProject(data: CreateProjectRequest) {
    return this.http.post<Project>(`${this.API_URL}/projects`, data);
  }

  updateProject(projectId: string, data: UpdateProjectRequest) {
    return this.http.patch<Project>(`${this.API_URL}/projects/${projectId}`, data);
  }

  deleteProject(projectId: string) {
    return this.http.delete(`${this.API_URL}/projects/${projectId}`);
  }

  // Dataset methods
  getDatasets(projectId: string) {
    return this.http.get<DatasetDetail[]>(`${this.API_URL}/projects/${projectId}/datasets`);
  }

  createDataset(projectId: string, name: string) {
    return this.http.post<DatasetDetail>(`${this.API_URL}/projects/${projectId}/datasets`, { name });
  }

  deleteDataset(projectId: string, datasetId: string) {
    return this.http.delete(`${this.API_URL}/projects/${projectId}/datasets/${datasetId}`);
  }

  // Image methods
  getImages(projectId: string, datasetId: string) {
    return this.http.get<ImageItem[]>(`${this.API_URL}/projects/${projectId}/datasets/${datasetId}/images`);
  }

  uploadImages(projectId: string, datasetId: string, files: File[]) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    return this.http.post<ImageItem[]>(`${this.API_URL}/projects/${projectId}/datasets/${datasetId}/images`, formData);
  }

  // Upload single file with progress tracking
  uploadSingleImage(projectId: string, datasetId: string, file: File): Observable<{
    progress?: number;
    result?: ImageItem[];
    error?: string;
    filename: string;
  }> {
    const formData = new FormData();
    formData.append('files', file);

    return this.http.post<ImageItem[]>(
      `${this.API_URL}/projects/${projectId}/datasets/${datasetId}/images`,
      formData,
      {
        reportProgress: true,
        observe: 'events'
      }
    ).pipe(
      map((event: HttpEvent<ImageItem[]>) => {
        switch (event.type) {
          case HttpEventType.UploadProgress:
            const progress = event.total ? Math.round(100 * event.loaded / event.total) : 0;
            return { progress, filename: file.name };
          case HttpEventType.Response:
            return { result: event.body || [], filename: file.name };
          default:
            return { filename: file.name };
        }
      }),
      catchError(err => {
        console.error(`Upload failed for ${file.name}:`, err);
        return [{ error: err.message || 'Upload failed', filename: file.name }];
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
    return this.http.delete(`${this.API_URL}/projects/${projectId}/datasets/${datasetId}/images/${imageId}`);
  }

  getImageUrl(projectId: string, datasetId: string, imageId: string) {
    return `${this.API_URL}/projects/${projectId}/datasets/${datasetId}/images/${imageId}/file`;
  }

  // Get signed URL for direct GCS access (cloud) or proxy URL (local)
  getImageSignedUrl(projectId: string, datasetId: string, imageId: string) {
    return this.http.get<{url: string; type: string}>(
      `${this.API_URL}/projects/${projectId}/datasets/${datasetId}/images/${imageId}/url`
    );
  }

  // Get thumbnail URL (256x256 JPEG from database, no expiry)
  getImageThumbnailUrl(projectId: string, datasetId: string, imageId: string) {
    return `${this.API_URL}/projects/${projectId}/datasets/${datasetId}/images/${imageId}/thumbnail`;
  }
}
