import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface LabellingJob {
  id: string;
  name: string;
  project_id: string;
  dataset_id: string | null;
  dataset_name: string | null;
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
export class LabellingJobsService {
  private apiUrl = `${environment.apiUrl}/labelling-jobs`;

  constructor(private http: HttpClient) {}

  /**
   * Get all labelling jobs, optionally filtered by project
   */
  getLabellingJobs(projectId?: string): Observable<LabellingJob[]> {
    let params = new HttpParams();
    if (projectId) {
      params = params.set('project_id', projectId);
    }
    return this.http.get<LabellingJob[]>(this.apiUrl, { params });
  }

  /**
   * Get a specific labelling job by ID
   */
  getLabellingJob(jobId: string): Observable<LabellingJob> {
    return this.http.get<LabellingJob>(`${this.apiUrl}/${jobId}`);
  }

  /**
   * Create a new labelling job
   */
  createLabellingJob(data: CreateLabellingJob): Observable<LabellingJob> {
    return this.http.post<LabellingJob>(this.apiUrl, data);
  }

  /**
   * Update a labelling job
   */
  updateLabellingJob(jobId: string, data: UpdateLabellingJob): Observable<LabellingJob> {
    return this.http.patch<LabellingJob>(`${this.apiUrl}/${jobId}`, data);
  }

  /**
   * Delete a labelling job
   */
  deleteLabellingJob(jobId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${jobId}`);
  }

  /**
   * Manually trigger a labelling job execution
   */
  triggerJob(jobId: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/${jobId}/trigger`, {});
  }

  /**
   * Get execution history for a labelling job
   */
  getJobRuns(jobId: string, limit: number = 50, offset: number = 0): Observable<LabellingJobRun[]> {
    let params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());
    return this.http.get<LabellingJobRun[]>(`${this.apiUrl}/${jobId}/runs`, { params });
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
    let params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());

    if (runId) {
      params = params.set('run_id', runId);
    }

    return this.http.get<LabellingResult[]>(`${this.apiUrl}/${jobId}/results`, { params });
  }
}
