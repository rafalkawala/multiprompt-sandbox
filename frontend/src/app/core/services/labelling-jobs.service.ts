import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { BaseApiService } from './base-api.service';

export interface LabellingJob {
  id: string;
  name: string;
  project_id: string;
  dataset_id: string | null;
  dataset_name: string | null;
  thumbnail?: string | null;
  gcs_folder_path: string;
  last_processed_timestamp: string | null;
  frequency_minutes: number;
  is_active: boolean;
  status: string;
  last_run_at: string | null;
  next_run_at: string | null;
  total_runs: number;
  total_images_processed: number;
  total_images_labeled: number;
  total_errors: number;
  created_by_id: string;
  created_at: string;
  updated_at: string;
}

export interface CreateLabellingJob {
  name: string;
  project_id: string;
  evaluation_id: string;
  gcs_folder_path: string;
  frequency_minutes?: number;
  is_active?: boolean;
}

export interface UpdateLabellingJob {
  name?: string;
  gcs_folder_path?: string;
  frequency_minutes?: number;
  is_active?: boolean;
}

export interface LabellingJobRun {
  id: string;
  labelling_job_id: string;
  status: string;
  trigger_type: string;
  images_discovered: number;
  images_ingested: number;
  images_labeled: number;
  images_failed: number;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  error_message: string | null;
  created_at: string;
}

export interface LabellingResult {
  id: string;
  labelling_job_id: string;
  labelling_job_run_id: string;
  image_id: string;
  model_response: string;
  parsed_answer: any;
  confidence_score: number | null;
  latency_ms: number | null;
  error: string | null;
  gcs_source_path: string | null;
  created_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class LabellingJobsService extends BaseApiService {

  constructor(http: HttpClient) {
    super(http);
  }

  /**
   * Get all labelling jobs, optionally filtered by project
   */
  getLabellingJobs(projectId?: string): Observable<LabellingJob[]> {
    const params = projectId ? { project_id: projectId } : undefined;
    return this.get<LabellingJob[]>('/labelling-jobs', params);
  }

  /**
   * Get a specific labelling job by ID
   */
  getLabellingJob(jobId: string): Observable<LabellingJob> {
    return this.get<LabellingJob>(`/labelling-jobs/${jobId}`);
  }

  /**
   * Create a new labelling job
   */
  createLabellingJob(data: CreateLabellingJob): Observable<LabellingJob> {
    return this.post<LabellingJob>('/labelling-jobs', data);
  }

  /**
   * Update a labelling job
   */
  updateLabellingJob(jobId: string, data: UpdateLabellingJob): Observable<LabellingJob> {
    return this.patch<LabellingJob>(`/labelling-jobs/${jobId}`, data);
  }

  /**
   * Delete a labelling job
   */
  deleteLabellingJob(jobId: string): Observable<void> {
    return this.delete<void>(`/labelling-jobs/${jobId}`);
  }

  /**
   * Manually trigger a labelling job execution
   */
  triggerJob(jobId: string): Observable<any> {
    return this.post(`/labelling-jobs/${jobId}/trigger`, {});
  }

  /**
   * Get execution history for a labelling job
   */
  getJobRuns(jobId: string, limit: number = 50, offset: number = 0): Observable<LabellingJobRun[]> {
    return this.get<LabellingJobRun[]>(`/labelling-jobs/${jobId}/runs`, { limit, offset });
  }

  /**
   * Get labeling results for a job
   */
  getJobResults(
    jobId: string,
    runId?: string,
    limit: number = 100,
    offset: number = 0
  ): Observable<LabellingResult[]> {
    const params: any = { limit, offset };
    if (runId) {
      params['run_id'] = runId;
    }
    return this.get<LabellingResult[]>(`/labelling-jobs/${jobId}/results`, params);
  }
}
