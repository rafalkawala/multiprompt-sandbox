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
    // Check for session expired flag
    try {
      const sessionExpired = sessionStorage.getItem('session_expired');
      if (sessionExpired === 'true') {
        sessionStorage.removeItem('session_expired');
        this.errorSignal.set({
          message: 'Your session has expired. Please sign in again.',
          code: 'SESSION_EXPIRED'
        });
      }
    } catch (error) {
      console.warn('[Auth Service] Could not check session expired flag:', error);
    }

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
    console.log('[Auth Service] handleCallback called', {
      hasTokenFromHash: !!tokenFromHash,
      tokenLength: tokenFromHash?.length,
      hasLocalStorageToken: !!localStorage.getItem('dev_access_token'),
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString()
    });

    this.errorSignal.set(null);

    // If a token is provided in the hash (dev environment workaround)
    if (tokenFromHash) {
      try {
        localStorage.setItem('dev_access_token', tokenFromHash);
        console.log('[Auth Service] Token stored in localStorage successfully');
        // Remove the token from the URL hash to clean up the URL
        this.router.navigate([], { replaceUrl: true, fragment: undefined });
      } catch (error) {
        console.error('[Auth Service] Failed to store token in localStorage:', error);
        this.errorSignal.set({
          message: 'Failed to store authentication token. Please check browser settings.',
          code: 'STORAGE_FAILED'
        });
        return;
      }
    }

    // Attempt to load the user (will now also check localStorage token if available)
    console.log('[Auth Service] Attempting to load user...');
    await this.loadUser();

    if (this.userSignal()) {
      console.log('[Auth Service] User loaded successfully, redirecting to /home');
      this.router.navigate(['/home']);
    } else {
      // If no user after callback, something went wrong
      console.error('[Auth Service] User not loaded after callback', {
        hadToken: !!tokenFromHash,
        hasStoredToken: !!localStorage.getItem('dev_access_token')
      });
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

    const hasLocalStorageToken = !!localStorage.getItem('dev_access_token');
    const hasSessionStorageToken = !!sessionStorage.getItem('dev_access_token');
    console.log('[Auth Service] loadUser - starting', {
      apiUrl: this.API_URL,
      hasLocalStorageToken,
      hasSessionStorageToken,
      userAgent: navigator.userAgent
    });

    try {
      // Token is automatically added by auth interceptor
      const user = await this.http.get<User>(
        `${this.API_URL}/auth/me`,
        { withCredentials: true, responseType: 'json' }
      ).toPromise();

      if (user) {
        console.log('[Auth Service] loadUser - success', {
          userId: user.id,
          email: user.email,
          role: user.role
        });
        this.userSignal.set(user);
      } else {
        console.warn('[Auth Service] loadUser - no user returned');
      }
    } catch (error) {
      console.error('[Auth Service] loadUser - failed', {
        error,
        hasLocalStorageToken,
        hasSessionStorageToken,
        errorStatus: error instanceof HttpErrorResponse ? error.status : 'unknown',
        errorMessage: error instanceof HttpErrorResponse ? error.message : String(error),
        userAgent: navigator.userAgent
      });

      if (error instanceof HttpErrorResponse) {
        if (error.status === 401) {
          // Not authenticated - this is normal for logged out users
          console.log('[Auth Service] loadUser - 401 Unauthorized (expected for logged out users)');
          this.userSignal.set(null);
        } else if (error.status === 400) {
          // User is deactivated
          console.log('[Auth Service] loadUser - 400 Bad Request (account deactivated)');
          this.userSignal.set(null);
          this.errorSignal.set({
            message: 'Your account has been deactivated. Please contact an administrator.',
            code: 'ACCOUNT_DEACTIVATED'
          });
        } else {
          // Network or server error
          console.error('[Auth Service] loadUser - Network/server error', {
            status: error.status,
            statusText: error.statusText,
            url: error.url
          });
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
    console.log('[Auth Service] logout - starting');
    try {
      await this.http.post(
        `${this.API_URL}/auth/logout`,
        {},
        { withCredentials: true }
      ).toPromise();
      console.log('[Auth Service] logout - backend call successful');
    } catch (error) {
      console.error('[Auth Service] logout - backend call failed:', error);
    }

    // Clear localStorage token
    try {
      localStorage.removeItem('dev_access_token');
      console.log('[Auth Service] logout - localStorage cleared');
    } catch (error) {
      console.error('[Auth Service] logout - failed to clear localStorage:', error);
    }

    this.userSignal.set(null);
    this.errorSignal.set(null);
    console.log('[Auth Service] logout - complete');
  }

  handleSessionExpired(): void {
    console.log('[Auth Service] Handling session expiration');

    // Clear token
    try {
      localStorage.removeItem('dev_access_token');
      sessionStorage.removeItem('dev_access_token');
    } catch (error) {
      console.warn('[Auth Service] Failed to clear tokens:', error);
    }

    // Clear user state
    this.userSignal.set(null);

    // Set error message to be displayed on login screen
    this.errorSignal.set({
      message: 'Your session has expired. Please sign in again.',
      code: 'SESSION_EXPIRED'
    });

    // Navigate to root to ensure login screen is shown (though signal change handles view update)
    this.router.navigate(['/']);
  }
}
