import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';

export interface User {
  id: string;
  email: string;
  name: string | null;
  picture_url: string | null;
  role: 'admin' | 'user' | 'viewer';
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly TOKEN_KEY = 'auth_token';
  private readonly API_URL = environment.apiUrl;

  private userSignal = signal<User | null>(null);
  private loadingSignal = signal<boolean>(false);

  user = this.userSignal.asReadonly();
  loading = this.loadingSignal.asReadonly();
  isAuthenticated = computed(() => !!this.userSignal());
  isAdmin = computed(() => this.userSignal()?.role === 'admin');

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    this.initializeAuth();
  }

  private async initializeAuth(): Promise<void> {
    const token = this.getToken();
    if (token) {
      await this.loadUser();
    }
  }

  async login(): Promise<void> {
    try {
      const response = await this.http.get<{ auth_url: string }>(
        `${this.API_URL}/auth/google/login`
      ).toPromise();

      if (response?.auth_url) {
        window.location.href = response.auth_url;
      }
    } catch (error) {
      console.error('Failed to get login URL:', error);
      throw error;
    }
  }

  async handleCallback(token: string): Promise<void> {
    this.setToken(token);
    await this.loadUser();
    this.router.navigate(['/home']);
  }

  async loadUser(): Promise<void> {
    const token = this.getToken();
    if (!token) return;

    this.loadingSignal.set(true);
    try {
      const user = await this.http.get<User>(
        `${this.API_URL}/auth/me`
      ).toPromise();

      if (user) {
        this.userSignal.set(user);
      }
    } catch (error) {
      console.error('Failed to load user:', error);
      this.logout();
    } finally {
      this.loadingSignal.set(false);
    }
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    this.userSignal.set(null);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  private setToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token);
  }
}
