import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
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
    private router: Router,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.handleCallback();
  }

  private async handleCallback(): Promise<void> {
    // Extract token from URL hash if present
    let token: string | null = null;

    // Wait a moment for browser to fully process the URL (especially on mobile)
    await new Promise(resolve => setTimeout(resolve, 100));

    const hash = window.location.hash;
    const href = window.location.href;

    console.log('[Auth Callback] Processing callback', {
      hasHash: !!hash,
      hashLength: hash?.length,
      fullUrl: href,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString()
    });

    // Try multiple methods to extract the token (mobile browsers can be tricky)
    if (hash && hash.includes('token=')) {
      try {
        // Remove leading # if present
        const hashParams = hash.startsWith('#') ? hash.substring(1) : hash;

        // Parse the hash parameters more robustly
        const params = new URLSearchParams(hashParams);
        token = params.get('token');

        if (!token) {
          // Fallback to simple split if URLSearchParams didn't work
          const parts = hashParams.split('token=');
          if (parts.length > 1) {
            // Take everything after 'token=' and before any & or end
            token = parts[1].split('&')[0];
          }
        }

        console.log('[Auth Callback] Token extracted from hash', {
          tokenPresent: !!token,
          tokenLength: token?.length
        });
      } catch (error) {
        console.error('[Auth Callback] Error extracting token from hash:', error, {
          hash,
          userAgent: navigator.userAgent
        });
      }
    } else if (href.includes('#token=')) {
      // Fallback: extract from full URL if hash isn't populated
      try {
        const urlParts = href.split('#token=');
        if (urlParts.length > 1) {
          token = urlParts[1].split('&')[0];
          console.log('[Auth Callback] Token extracted from href', {
            tokenPresent: !!token,
            tokenLength: token?.length
          });
        }
      } catch (error) {
        console.error('[Auth Callback] Error extracting token from href:', error);
      }
    } else {
      console.log('[Auth Callback] No token in URL, relying on cookie authentication');
    }

    // Store token immediately if found (before calling handleCallback)
    if (token) {
      try {
        localStorage.setItem('dev_access_token', token);
        console.log('[Auth Callback] Token pre-stored in localStorage');
      } catch (error) {
        console.error('[Auth Callback] Failed to pre-store token:', error);
      }
    }

    await this.authService.handleCallback(token);
  }
}
