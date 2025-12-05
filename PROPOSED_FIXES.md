# Proposed Fixes for Login Issues

## Analysis
The login issue on iPhone (and potentially other devices) likely stems from the backend redirecting to a hardcoded `FRONTEND_URL` that might not match the actual URL the user is using. This is common when the application is accessed via different domains (e.g., a default Cloud Run URL vs. a custom domain).

Additionally, the frontend callback component manually manipulates the browser history before the Angular Router processes the navigation, which can lead to race conditions or unexpected behavior, particularly on mobile browsers (Safari on iOS).

## Proposed Changes

### 1. Backend: Dynamic Redirect Support (`backend/api/v1/auth.py`)

**Goal**: Allow the authentication flow to preserve the original frontend URL through the OAuth process.

**Changes**:
1.  Modify `google_login` to capture the `referer` header or a `next` query parameter.
2.  Encode this URL into the `state` parameter of the OAuth request.
3.  Modify `google_callback` to decode the `state` parameter and use it as the redirect base if valid.

```python
# backend/api/v1/auth.py

# Add import for base64 and json to handle state encoding
import base64
import json

# ... existing imports ...

@router.get("/google/login")
async def google_login(request: Request, next: Optional[str] = None):
    """Initiate Google OAuth login"""

    # Determine the return URL
    # 1. Prefer explicitly provided 'next' param
    # 2. Fallback to Referer header
    # 3. Fallback to configured FRONTEND_URL

    frontend_url = settings.FRONTEND_URL

    if next:
        frontend_url = next
    elif request.headers.get("referer"):
        # Use origin from referer
        from urllib.parse import urlparse
        referer = request.headers.get("referer")
        parsed = urlparse(referer)
        frontend_url = f"{parsed.scheme}://{parsed.netloc}"

    # Basic validation to ensure we don't redirect to malicious sites
    # Check against ALLOWED_ORIGINS if strict security is needed

    # Create state parameter containing the return URL
    state_data = {"return_url": frontend_url}
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

    # Build the Google OAuth URL with state
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"access_type=offline&"
        f"prompt=consent&"
        f"state={state}"  # Add state parameter
    )
    return {"auth_url": google_auth_url}


@router.get("/google/callback")
async def google_callback(code: str, state: Optional[str] = None, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""

    # ... existing code ...

        # Determine redirect base URL from state
        redirect_base = settings.FRONTEND_URL
        if state:
            try:
                state_data = json.loads(base64.urlsafe_b64decode(state).decode())
                if "return_url" in state_data:
                    redirect_base = state_data["return_url"]
            except Exception as e:
                logger.warning(f"Failed to decode state parameter: {e}")

        # Redirect to frontend with token in URL hash
        # Use the dynamic redirect_base instead of settings.FRONTEND_URL
        redirect_url = f"{redirect_base}/auth/callback#token={jwt_token}"
        response = RedirectResponse(url=redirect_url)

    # ... existing code ...
```

### 2. Frontend: Robust Callback Handling (`frontend/src/app/features/auth/callback/callback.component.ts`)

**Goal**: Remove manual history manipulation that might conflict with Angular's Router, ensuring smooth navigation on all devices.

**Changes**:
1.  Remove `window.history.replaceState`.
2.  Rely on `AuthService` (which uses Angular Router) to clean the URL.

```typescript
// frontend/src/app/features/auth/callback/callback.component.ts

// ... existing code ...

  private async handleCallback(): Promise<void> {
    // Extract token from URL hash if present
    let token: string | null = null;
    const hash = window.location.hash;

    console.log('[Auth Callback] Processing callback', {
      hasHash: !!hash,
      hashLength: hash?.length,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString()
    });

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

        console.log('[Auth Callback] Token extracted', {
          tokenPresent: !!token,
          tokenLength: token?.length
        });

        // REMOVE THIS LINE:
        // window.history.replaceState(null, '', window.location.pathname);

      } catch (error) {
        console.error('[Auth Callback] Error extracting token from hash:', error, {
          hash,
          userAgent: navigator.userAgent
        });
      }
    } else {
      console.log('[Auth Callback] No token in hash, relying on cookie authentication');
    }

    await this.authService.handleCallback(token);
  }

// ... existing code ...
```
