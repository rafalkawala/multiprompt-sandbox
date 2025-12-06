import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="login-container">
      <mat-card class="login-card">
        <mat-card-header>
          <mat-card-title>MultiPrompt Sandbox</mat-card-title>
          <mat-card-subtitle>MLLM Benchmarking Platform</mat-card-subtitle>
        </mat-card-header>

        <mat-card-content>
          <p class="description">
            Sign in to access the benchmarking platform and manage your experiments.
          </p>

          @if (authService.error()) {
            <div class="error-message">
              <mat-icon>error</mat-icon>
              <span>{{ authService.error()?.message }}</span>
            </div>
          }
        </mat-card-content>

        <mat-card-actions>
          <button
            mat-raised-button
            color="primary"
            (click)="login()"
            [disabled]="loading"
            class="google-btn">
            @if (loading) {
              <mat-spinner diameter="20"></mat-spinner>
            } @else {
              <img src="https://www.google.com/favicon.ico" alt="Google" class="google-icon">
              Sign in with Google
            }
          </button>
        </mat-card-actions>
      </mat-card>
    </div>
  `,
  styles: [`
    .login-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      width: 100%;
      padding: 16px; /* Handles safe spacing from edges on mobile */
    }

    .login-card {
      max-width: 400px;
      width: 100%;
      /* margin: 16px; -- REMOVED: Caused overflow on mobile (100% + 32px) */
      padding: 24px;
    }

    mat-card-header {
      justify-content: center;
      text-align: center;
      margin-bottom: 16px;
    }

    mat-card-title {
      font-size: 24px !important;
      margin-bottom: 8px;
    }

    .description {
      text-align: center;
      color: rgba(0, 0, 0, 0.6);
      margin: 16px 0;
    }

    .error-message {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      background: #ffebee;
      border-radius: 4px;
      color: #c62828;
      margin: 16px 0;
      font-size: 14px;
    }

    .error-message mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    mat-card-actions {
      display: flex;
      justify-content: center;
      padding: 16px 0;
    }

    .google-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 24px;
    }

    .google-icon {
      width: 18px;
      height: 18px;
    }

    mat-spinner {
      display: inline-block;
    }
  `]
})
export class LoginComponent {
  loading = false;

  constructor(public authService: AuthService) {}

  async login(): Promise<void> {
    this.loading = true;
    this.authService.clearError();
    try {
      await this.authService.login();
    } catch (error) {
      console.error('Login failed:', error);
      this.loading = false;
    }
  }
}
