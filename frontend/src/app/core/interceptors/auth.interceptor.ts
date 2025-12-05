import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // Get token from localStorage
  const token = localStorage.getItem('dev_access_token');

  console.log('[Auth Interceptor]', {
    url: req.url,
    hasToken: !!token,
    tokenLength: token?.length,
    method: req.method
  });

  // Clone request and add Authorization header if token exists
  if (token) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
    console.log('[Auth Interceptor] Authorization header added');
  } else {
    console.log('[Auth Interceptor] No token available, request will rely on cookie');
  }

  return next(req);
};
