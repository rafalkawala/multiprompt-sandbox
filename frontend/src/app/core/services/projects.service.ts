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

export interface DatasetSplit {
  id: string;
  dataset_id: string;
  name: string;
  split_type: string;
  split_value?: number;
  purpose?: string; // 'annotation', 'test', 'unlabeled_pool'
  excluded_split_ids?: string[];
  image_ids: string[];
  created_at: string;
}

export interface CreateSplitRequest {
  name: string;
  split_type: string; // 'random_percent', 'random_count', 'k_means_centroid'
  split_value?: number;
  purpose?: string; // 'annotation', 'test', 'unlabeled_pool'
  excluded_split_ids?: string[];
}

export interface SampleSizeCalculation {
  recommended_size: number;
  percentage: number;
  confidence_level: number;
  margin_of_error: number;
  z_score: number;
  formula_explanation: string;
  is_exact: boolean;
}

export interface ClusteringStatus {
  is_clustered: boolean;
  cluster_count: number;
  images_clustered: number;
  images_without_clusters: number;
  images_without_embeddings: number;
}

export interface ClusteringResult {
  cluster_count: number;
  centroids: number[][];
  cluster_sizes: Record<number, number>;
  images_clustered: number;
  images_without_embeddings: number;
  inertia: number;
}

export interface KRecommendation {
  recommended_k: number;
  min_cluster_size: number;
  max_k: number;
  min_k: number;
  explanation: string;
  confidence_level: number;
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
  getImages(projectId: string, datasetId: string, skip: number = 0, limit: number = 50, splitId?: string) {
    const params: any = {
      skip: skip,
      limit: limit,
      include_thumbnails: 'true'
    };
    if (splitId) {
      params['split_id'] = splitId;
    }
    return this.get<ImageItem[]>(`/projects/${projectId}/datasets/${datasetId}/images`, params);
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

  // Dataset Split Methods
  createDatasetSplit(projectId: string, datasetId: string, data: CreateSplitRequest) {
    // Note: The endpoint is /api/v1/datasets/{datasetId}/splits
    // The previous implementation of dataset_splits.py used /{dataset_id}/splits directly under the router
    // but the router prefix was "/api/v1/datasets" or empty?
    // Let's check api/v1/__init__.py and api/v1/dataset_splits.py
    // api/v1/dataset_splits.py has @router.post("/{dataset_id}/splits")
    // api/v1/__init__.py has api_router.include_router(dataset_splits.router, prefix="", tags=["dataset-splits"])
    // So the URL is /api/v1/{dataset_id}/splits

    // Wait, typical pattern is /api/v1/projects/{projectId}/datasets/{datasetId}/splits?
    // My backend implementation used /api/v1/{dataset_id}/splits directly.
    // I should probably stick to what I implemented in backend.

    return this.http.post<DatasetSplit>(`${this.API_URL}/${datasetId}/splits`, data);
  }

  getDatasetSplits(projectId: string, datasetId: string) {
     return this.http.get<DatasetSplit[]>(`${this.API_URL}/${datasetId}/splits`);
  }

  // Statistical Sample Size Calculator
  calculateSampleSize(
    projectId: string,
    datasetId: string,
    confidenceLevel: number = 0.95,
    marginOfError: number = 0.05
  ) {
    const params = new HttpParams()
      .set('confidence_level', confidenceLevel.toString())
      .set('margin_of_error', marginOfError.toString());

    return this.http.get<SampleSizeCalculation>(
      `${this.API_URL}/${datasetId}/sample-size-calculator`,
      { params }
    );
  }

  // K-Means Clustering Methods
  performClustering(
    projectId: string,
    datasetId: string,
    k?: number,
    confidenceLevel: number = 0.95
  ) {
    const body = {
      k: k || null,
      confidence_level: confidenceLevel
    };

    return this.http.post<ClusteringResult>(
      `${this.API_URL}/${datasetId}/cluster`,
      body
    );
  }

  getClusteringStatus(projectId: string, datasetId: string) {
    return this.http.get<ClusteringStatus>(
      `${this.API_URL}/${datasetId}/clustering-status`
    );
  }

  getKRecommendation(
    projectId: string,
    datasetId: string,
    confidenceLevel: number = 0.95
  ) {
    const params = new HttpParams()
      .set('confidence_level', confidenceLevel.toString());

    return this.http.get<KRecommendation>(
      `${this.API_URL}/${datasetId}/k-recommendation`,
      { params }
    );
  }

  // Unlabeled Pool Creation
  createUnlabeledPool(projectId: string, datasetId: string) {
    return this.http.post<DatasetSplit>(
      `${this.API_URL}/${datasetId}/unlabeled-pool`,
      {}
    );
  }
}
