import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

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
export class AdminService {
  private readonly API_URL = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getUsers() {
    return this.http.get<AdminUser[]>(`${this.API_URL}/users`);
  }

  getUser(userId: string) {
    return this.http.get<AdminUser>(`${this.API_URL}/users/${userId}`);
  }

  createUser(email: string, role: string) {
    return this.http.post<AdminUser>(`${this.API_URL}/users`, { email, role });
  }

  updateUser(userId: string, data: UpdateUserRequest) {
    return this.http.patch<AdminUser>(`${this.API_URL}/users/${userId}`, data);
  }

  deleteUser(userId: string) {
    return this.http.delete(`${this.API_URL}/users/${userId}`);
  }
}
