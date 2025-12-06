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
    // Extract token from URL (query param or hash)
    let token: string | null = null;

    const searchParams = new URLSearchParams(window.location.search);
    const hash = window.location.hash;
    const fullUrl = window.location.href;

    console.log('[Auth Callback] Processing callback', {
      hasQuery: !!window.location.search,
      hasHash: !!hash,
      fullUrl: fullUrl,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString()
    });

    // Try query parameter first (new mobile-friendly approach)
    token = searchParams.get('token');
    if (token) {
      console.log('[Auth Callback] Token extracted from query param', {
        tokenLength: token.length
      });
    }

    // Fallback: Try hash fragment (legacy approach)
    if (!token && hash && hash.includes('token=')) {
      try {
        const hashParams = hash.startsWith('#') ? hash.substring(1) : hash;
        const params = new URLSearchParams(hashParams);
        token = params.get('token');

        if (!token) {
          const parts = hashParams.split('token=');
          if (parts.length > 1) {
            token = parts[1].split('&')[0];
          }
        }

        if (token) {
          console.log('[Auth Callback] Token extracted from hash', {
            tokenLength: token.length
          });
        }
      } catch (error) {
        console.error('[Auth Callback] Error extracting token from hash:', error);
      }
    }

    if (!token) {
      console.log('[Auth Callback] No token in URL, relying on cookie authentication');
    }

    // Store token immediately if found (before calling handleCallback)
    if (token) {
      let stored = false;
      let storageMethod = 'none';

      // Try localStorage first
      try {
        localStorage.setItem('dev_access_token', token);
        console.log('[Auth Callback] Token stored in localStorage');
        stored = true;
        storageMethod = 'localStorage';
      } catch (error) {
        console.warn('[Auth Callback] localStorage blocked or unavailable:', error);
      }

      // Fallback to sessionStorage if localStorage failed
      if (!stored) {
        try {
          sessionStorage.setItem('dev_access_token', token);
          console.log('[Auth Callback] Token stored in sessionStorage (localStorage blocked)');
          stored = true;
          storageMethod = 'sessionStorage';
        } catch (error) {
          console.error('[Auth Callback] sessionStorage also blocked:', error);
        }
      }

      if (!stored) {
        console.error('[Auth Callback] CRITICAL: Cannot store token - all storage methods blocked!');
        alert('Authentication Error:\n\nBrowser storage is blocked. Please:\n1. Disable Private Browsing mode\n2. Check Safari privacy settings\n3. Allow cookies and site data');
      } else {
        console.log(`[Auth Callback] Token successfully stored using ${storageMethod}`);
      }

      // Clean URL immediately to remove token from browser history
      try {
        window.history.replaceState({}, document.title, window.location.pathname);
        console.log('[Auth Callback] URL cleaned');
      } catch (error) {
        console.error('[Auth Callback] Failed to clean URL:', error);
      }
    }

    await this.authService.handleCallback(token);
  }
}
