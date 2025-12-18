import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BaseApiService } from './base-api.service';

export interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  picture_url: string | null;
  role: 'admin' | 'user' | 'viewer';
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface UpdateUserRequest {
  name?: string;
  role?: string;
  is_active?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AdminService extends BaseApiService {

  constructor(http: HttpClient) {
    super(http);
  }

  getUsers() {
    return this.get<AdminUser[]>('/users');
  }

  getUser(userId: string) {
    return this.get<AdminUser>(`/users/${userId}`);
  }

  createUser(email: string, role: string) {
    return this.post<AdminUser>('/users', { email, role });
  }

  updateUser(userId: string, data: UpdateUserRequest) {
    return this.patch<AdminUser>(`/users/${userId}`, data);
  }

  deleteUser(userId: string) {
    return this.delete(`/users/${userId}`);
  }
}
