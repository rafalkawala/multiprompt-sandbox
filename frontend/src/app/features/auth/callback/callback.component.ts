import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-auth-callback',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule],
  template: `
    <div class="callback-container">
      <mat-spinner></mat-spinner>
      <p>Completing sign in...</p>
    </div>
  `,
  styles: [`
    .callback-container {
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      gap: 16px;
    }

    p {
      color: rgba(0, 0, 0, 0.6);
    }
  `]
})
export class CallbackComponent implements OnInit {
  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.handleCallback();
  }

  private async handleCallback(): Promise<void> {
    const token = this.route.snapshot.queryParamMap.get('token');

    if (token) {
      await this.authService.handleCallback(token);
    } else {
      console.error('No token in callback');
      this.router.navigate(['/login']);
    }
  }
}
