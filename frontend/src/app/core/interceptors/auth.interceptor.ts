import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // Add withCredentials to send cookies with requests
  const clonedReq = req.clone({
    withCredentials: true
  });

  return next(clonedReq);
};
