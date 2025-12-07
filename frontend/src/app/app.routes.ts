import { Routes } from '@angular/router';
import { authGuard, adminGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/home',
    pathMatch: 'full'
  },
  {
    path: 'auth/callback',
    loadComponent: () => import('./features/auth/callback/callback.component').then(m => m.CallbackComponent)
  },
  {
    path: 'home',
    loadComponent: () => import('./features/home/home.component').then(m => m.HomeComponent),
    canActivate: [authGuard]
  },
  {
    path: 'projects',
    loadComponent: () => import('./features/projects/projects.component').then(m => m.ProjectsComponent),
    canActivate: [authGuard]
  },
  {
    path: 'projects/:id',
    loadComponent: () => import('./features/projects/project-detail.component').then(m => m.ProjectDetailComponent),
    canActivate: [authGuard]
  },
  {
    path: 'annotations',
    loadComponent: () => import('./features/annotations/annotations-list.component').then(m => m.AnnotationsListComponent),
    canActivate: [authGuard]
  },
  {
    path: 'projects/:projectId/datasets/:datasetId/annotate',
    loadComponent: () => import('./features/annotations/annotation.component').then(m => m.AnnotationComponent),
    canActivate: [authGuard]
  },
  {
    path: 'models',
    loadComponent: () => import('./features/models/models.component').then(m => m.ModelsComponent),
    canActivate: [authGuard, adminGuard]
  },
  {
    path: 'evaluations/compare',
    loadComponent: () => import('./features/evaluations/compare/compare.component').then(m => m.CompareComponent),
    canActivate: [authGuard]
  },
  {
    path: 'evaluations',
    loadComponent: () => import('./features/evaluations/evaluations.component').then(m => m.EvaluationsComponent),
    canActivate: [authGuard]
  },
  {
    path: 'labelling-jobs',
    loadComponent: () => import('./features/labelling-jobs/labelling-jobs.component').then(m => m.LabellingJobsComponent),
    canActivate: [authGuard]
  },
  {
    path: 'admin/users',
    loadComponent: () => import('./features/admin/users/users.component').then(m => m.AdminUsersComponent),
    canActivate: [authGuard, adminGuard]
  },
  {
    path: '**',
    redirectTo: '/home'
  }
];
