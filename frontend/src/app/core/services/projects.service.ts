import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
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

  deleteImage(projectId: string, datasetId: string, imageId: string) {
    return this.http.delete(`${this.API_URL}/projects/${projectId}/datasets/${datasetId}/images/${imageId}`);
  }

  getImageUrl(projectId: string, datasetId: string, imageId: string) {
    return `${this.API_URL}/projects/${projectId}/datasets/${datasetId}/images/${imageId}/file`;
  }
}
