import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { BaseApiService } from './base-api.service';

export interface ModelConfig {
  id: string;
  name: string;
  provider: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  concurrency: number;
  additional_params: any;
  pricing_config: any;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ModelConfigListItem {
  id: string;
  name: string;
  provider: string;
  model_name: string;
  is_active: boolean;
  created_at: string;
}

export interface CreateModelConfig {
  name: string;
  provider: string;
  model_name: string;
  api_key?: string;  // Optional - uses service account auth if not provided
  temperature?: number;
  max_tokens?: number;
  concurrency?: number;  // Number of parallel API calls (default: 3)
  additional_params?: any;
  pricing_config?: any;  // Cost tracking configuration
}

export interface TestResponse {
  success: boolean;
  response?: string;
  error?: string;
  latency_ms?: number;
}

// Multi-phase prompting interfaces
export interface PromptStep {
  step_number: number;
  system_message: string;
  prompt: string;
}

export interface StepResult {
  step_number: number;
  raw_output: string;
  latency_ms: number;
  error: string | null;
}

export interface Evaluation {
  id: string;
  name: string;
  project_id: string;
  dataset_id: string;
  model_config_id: string;
  status: string;
  progress: number;
  total_images: number;
  processed_images: number;
  accuracy: number | null;
  results_summary: any;
  error_message: string | null;
  system_message: string | null;
  question_text: string | null;
  prompt_chain: PromptStep[] | null;  // Multi-phase prompting
  selection_config?: any; // Dataset subselection
  estimated_cost: number | null;  // Cost estimation before execution
  actual_cost: number | null;  // Actual cost after execution
  cost_details: any | null;  // Detailed cost breakdown
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface EvaluationListItem {
  id: string;
  name: string;
  project_name: string;
  dataset_name: string;
  model_name: string;
  status: string;
  progress: number;
  total_images: number;
  processed_images: number;
  accuracy: number | null;
  created_at: string;
  results_summary?: {
    latest_images?: string[];
    eta_seconds?: number;
    [key: string]: any;
  };
}

export interface EvaluationResult {
  id: string;
  image_id: string;
  image_filename: string;
  model_response: string | null;
  parsed_answer: any;
  ground_truth: any;
  is_correct: boolean | null;
  latency_ms: number | null;
  step_results?: StepResult[];  // Multi-phase prompting results
}

export interface CreateEvaluation {
  name: string;
  project_id: string;
  dataset_id: string;
  model_config_id: string;
  // Legacy single-prompt (optional)
  system_message?: string;
  question_text?: string;
  // Multi-phase prompting (optional)
  prompt_chain?: PromptStep[];
  // Dataset subselection
  selection_config?: any;
}

export interface AnnotationStats {
  total_images: number;
  annotated: number;
  skipped: number;
  flagged: number;
  remaining: number;
}

export interface Annotation {
  id: string;
  image_id: string;
  answer_value: any;
  is_skipped: boolean;
  is_flagged: boolean;
  flag_reason: string | null;
  annotator_id: string | null;
  created_at: string;
  updated_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class EvaluationsService extends BaseApiService {

  constructor(http: HttpClient) {
    super(http);
  }

  // Model Configs
  getModelConfigs() {
    return this.get<ModelConfigListItem[]>('/model-configs');
  }

  getModelConfig(id: string) {
    return this.get<ModelConfig>(`/model-configs/${id}`);
  }

  createModelConfig(data: CreateModelConfig) {
    return this.post<ModelConfig>('/model-configs', data);
  }

  updateModelConfig(id: string, config: Partial<ModelConfig>): Observable<ModelConfig> {
    return this.patch<ModelConfig>(`/model-configs/${id}`, config);
  }

  deleteModelConfig(id: string): Observable<void> {
    return this.delete<void>(`/model-configs/${id}`);
  }

  testModelConfig(id: string, prompt: string): Observable<TestResponse> {
    return this.post<TestResponse>(`/model-configs/${id}/test`, { prompt });
  }

  exportModelConfigs(): Observable<Blob> {
    return this.http.get(`${this.API_URL}/model-configs/export`, { responseType: 'blob' });
  }

  importModelConfigs(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.post<any>('/model-configs/import', formData);
  }

  // --- Evaluation Endpoints ---
  getEvaluations(projectId?: string) {
    return this.get<EvaluationListItem[]>('/evaluations', projectId ? { project_id: projectId } : undefined);
  }

  getEvaluation(id: string) {
    return this.get<Evaluation>(`/evaluations/${id}`);
  }

  createEvaluation(data: CreateEvaluation) {
    return this.post<Evaluation>('/evaluations', data);
  }

  getEvaluationResults(id: string, skip: number = 0, limit: number = 50, filter: string = 'all') {
    return this.get<EvaluationResult[]>(`/evaluations/${id}/results`, { skip, limit, filter });
  }

  estimateEvaluationCost(id: string) {
    return this.get<{estimated_cost: number, image_count: number, avg_cost_per_image: number, details: any}>(`/evaluations/${id}/estimate-cost`);
  }

  deleteEvaluation(id: string) {
    return this.delete(`/evaluations/${id}`);
  }

  // Annotations
  getAnnotationStats(projectId: string, datasetId: string) {
    return this.get<AnnotationStats>(`/projects/${projectId}/datasets/${datasetId}/annotations/stats`);
  }

  getNextUnannotated(projectId: string, datasetId: string) {
    return this.get<{image: {id: string, filename: string, dataset_id: string} | null}>(`/projects/${projectId}/datasets/${datasetId}/annotations/next`);
  }

  getAnnotation(projectId: string, datasetId: string, imageId: string) {
    return this.get<{annotation: Annotation | null}>(`/projects/${projectId}/datasets/${datasetId}/images/${imageId}/annotation`);
  }

  saveAnnotation(projectId: string, datasetId: string, imageId: string, data: {answer_value?: any, is_skipped?: boolean, is_flagged?: boolean, flag_reason?: string}) {
    return this.put<Annotation>(`/projects/${projectId}/datasets/${datasetId}/images/${imageId}/annotation`, data);
  }

  deleteAnnotation(projectId: string, datasetId: string, imageId: string) {
    return this.delete(`/projects/${projectId}/datasets/${datasetId}/images/${imageId}/annotation`);
  }

  // Import/Export methods
  exportAnnotations(projectId: string, datasetId: string): void {
    // Trigger download by navigating to export endpoint
    const url = `${this.API_URL}/projects/${projectId}/datasets/${datasetId}/annotations/export`;
    window.open(url, '_blank');
  }

  downloadTemplate(projectId: string, datasetId: string): void {
    // Trigger download of sample template
    const url = `${this.API_URL}/projects/${projectId}/datasets/${datasetId}/annotations/template`;
    window.open(url, '_blank');
  }

  previewImport(projectId: string, datasetId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return this.post<{
      total_rows: number,
      valid: number,
      errors: number,
      warnings: number,
      create: number,
      update: number,
      skip: number,
      results: any[]
    }>(`/projects/${projectId}/datasets/${datasetId}/annotations/import/preview`, formData);
  }

  confirmImport(projectId: string, datasetId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return this.post<{
      created: number,
      updated: number,
      skipped: number,
      total: number
    }>(`/projects/${projectId}/datasets/${datasetId}/annotations/import/confirm`, formData);
  }
}
