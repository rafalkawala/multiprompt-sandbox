import { Injectable, signal, computed } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
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

export interface AuthError {
  message: string;
  code: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly API_URL = environment.apiUrl;

  private userSignal = signal<User | null>(null);
  private loadingSignal = signal<boolean>(false);
  private authInitializedSignal = signal<boolean>(false);
  private errorSignal = signal<AuthError | null>(null);

  user = this.userSignal.asReadonly();
  loading = this.loadingSignal.asReadonly();
  isAuthenticated = computed(() => !!this.userSignal());
  isAdmin = computed(() => this.userSignal()?.role === 'admin');
  authInitialized = this.authInitializedSignal.asReadonly();
  error = this.errorSignal.asReadonly();

  private initPromise: Promise<void>;

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    this.initPromise = this.initializeAuth();
  }

  private async initializeAuth(): Promise<void> {
    // Try to load user - cookie will be sent automatically if present
    await this.loadUser();
    this.authInitializedSignal.set(true);
  }

  waitForInit(): Promise<void> {
    return this.initPromise;
  }

  clearError(): void {
    this.errorSignal.set(null);
  }

  async login(): Promise<void> {
    this.errorSignal.set(null);
    try {
      const response = await this.http.get<{ auth_url: string }>(
        `${this.API_URL}/auth/google/login`
      ).toPromise();

      if (response?.auth_url) {
        window.location.href = response.auth_url;
      }
    } catch (error) {
      console.error('Failed to get login URL:', error);
      this.errorSignal.set({
        message: 'Unable to connect to authentication service. Please try again.',
        code: 'LOGIN_FAILED'
      });
      throw error;
    }
  }

  async handleCallback(tokenFromHash: string | null = null): Promise<void> {
    this.errorSignal.set(null);

    // If a token is provided in the hash (dev environment workaround)
    if (tokenFromHash) {
      localStorage.setItem('dev_access_token', tokenFromHash);
      // Remove the token from the URL hash to clean up the URL
      this.router.navigate([], { replaceUrl: true, fragment: undefined });
    }

    // Attempt to load the user (will now also check localStorage token if available)
    await this.loadUser();

    if (this.userSignal()) {
      this.router.navigate(['/home']);
    } else {
      // If no user after callback, something went wrong
      this.errorSignal.set({
        message: 'Authentication failed. Please try again.',
        code: 'CALLBACK_FAILED'
      });
      this.router.navigate(['/']);
    }
  }

  async loadUser(): Promise<void> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);
    try {
      // Token is automatically added by auth interceptor
      const user = await this.http.get<User>(
        `${this.API_URL}/auth/me`,
        { withCredentials: true, responseType: 'json' }
      ).toPromise();

      if (user) {
        this.userSignal.set(user);
      }
    } catch (error) {
      console.error('Failed to load user:', error);
      if (error instanceof HttpErrorResponse) {
        if (error.status === 401) {
          // Not authenticated - this is normal for logged out users
          this.userSignal.set(null);
        } else if (error.status === 400) {
          // User is deactivated
          this.userSignal.set(null);
          this.errorSignal.set({
            message: 'Your account has been deactivated. Please contact an administrator.',
            code: 'ACCOUNT_DEACTIVATED'
          });
        } else {
          // Network or server error
          this.errorSignal.set({
            message: 'Unable to connect to server. Please check your connection.',
            code: 'CONNECTION_ERROR'
          });
        }
      }
    } finally {
      this.loadingSignal.set(false);
    }
  }

  async logout(): Promise<void> {
    try {
      await this.http.post(
        `${this.API_URL}/auth/logout`,
        {},
        { withCredentials: true }
      ).toPromise();
    } catch (error) {
      console.error('Logout failed:', error);
    }
    this.userSignal.set(null);
    this.errorSignal.set(null);
  }
}
