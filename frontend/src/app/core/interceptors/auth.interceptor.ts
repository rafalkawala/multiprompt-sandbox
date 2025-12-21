import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);

  // Get token from localStorage or sessionStorage (fallback for iOS Safari)
  let token: string | null = null;
  let source = 'none';

  try {
    token = localStorage.getItem('dev_access_token');
    if (token) {
      source = 'localStorage';
    }
  } catch (error) {
    console.warn('[Auth Interceptor] localStorage unavailable:', error);
  }

  // Fallback to sessionStorage if localStorage is blocked
  if (!token) {
    try {
      token = sessionStorage.getItem('dev_access_token');
      if (token) {
        source = 'sessionStorage';
      }
    } catch (error) {
      console.warn('[Auth Interceptor] sessionStorage unavailable:', error);
    }
  }

  console.log('[Auth Interceptor]', {
    url: req.url,
    hasToken: !!token,
    tokenLength: token?.length,
    source: source,
    method: req.method
  });

  // Clone request and add Authorization header if token exists
  if (token) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
    console.log(`[Auth Interceptor] Authorization header added (from ${source})`);
  } else {
    console.log('[Auth Interceptor] No token available, request will rely on cookie');
  }

  return next(req).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        // Don't intercept 401s during login flow or initial load to avoid loops
        if (!req.url.includes('/auth/me') && !req.url.includes('/auth/login')) {
          console.log('[Auth Interceptor] 401 Unauthorized detected - handling session expiration');
          authService.handleSessionExpired();
        }
      }
      return throwError(() => error);
    })
  );
};
