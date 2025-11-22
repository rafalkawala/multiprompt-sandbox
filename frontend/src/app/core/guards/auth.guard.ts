import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = async () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Wait for auth initialization to complete
  await authService.waitForInit();

  if (authService.getToken()) {
    return true;
  }

  router.navigate(['/login']);
  return false;
};

export const adminGuard: CanActivateFn = async () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Wait for auth initialization to complete
  await authService.waitForInit();

  if (authService.isAdmin()) {
    return true;
  }

  router.navigate(['/home']);
  return false;
};
