import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
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

  return next(req);
};
