# Security Assessment and Proposal

## Executive Summary

This document presents a security review of the MultiPrompt Sandbox application, focusing on secret management and authentication flows. The review identified a critical issue regarding the exposure of authentication tokens in production environments due to a "development workaround" that persists in the codebase. Additionally, configuration management practices were reviewed, identifying areas where hardcoded values should be replaced with environment variables.

## Identified Security Issues & Gaps

### 1. Insecure Token Storage (Critical)

**Issue:**
The application uses a hybrid authentication approach where the backend sets an `HttpOnly` cookie (secure) but *also* sends the JWT access token in the URL query parameters to the frontend. The frontend then captures this token and stores it in `localStorage` (or `sessionStorage`) under the key `dev_access_token`.

**Risk:**
- **XSS Vulnerability:** Storing sensitive tokens in `localStorage` makes them accessible to any JavaScript running on the page. If the application has a Cross-Site Scripting (XSS) vulnerability, an attacker can steal the token and impersonate the user.
- **URL Leakage:** Passing tokens in the URL (even as a query parameter or hash) risks leaking them in browser history, proxy logs, and `Referer` headers.

**Evidence:**
- `backend/api/v1/auth.py`: Redirects to `${redirect_base}/auth/callback?token={jwt_token}`.
- `frontend/src/app/core/services/auth.service.ts`: Explicitly looks for `dev_access_token` and stores it.
- `frontend/src/auth-callback.html`: A static file that extracts the token from the URL and saves it to storage.

### 2. Hardcoded Configuration in Code

**Issue:**
`backend/core/config.py` contains hardcoded production URLs in the fallback logic. While environment variables take precedence, having specific production infrastructure details in the source code is bad practice and requires code changes for infrastructure updates.

**Evidence:**
```python
# backend/core/config.py
if self.ENVIRONMENT == "production":
    origins.extend([
        "https://multiprompt-frontend-595703335416.us-central1.run.app",
        # ...
    ])
```

### 3. "Dev Access Token" Workaround in Production

**Issue:**
The variable name `dev_access_token` and comments like `// If a token is provided in the hash (dev environment workaround)` suggest this was intended for development but is now the primary auth mechanism for some flows (especially mobile/iOS compatibility mentioned in comments).

## Proposed Changes

The following changes propose a move to a strictly cookie-based authentication flow (HttpOnly cookies), removing `localStorage` usage for auth tokens.

### 1. Backend: Stop Sending Token in URL

Modify `backend/api/v1/auth.py` to stop appending the token to the redirect URL. The `HttpOnly` cookie is sufficient and secure.

**Location:** `backend/api/v1/auth.py`

```python
<<<<<<< SEARCH
        # Redirect to frontend with token in query parameter for localStorage
        # AND set cookie for browsers that support it
        redirect_url = f"{redirect_base}/auth/callback?token={jwt_token}"
        logger.info(f"Redirecting to: {redirect_url}")
=======
        # Redirect to frontend - rely on cookie for authentication
        redirect_url = f"{redirect_base}/auth/callback"
        logger.info(f"Redirecting to: {redirect_url}")
>>>>>>> REPLACE
```

### 2. Frontend: Remove Token Storage Logic

Update `AuthService` to stop looking for and storing the token.

**Location:** `frontend/src/app/core/services/auth.service.ts`

```typescript
<<<<<<< SEARCH
  async handleCallback(tokenFromHash: string | null = null): Promise<void> {
    console.log('[Auth Service] handleCallback called', {
      hasTokenFromHash: !!tokenFromHash,
      tokenLength: tokenFromHash?.length,
      hasLocalStorageToken: !!localStorage.getItem('dev_access_token'),
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString()
    });

    this.errorSignal.set(null);

    // If a token is provided in the hash (dev environment workaround)
    if (tokenFromHash) {
      try {
        localStorage.setItem('dev_access_token', tokenFromHash);
        console.log('[Auth Service] Token stored in localStorage successfully');
        // Remove the token from the URL hash to clean up the URL
        this.router.navigate([], { replaceUrl: true, fragment: undefined });
      } catch (error) {
        console.error('[Auth Service] Failed to store token in localStorage:', error);
        this.errorSignal.set({
          message: 'Failed to store authentication token. Please check browser settings.',
          code: 'STORAGE_FAILED'
        });
        return;
      }
    }

    // Attempt to load the user (will now also check localStorage token if available)
    console.log('[Auth Service] Attempting to load user...');
    await this.loadUser();
=======
  async handleCallback(): Promise<void> {
    console.log('[Auth Service] handleCallback called', {
      timestamp: new Date().toISOString()
    });

    this.errorSignal.set(null);

    // Attempt to load the user (relying on HttpOnly cookie)
    console.log('[Auth Service] Attempting to load user...');
    await this.loadUser();
>>>>>>> REPLACE
```

And remove storage checks in `loadUser`:

```typescript
<<<<<<< SEARCH
  async loadUser(): Promise<void> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);

    const hasLocalStorageToken = !!localStorage.getItem('dev_access_token');
    const hasSessionStorageToken = !!sessionStorage.getItem('dev_access_token');
    console.log('[Auth Service] loadUser - starting', {
      apiUrl: this.API_URL,
      hasLocalStorageToken,
      hasSessionStorageToken,
      userAgent: navigator.userAgent
    });
=======
  async loadUser(): Promise<void> {
    this.loadingSignal.set(true);
    this.errorSignal.set(null);

    console.log('[Auth Service] loadUser - starting', {
      apiUrl: this.API_URL,
      userAgent: navigator.userAgent
    });
>>>>>>> REPLACE
```

And logout cleanup:

```typescript
<<<<<<< SEARCH
    // Clear localStorage token
    try {
      localStorage.removeItem('dev_access_token');
      console.log('[Auth Service] logout - localStorage cleared');
    } catch (error) {
      console.error('[Auth Service] logout - failed to clear localStorage:', error);
    }
=======
    // LocalStorage token cleanup not needed (using cookies)
>>>>>>> REPLACE
```

### 3. Frontend: Simplify Interceptor

The interceptor no longer needs to manually attach headers if we rely on cookies.

**Location:** `frontend/src/app/core/interceptors/auth.interceptor.ts`

```typescript
<<<<<<< SEARCH
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
=======
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // Request will rely on HttpOnly cookies (handled by browser)
  return next(req);
};
>>>>>>> REPLACE
```

### 4. Backend: Clean Config

Remove hardcoded URLs.

**Location:** `backend/core/config.py`

```python
<<<<<<< SEARCH
        # Add Cloud Run URLs if in production
        if self.ENVIRONMENT == "production":
            origins.extend([
                "https://multiprompt-frontend-595703335416.us-central1.run.app",
                "https://multiprompt-frontend-595703335416.us-central1.run.app/",
            ])
        return origins
=======
        return origins
>>>>>>> REPLACE
```

## Additional Recommendations

1.  **Secret Rotation:** Implement an automated key rotation strategy for `SECRET_KEY` and Google OAuth credentials using Google Secret Manager.
2.  **CSP Headers:** Implement Content Security Policy (CSP) headers in the Nginx configuration to further mitigate XSS risks.
3.  **Strict Cookie Settings:** Ensure `SameSite=Strict` is used where possible, falling back to `Lax` only if necessary. The current `SameSite=None` in production is required for cross-site cookie usage but makes CSRF protection more critical (FastAPI handles this if configured). Since frontend and backend are on different domains (in production Cloud Run), `SameSite=None` + `Secure` is correct, but requires careful handling.
