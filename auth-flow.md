# Authentication Flow Document

This document provides a detailed, step-by-step description of the authentication flow within the application, including all relevant parameters, redirects, and methods.

## Table of Contents
1.  [Overview](#1-overview)
2.  [Frontend Components](#2-frontend-components)
    *   [2.1 `app.routes.ts`](#21-approutes-ts)
    *   [2.2 `auth.guard.ts`](#22-authguard-ts)
    *   [2.3 `auth.service.ts`](#23-authservice-ts)
    *   [2.4 `callback.component.ts`](#24-callbackcomponent-ts)
    *   [2.5 `environment.ts`](#25-environment-ts)
3.  [Backend Components](#3-backend-components)
    *   [3.1 `main.py` (CORS)](#31-mainpy-cors)
    *   [3.2 `config.py`](#32-configpy)
    *   [3.3 `auth.py` (API Endpoints)](#33-authpy-api-endpoints)
    *   [3.4 `user.py` (User Model)](#34-userpy-user-model)
    *   [3.5 `database.py`](#35-databasepy)
4.  [Step-by-Step Authentication Flow](#4-step-by-step-authentication-flow)
    *   [4.1 Application Initialization & Route Guarding](#41-application-initialization--route-guarding)
    *   [4.2 Initiating Google OAuth Login](#42-initiating-google-oauth-login)
    *   [4.3 Google Authentication & Callback](#43-google-authentication--callback)
    *   [4.4 Frontend Callback Handling & Session Establishment](#44-frontend-callback-handling--session-establishment)
    *   [4.5 User Session Verification (`/auth/me`)](#45-user-session-verification-authme)
    *   [4.6 Logout Flow](#46-logout-flow)
5.  [Key Parameters and Variables](#5-key-parameters-and-variables)
6.  [Known Issues/Considerations](#6-known-issuesconsiderations)

---

## 1. Overview
The application uses Google OAuth2 for user authentication. The flow involves a FastAPI backend serving as an OAuth provider and an Angular frontend consuming its API. User sessions are managed primarily via HttpOnly cookies containing JWT tokens. A development-specific workaround is implemented to handle cross-origin cookie issues locally by passing the JWT via URL hash fragment.

---

## 2. Frontend Components

### 2.1 `app.routes.ts`
This file defines the routing configuration for the Angular application, playing a critical role in directing initial navigation and protecting authenticated routes.

*   **Default Route (`/`):**
    *   `path: ''`, `redirectTo: '/home'`, `pathMatch: 'full'`
    *   Any request to the application's root URL (`/`) is immediately redirected to the `/home` route.
*   **Authentication Callback Route (`/auth/callback`):**
    *   `path: 'auth/callback'`, `loadComponent: () => import('./features/auth/callback/callback.component').then(m => m.CallbackComponent)`
    *   This route is designed to handle the redirect from the OAuth provider (Google) after a successful authentication attempt. It loads the `CallbackComponent`.
*   **Home Route (`/home`):**
    *   `path: 'home'`, `loadComponent: () => import('./features/home/home.component').then(m => m.HomeComponent)`, `canActivate: [authGuard]`
    *   Loads the `HomeComponent`. This route is protected by the `authGuard`, meaning a user must be successfully authenticated to access it.
*   **Projects List Route (`/projects`):**
    *   `path: 'projects'`, `loadComponent: () => import('./features/projects/projects.component').then(m => m.ProjectsComponent)`, `canActivate: [authGuard]`
    *   Loads the `ProjectsComponent`. This route is protected by `authGuard`.
*   **Project Detail Route (`/projects/:id`):**
    *   `path: 'projects/:id'`, `loadComponent: () => import('./features/projects/project-detail.component').then(m => m.ProjectDetailComponent)`, `canActivate: [authGuard]`
    *   Loads the `ProjectDetailComponent` for a specific project ID. This route is protected by `authGuard`.
*   **Admin Users Route (`/admin/users`):**
    *   `path: 'admin/users'`, `loadComponent: () => import('./features/admin/users/users.component').then(m => m.AdminUsersComponent)`, `canActivate: [authGuard, adminGuard]`
    *   Loads the `AdminUsersComponent`. This route is protected by both `authGuard` and `adminGuard`, requiring the user to be authenticated and have an 'admin' role.
*   **Wildcard Route (`**`):**
    *   `path: '**'`, `redirectTo: '/home'`
    *   Any URL path that does not match a defined route will be redirected to the `/home` route.

### 2.2 `auth.guard.ts`
This file defines route guards that control access to different parts of the application based on the user's authentication status and role.

*   **`authGuard` (`CanActivateFn`)**
    *   **Purpose:** To protect routes that require authentication.
    *   **Dependencies:** `AuthService` (for checking authentication status).
    *   **Flow:**
        1.  **Initialization Wait:** `await authService.waitForInit()`: Ensures the `AuthService` has completed its initial check for an existing user session.
        2.  **Authentication Status Return:** `return authService.isAuthenticated()`: The guard now simply returns the current authentication status. It **does not** directly initiate the login process (`authService.login()`).
        3.  **Login Responsibility Shift:** If `isAuthenticated()` returns `false`, the route activation is denied. The responsibility for redirecting the user to a login screen or initiating the login process now lies with a higher-level component (e.g., `app.component.ts`) that observes the `AuthService`'s authentication state. This change moves the redirection logic out of the guard itself.

*   **`adminGuard` (`CanActivateFn`)**
    *   **Purpose:** To restrict access to administrative routes (e.g., `/admin/users`) to users who are both authenticated and possess the 'admin' role.
    *   **Dependencies:** `AuthService` (for checking admin status) and `Router` (for navigation).
    *   **Flow:**
        1.  **Initialization Wait:** `await authService.waitForInit()`: Similar to `authGuard`, waits for `AuthService` initialization.
        2.  **Admin Check:** `authService.isAdmin()`: Calls the `AuthService` to check if the current user has the 'admin' role. This is a computed signal based on the `userSignal`'s `role` property.
        3.  **Access Granted:** If `isAdmin()` returns `true`, the guard returns `true`, allowing navigation to the admin route.
        4.  **Access Denied:** If `isAdmin()` returns `false`, `router.navigate(['/home'])` is called to redirect the user to the home page, and the guard returns `false`, blocking access to the admin route.

### 2.3 `auth.service.ts`
This service is the central hub for managing the user's authentication state within the Angular frontend. It handles communication with the backend authentication API, stores user information, and provides methods for login, logout, and checking authentication status.

*   **Key Properties and Signals:**
    *   `API_URL`: (string) The base URL for all backend API calls, retrieved from `environment.apiUrl`.
    *   `userSignal`: (`Signal<User | null>`) Holds the current authenticated `User` object or `null` if no user is logged in. This signal is the source of truth for the user's state.
    *   `loadingSignal`: (`Signal<boolean>`) Indicates whether an authentication-related operation (e.g., `loadUser`) is currently in progress.
    *   `authInitializedSignal`: (`Signal<boolean>`) Becomes `true` once the service has completed its initial attempt to load user data (e.g., from an existing session).
    *   `errorSignal`: (`Signal<AuthError | null>`) Stores any authentication-related error details.
    *   `user`: (`Signal<Readonly<User | null>>`) A read-only view of `userSignal` for external consumption.
    *   `loading`: (`Signal<Readonly<boolean>>`) A read-only view of `loadingSignal`.
    *   `isAuthenticated`: (`Computed<boolean>`) A computed signal that evaluates to `true` if `userSignal` contains a `User` object (i.e., the user is logged in), `false` otherwise. Used by `authGuard`.
    *   `isAdmin`: (`Computed<boolean>`) A computed signal that evaluates to `true` if the logged-in user's `role` is 'admin', `false` otherwise. Used by `adminGuard`.
    *   `authInitialized`: (`Signal<Readonly<boolean>>`) A read-only view of `authInitializedSignal`.
    *   `error`: (`Signal<Readonly<AuthError | null>>`) A read-only view of `errorSignal`.
    *   `initPromise`: (`Promise<void>`) A promise that resolves once the initial authentication check (`initializeAuth`) is complete.

*   **Constructor:**
    *   Injects Angular's `HttpClient` for making API requests and `Router` for programmatic navigation.
    *   Calls the `initializeAuth()` method immediately to perform an initial check for an existing user session.

*   **`initializeAuth()` (Private Method):**
    *   Asynchronously calls `loadUser()` to attempt to retrieve user details. This is the primary mechanism for re-establishing a session (e.g., when the app starts or a page is refreshed).
    *   Sets `authInitializedSignal` to `true` after `loadUser()` completes, signifying that the service's initial state is ready.

*   **`waitForInit()`:**
    *   Returns the `initPromise`. This method is used by route guards (like `authGuard`) to pause navigation until the `AuthService` has determined the initial authentication status, preventing race conditions.

*   **`clearError()`:**
    *   Resets the `errorSignal` to `null`, clearing any displayed authentication error messages.

*   **`login()`:**
    *   Initiates the Google OAuth login flow.
    *   Makes an HTTP GET request to `${API_URL}/auth/google/login` on the backend. The backend is expected to respond with a `auth_url` (the Google login endpoint).
    *   If an `auth_url` is received, the method performs a full browser redirect to this URL, taking the user to Google's authentication page.
    *   Includes error handling for failed API calls.

*   **`handleCallback(tokenFromHash: string | null = null)`:**
    *   This method is called by the `CallbackComponent` after the user is redirected back to the frontend from Google's OAuth flow.
    *   **Development Workaround:**
        *   If `tokenFromHash` is provided (which would occur if the backend includes the JWT in the URL hash fragment in a development environment, bypassing cross-origin cookie issues), it stores this JWT in `localStorage` under the key `'dev_access_token'`.
        *   It then removes the token from the URL hash (`this.router.navigate([], { replaceUrl: true, fragment: undefined })`) to clean up the browser's address bar.
    *   Calls `loadUser()` to attempt to fetch and set the user's details, now potentially using the `dev_access_token` or relying on an `HttpOnly` cookie.
    *   If `userSignal()` is successfully populated after `loadUser()`, the user is navigated to the `/home` route.
    *   If `userSignal()` remains `null` (authentication failed post-callback), an error is set, and the user is redirected to the application's root (`/`).

*   **`loadUser()`:**
    *   Fetches the current user's profile from the backend's `${API_URL}/auth/me` endpoint.
    *   Sets `loadingSignal` to `true` and clears any previous `errorSignal`.
    *   **Authentication Credentials Logic:**
        *   Retrieves the `dev_access_token` from `localStorage`.
        *   Constructs `HttpHeaders`. If `dev_access_token` exists, an `Authorization: Bearer <token>` header is added.
        *   Makes the HTTP GET request to `/auth/me` including `withCredentials: true` (to send any browser-managed cookies, e.g., `HttpOnly` cookies set by the backend) and the constructed `HttpHeaders`.
        *   `responseType: 'json'` is explicitly set to ensure correct parsing of the backend response.
    *   If successful, `userSignal` is updated with the returned `User` object.
    *   Includes robust error handling for various `HttpErrorResponse` statuses:
        *   `401 Unauthorized`: User is set to `null` (expected for unauthenticated state).
        *   `400 Bad Request`: Handles cases like deactivated user accounts.
        *   Other errors: Catches network or server connectivity issues.
    *   Ensures `loadingSignal` is reset to `false` in the `finally` block.

*   **`logout()`:**
    *   Initiates the user logout sequence.
    *   Makes an HTTP POST request to `${API_URL}/auth/logout` on the backend, which is expected to invalidate the server-side session/cookie.
    *   Locally clears `userSignal` and `errorSignal`, effectively logging out the user from the frontend's perspective.
    *   Includes error logging for failed logout attempts.


### 2.4 `callback.component.ts`
This is a standalone Angular component specifically designed to process the redirect back to the frontend after a user has completed the authentication process with an external OAuth provider (e.g., Google).

*   **Purpose:** To serve as a temporary landing page that captures authentication details (like a JWT token) from the URL and delegates the actual session establishment to the `AuthService`. It provides visual feedback to the user while this background processing occurs.
*   **Dependencies:** `AuthService` (for processing the authentication result) and `Router` (for potential navigation, though primarily handled by `AuthService`).
*   **Template:** Displays a `mat-spinner` and the text "Completing sign in...", indicating that background work is in progress.
*   **`ngOnInit()`:**
    *   This lifecycle hook ensures that the `handleCallback()` method is invoked as soon as the component is initialized, typically when the browser navigates to `/auth/callback`.
*   **`handleCallback()` (Private Method):**
    *   It now simply calls `this.authService.handleCallback()`.
    *   The previous logic for extracting a `token` from `window.location.hash` and passing it to `AuthService` has been removed. This means the frontend's `CallbackComponent` now expects the authentication to be solely managed through HttpOnly cookies set by the backend, rather than any development-specific URL hash workaround.


### 2.5 `environment.ts`
This file defines environment-specific configuration variables that the Angular frontend application uses. These settings allow for different behaviors and endpoints depending on whether the application is running in development, production, or other environments.

*   **`production: boolean`**:
    *   **Value:** `false` (in `environment.ts`), `true` (in `environment.prod.ts`).
    *   **Description:** A flag indicating whether the current environment is for production deployment. When `false`, it typically enables development-specific features like debugging, hot-reloading, and might influence logging levels or error reporting.
*   **`apiUrl: string`**:
    *   **Value:** `'http://localhost:8000/api/v1'` (in `environment.ts`).
    *   **Description:** Specifies the base URL for all API requests originating from the frontend application. In a local development setup, this points to the address and port where the backend API server is expected to be running. This is critical for the frontend to locate and communicate with the backend's authentication and other services.

---

## 3. Backend Components

### 3.1 `main.py` (CORS)
This file serves as the main entry point for the FastAPI application, where the application instance is created, middleware is configured, and API routes are included. The Cross-Origin Resource Sharing (CORS) configuration within this file is particularly vital for the authentication flow, as it dictates how the frontend (running on a potentially different origin) can interact with the backend.

*   **CORS Middleware (`CORSMiddleware`)**:
    *   **Purpose:** To enable browsers to permit requests from specific origins to access resources on the backend, which would otherwise be blocked by the browser's same-origin policy. This is essential when the frontend and backend are hosted on different domains or ports (e.g., `localhost:4200` for frontend and `localhost:8000` for backend).
    *   **Key Parameters for Authentication:**
        *   `allow_origins=settings.ALLOWED_ORIGINS`:
            *   **Description:** This parameter specifies a list of allowed origins (URLs) from which the backend will accept cross-origin requests. The `settings.ALLOWED_ORIGINS` property is dynamically determined by the `CORS_ALLOWED_ORIGINS` environment variable or defaults to common local development origins (`http://localhost:4200`, `http://localhost:3000`, `http://localhost:8080`) for development.
            *   **Impact on Auth Flow:** The frontend's URL (`http://localhost:4200` in development) **must** be included in this list for the browser to allow API calls to the backend.
        *   `allow_credentials=True`:
            *   **Description:** This parameter is **crucial** for authentication. When set to `True`, it instructs browsers to include credentials (such as `HttpOnly` cookies, `Authorization` headers, or TLS client certificates) with cross-origin requests.
            *   **Impact on Auth Flow:** Without `allow_credentials=True`, the browser would *not* send the `auth_token` HttpOnly cookie (set by the backend during the OAuth callback) along with subsequent frontend requests to the backend (e.g., `/auth/me`). This would result in the backend failing to authenticate the user for those requests.
        *   `allow_methods=["*"]`: Allows all HTTP methods (GET, POST, PUT, DELETE, etc.) for cross-origin requests.
        *   `allow_headers=["*"]`: Allows all HTTP headers for cross-origin requests.

*   **`@app.on_event("startup") async def sync_admin_users()`:**
    *   **Purpose:** On application startup, this function checks if any emails listed in `settings.ADMIN_EMAIL_LIST` exist in the database. If they do and their role is not already 'admin', their role is upgraded to 'admin'. If the user does not exist, a log entry is made indicating they will get admin status on first login.
    *   **Impact on Auth Flow:** This ensures that predefined administrative users have the correct permissions within the application, affecting access control managed by `adminGuard` on the frontend.

*   **`app.include_router(api_router, prefix="/api/v1")`:**
    *   **Purpose:** Mounts the API router (defined in `api.v1.__init__.py`, which includes `api.v1.auth.py`) under the `/api/v1` prefix.
    *   **Impact on Auth Flow:** This makes all authentication endpoints (e.g., `/api/v1/auth/google/login`, `/api/v1/auth/me`) accessible.

This file ensures the foundational communication layer for authentication is correctly established.

### 3.2 `config.py`
This file defines the application's configuration settings using Pydantic's `BaseSettings`. These settings are crucial for the authentication flow, as they configure backend interaction with Google OAuth, JWT issuance, and communication with the frontend. Values are typically loaded from environment variables or a `.env` file.

*   **`ENVIRONMENT: str`**:
    *   **Default Value:** `"development"`
    *   **Description:** Specifies the application's current operating environment.
    *   **Impact on Auth Flow:** Affects conditional logic within the backend's `google_callback` endpoint (e.g., determining if the JWT should be passed in the URL hash for development workarounds, and setting the `secure` flag on cookies).
*   **`CORS_ALLOWED_ORIGINS: str` / `ALLOWED_ORIGINS` property**:
    *   **Description:** Controls which origins (frontend URLs) are permitted to make cross-origin requests to the backend API. The `ALLOWED_ORIGINS` property parses `CORS_ALLOWED_ORIGINS` from the environment or defaults to common local frontend addresses (e.g., `http://localhost:4200`, `http://localhost:3000`) for development.
    *   **Impact on Auth Flow:** Directly configured in `main.py`'s `CORSMiddleware`, this ensures the frontend can successfully send authenticated requests (including cookies) to the backend.
*   **`SECRET_KEY: str`**:
    *   **Description:** A critical cryptographic key used for signing and verifying JSON Web Tokens (JWTs). Must be a strong, randomly generated string and kept secret.
    *   **Impact on Auth Flow:** Essential for the security and integrity of the JWTs that represent user sessions. A compromised `SECRET_KEY` would allow malicious actors to forge JWTs.
*   **`ALGORITHM: str`**:
    *   **Default Value:** `"HS256"`
    *   **Description:** The cryptographic algorithm used for signing the JWTs.
    *   **Impact on Auth Flow:** Defines the method by which JWTs are encoded and decoded.
*   **`ACCESS_TOKEN_EXPIRE_MINUTES: int`**:
    *   **Default Value:** `30`
    *   **Description:** The duration (in minutes) for which an issued JWT access token is considered valid.
    *   **Impact on Auth Flow:** Determines the lifespan of a user's session before re-authentication or token refresh is required.
*   **`GOOGLE_CLIENT_ID: str`**:
    *   **Description:** The unique client ID assigned to your application by Google during the OAuth 2.0 client registration process.
    *   **Impact on Auth Flow:** Identifies your application to Google when initiating the OAuth login.
*   **`GOOGLE_CLIENT_SECRET: str`**:
    *   **Description:** The secret key associated with your `GOOGLE_CLIENT_ID`, also obtained from Google. Must be kept confidential.
    *   **Impact on Auth Flow:** Used by the backend to securely exchange the authorization code received from Google for an access token during the OAuth callback.
*   **`GOOGLE_REDIRECT_URI: str`**:
    *   **Default Value:** `"http://localhost:8000/api/v1/auth/google/callback"`
    *   **Description:** The URI within your backend application to which Google redirects the user after they have granted or denied permissions. This URI **must** be pre-registered and exactly match one of the authorized redirect URIs in your Google Cloud Console project.
    *   **Impact on Auth Flow:** This is the backend endpoint that receives the authorization code, allowing the backend to complete the OAuth handshake and establish a user session.
*   **`FRONTEND_URL: str`**:
    *   **Default Value:** `"http://localhost:4200"`
    *   **Description:** The base URL of the frontend application.
    *   **Impact on Auth Flow:** Used by the backend to construct the final redirect URL that sends the user back to the frontend's `CallbackComponent` after successful backend OAuth processing. This is crucial for completing the login flow on the client side.
*   **`ADMIN_EMAILS: str` / `ADMIN_EMAIL_LIST` property**:
    *   **Description:** A comma-separated string of email addresses that, upon successful initial login or during application startup, will automatically be granted the 'admin' user role.
    *   **Impact on Auth Flow:** Determines which users receive administrative privileges, affecting access to routes protected by `adminGuard` on the frontend.
*   **`validate_production_settings()`**:
    *   **Purpose:** A method that runs on application startup to ensure that critical security-related environment variables (like `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) are set when `ENVIRONMENT` is "production".
    *   **Impact on Auth Flow:** Helps prevent deployment errors and security vulnerabilities by enforcing required configurations in production environments.

This configuration file is the central repository for parameters influencing every stage of the authentication process.

### 3.3 `auth.py` (API Endpoints)
This FastAPI router file (`backend/api/v1/auth.py`) is the central component for handling all backend authentication logic. It integrates with Google OAuth 2.0, manages JWT creation and validation, and handles user session cookies.

*   **OAuth Setup (`oauth.register`)**:
    *   Initializes `authlib`'s OAuth client for Google.
    *   Configured with `settings.GOOGLE_CLIENT_ID`, `settings.GOOGLE_CLIENT_SECRET`, and Google's standard OpenID Connect discovery URL.
    *   Requests `openid`, `email`, and `profile` scopes from Google, ensuring access to basic user information.

*   **`get_db()` (Dependency Function)**:
    *   **Purpose:** Provides a SQLAlchemy database session (`SessionLocal`) for each incoming request that requires database interaction.
    *   **Impact on Auth Flow:** Ensures proper management of database connections when creating or updating user records during the OAuth callback, or when retrieving user details for protected endpoints.

*   **`create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str`**:
    *   **Purpose:** A utility function to generate a JSON Web Token (JWT).
    *   **Parameters:**
        *   `data`: A dictionary of claims (payload) to be embedded in the JWT (e.g., user email as `sub`, user role).
        *   `expires_delta`: An optional `timedelta` object to specify a custom expiration time. If `None`, `settings.ACCESS_TOKEN_EXPIRE_MINUTES` is used.
    *   **Logic:** Encodes the provided `data` along with an `exp` (expiration timestamp) claim, using `settings.SECRET_KEY` for signing and `settings.ALGORITHM` (e.g., HS256).
    *   **Impact on Auth Flow:** This token serves as the primary credential for identifying an authenticated user's session.

*   **`get_current_user(request: Request, db: Session = Depends(get_db), auth_token: Optional[str] = Cookie(default=None)) -> User` (Dependency Function)**:
    *   **Purpose:** This is a crucial FastAPI dependency that authenticates a user based on a provided JWT and retrieves their corresponding `User` object from the database. It protects API endpoints that require authentication.
    *   **Mechanism:**
        1.  **Token Extraction:** It first attempts to read the JWT from an `HttpOnly` cookie named `"auth_token"`. If the cookie is not present, it then checks the `Authorization` header for a `Bearer <token>` scheme.
        2.  **JWT Validation:** Decodes the extracted token using `jose.jwt.decode` with `settings.SECRET_KEY` and `settings.ALGORITHM`. Handles `JWTError` for invalid or expired tokens.
        3.  **User Lookup:** Extracts the user's `email` (subject `sub`) from the JWT payload and queries the database (`db.query(User).filter(User.email == email).first()`) to fetch the full `User` object.
        4.  **Authorization Checks:** Verifies that a user with the given email exists and that `user.is_active` is `True`.
        5.  **Error Handling:** Raises `HTTPException` (401 Unauthorized or 400 Bad Request for inactive users) if any validation step fails.
    *   **Impact on Auth Flow:** Ensures that only valid, active, and authenticated users can access protected backend resources (e.g., `/api/v1/me`).

*   **`@router.get("/google/login") async def google_login()`**:
    *   **Purpose:** Endpoint for initiating the Google OAuth 2.0 login sequence from the frontend.
    *   **Logic:** Dynamically constructs the Google OAuth authorization URL, incorporating `settings.GOOGLE_CLIENT_ID`, `settings.GOOGLE_REDIRECT_URI` (pointing to the backend's callback endpoint), and required scopes (`openid email profile`).
    *   **Return:** Returns a JSON object containing the `auth_url`. The frontend (`AuthService.login()`) then performs a `window.location.href` redirect to this URL.

*   **`@router.get("/google/callback") async def google_callback(code: str, db: Session = Depends(get_db))`**:
    *   **Purpose:** This is the designated backend endpoint where Google redirects the user after they successfully authenticate and authorize the application. It completes the OAuth handshake and establishes the user's session.
    *   **Parameters:** `code` (the authorization code from Google), `db` (database session).
    *   **Logic:**
        1.  **Token Exchange with Google:** Uses `httpx.AsyncClient` to send a POST request to Google's token endpoint (`https://oauth2.googleapis.com/token`), exchanging the received `code` for Google's `access_token` and other tokens, using `settings.GOOGLE_CLIENT_ID`, `settings.GOOGLE_CLIENT_SECRET`, and `settings.GOOGLE_REDIRECT_URI`.
        2.  **User Info from Google:** Uses Google's `access_token` to make a GET request to Google's `userinfo` endpoint, retrieving the user's email, name, picture, and Google ID.
        3.  **User Management (Database):**
            *   Queries the local database for an existing `User` with the retrieved email.
            *   If the user does not exist, a new `User` record is created, with their `role` defaulting to `UserRole.USER` or `UserRole.ADMIN` if their email is in `settings.ADMIN_EMAIL_LIST`.
            *   If the user exists, their details (`google_id`, `name`, `picture_url`, `last_login_at`) are updated.
        4.  **JWT Generation:** Calls `create_access_token` to generate a new JWT for the authenticated user based on their stored `email` and `role`.
        5.  **Frontend Redirect & Session Establishment:**
            *   Constructs a `RedirectResponse` object, setting its destination URL to `${settings.FRONTEND_URL}/auth/callback`.
            *   **HttpOnly Cookie:** Sets an `HttpOnly` cookie named `"auth_token"` with the generated `jwt_token` as its value.
                *   `httponly=True`: Prevents client-side JavaScript access to the cookie, enhancing security.
                *   `secure=is_production`: The `secure` flag is only set if `ENVIRONMENT` is "production" (requiring HTTPS).
                *   `samesite="none"` (in production) / `"lax"` (in development): This is critical for cross-origin cookie behavior. `SameSite=None` is required when cookies are sent from a different site (domain) in a cross-site context (e.g., frontend on `app.com`, backend on `api.app.com`). `SameSite=None` requires the `Secure` attribute to be set (which `secure=is_production` handles). In development, `SameSite=Lax` is typically sufficient.
                *   `max_age`: Set based on `settings.ACCESS_TOKEN_EXPIRE_MINUTES`.
                *   `path="/"`: Makes the cookie available across the entire domain.
    *   **Return:** Returns the `RedirectResponse` to the user's browser, directing them back to the frontend application to complete the login process.

*   **`@router.get("/me") async def get_me(current_user: User = Depends(get_current_user))`**:
    *   **Purpose:** A protected API endpoint that allows an authenticated frontend client to retrieve the profile details of the currently logged-in user.
    *   **Dependencies:** Uses the `get_current_user` dependency to ensure that only a valid, authenticated user can access this endpoint. If `get_current_user` fails, an `HTTPException` is raised before this endpoint's logic is executed.
    *   **Return:** Returns a dictionary containing the authenticated `User`'s ID, email, name, picture URL, role, activity status, creation timestamp, and last login timestamp.

*   **`@router.post("/logout") async def logout()`**:
    *   **Purpose:** Endpoint to log out the user by instructing the browser to remove the authentication cookie.
    *   **Logic:** Creates a `Response` object and uses `response.delete_cookie("auth_token", ...)` to set an expired cookie for `auth_token`, effectively deleting it from the browser.
    *   **Return:** Returns a simple JSON success message.

This file is the backbone of the application's authentication and session management.

### 3.4 `user.py` (User Model)
This file defines the SQLAlchemy ORM (Object-Relational Mapper) model for the `User` entity, which represents a user account stored in the application's database. It also defines an Enum for user roles.

*   **`UserRole` (Enum)**:
    *   **Purpose:** To define a set of discrete, permissible roles that a user can be assigned within the application. Using an Enum provides type safety and clarity.
    *   **Values:**
        *   `ADMIN = "admin"`
        *   `USER = "user"`
        *   `VIEWER = "viewer"`
    *   **Impact on Auth Flow:** The `google_callback` endpoint in `auth.py` uses this Enum to assign a role to new users, potentially promoting users to `ADMIN` based on `settings.ADMIN_EMAIL_LIST`. The assigned role is stored in the user's record, included in the JWT payload, and subsequently used by the frontend's `AuthService.isAdmin()` and `adminGuard` for role-based access control.

*   **`User` (SQLAlchemy ORM Model)**:
    *   **`__tablename__ = "users"`:** Specifies that this ORM model maps to a database table named `users`.
    *   **`id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`:**
        *   **Description:** The primary key for the user, a universally unique identifier (UUID).
        *   **Impact on Auth Flow:** Provides a stable, unique reference for each user record.
    *   **`email = Column(String, unique=True, index=True, nullable=False)`:**
        *   **Description:** The user's email address. It must be unique across all users and is indexed for efficient lookup.
        *   **Impact on Auth Flow:** This is the primary identifier for the user during the OAuth process and is stored as the "subject" (`sub`) claim in the JWT.
    *   **`name = Column(String, nullable=True)`:**
        *   **Description:** The user's full name, typically retrieved from their Google profile.
    *   **`picture_url = Column(String, nullable=True)`:**
        *   **Description:** A URL to the user's profile picture, typically retrieved from their Google profile.
    *   **`google_id = Column(String, unique=True, index=True, nullable=True)`:**
        *   **Description:** The unique identifier assigned to the user by Google.
        *   **Impact on Auth Flow:** Provides a direct link between the application's user record and the user's Google account, useful for preventing multiple accounts for the same Google ID.
    *   **`role = Column(String, default=UserRole.USER.value, nullable=False)`:**
        *   **Description:** Stores the user's role as a string, corresponding to values from the `UserRole` Enum.
        *   **Impact on Auth Flow:** Directly determines the authorization level of the user within the application.
    *   **`is_active = Column(Boolean, default=True, nullable=False)`:**
        *   **Description:** A flag indicating whether the user's account is currently active.
        *   **Impact on Auth Flow:** The `get_current_user` dependency checks this flag; inactive users will be denied access to protected resources.
    *   **`created_at = Column(DateTime, default=datetime.utcnow)`:**
        *   **Description:** Timestamp indicating when the user account was created.
    *   **`last_login_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)`:**
        *   **Description:** Timestamp indicating the last time the user logged in.
        *   **Impact on Auth Flow:** This field is updated in the `google_callback` endpoint upon successful login.

This model forms the foundation for managing user identities, roles, and status, all of which are essential inputs to the application's authentication and authorization decisions.

### 3.5 `database.py`
This file is responsible for setting up and managing the database connection for the FastAPI backend using SQLAlchemy. Although it doesn't contain direct authentication logic, it provides the essential infrastructure for storing and retrieving user data, which is fundamental to the authentication and authorization processes.

*   **Database URL Construction:**
    *   The `db_url` is dynamically constructed. It first attempts to use `settings.DATABASE_URL` (which can be a complete URL from an environment variable).
    *   If `settings.DATABASE_URL` is not provided, it falls back to constructing the URL from individual settings: `settings.DB_USER`, `settings.DB_PASSWORD`, `settings.DB_HOST`, `settings.DB_PORT`, and `settings.DB_NAME`. This ensures flexibility for different deployment environments.

*   **`engine = create_engine(db_url, ...)`:**
    *   **Purpose:** Creates the SQLAlchemy `Engine` instance. The `Engine` is the interface to the database, handling connection pooling and dialect-specific behavior.
    *   **Impact on Auth Flow:** This `engine` is the underlying component that `SessionLocal` uses to communicate with the database for all user-related operations.

*   **`SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`:**
    *   **Purpose:** Creates a configurable `sessionmaker` class. Instances derived from `SessionLocal` will represent a database session, which acts as a staging area for objects loaded from or destined for the database.
    *   **Configuration:**
        *   `autocommit=False`: Disables automatic committing of transactions, requiring explicit `session.commit()`.
        *   `autoflush=False`: Disables automatic flushing of changes to the database before a query.
        *   `bind=engine`: Connects the sessions created by this `sessionmaker` to the `engine`.
    *   **Impact on Auth Flow:** The `get_db()` dependency in `backend/api/v1/auth.py` uses `SessionLocal()` to create a database session for each request, allowing the authentication endpoints to query, create, and update `User` records.

*   **`Base = declarative_base()`:**
    *   **Purpose:** This is the base class that all declarative SQLAlchemy ORM models (like the `User` model in `backend/models/user.py`) inherit from.
    *   **Impact on Auth Flow:** It provides the metadata necessary for SQLAlchemy to map Python classes to database tables.

In essence, `database.py` lays the groundwork for the backend's ability to store, retrieve, and manage user authentication data.

---

## 4. Step-by-Step Authentication Flow

### 4.1 Application Initialization & Route Guarding

1.  **Frontend Application Load:** The Angular application starts.
2.  **`AuthService` Instantiation:** The `AuthService` (`frontend/src/app/core/services/auth.service.ts`), being `providedIn: 'root'`, is instantiated immediately.
3.  **Initial Auth Check (`AuthService.initializeAuth()`):**
    *   The `AuthService` constructor calls `initializeAuth()`, which in turn calls `loadUser()`.
    *   `loadUser()` makes an HTTP GET request to `/api/v1/auth/me` on the backend.
    *   This request includes `withCredentials: true` to send any existing `auth_token` HttpOnly cookie that the browser might have.
    *   **Note:** The previous development workaround (sending `Authorization: Bearer` from `localStorage`) is no longer active in the current `loadUser()` implementation.
    *   The backend's `/api/v1/auth/me` endpoint (protected by `get_current_user`) attempts to validate the cookie and return the user's details.
    *   If successful (user is already authenticated), the `userSignal` in `AuthService` is set with the user's data.
    *   If unsuccessful (e.g., 401 Unauthorized), `userSignal` remains `null`.
    *   Once `loadUser()` completes, `authInitializedSignal` is set to `true`, and `initPromise` resolves.
4.  **Route Navigation & `authGuard` Activation:**
    *   The browser attempts to navigate to the application's root (`/`).
    *   `frontend/src/app/app.routes.ts` redirects `''` to `/home`.
    *   The `authGuard` (`frontend/src/app/core/guards/auth.guard.ts`) is activated for the `/home` route.
5.  **`authGuard` Execution:**
    *   `authGuard` calls `authService.waitForInit()`, ensuring the initial authentication check is complete before proceeding.
    *   It then checks `authService.isAuthenticated()`.
    *   **Scenario A: User is Authenticated:** If `isAuthenticated()` is `true`, `authGuard` returns `true`, allowing navigation to `/home`, and the `HomeComponent` is loaded.
    *   **Scenario B: User is NOT Authenticated:** If `isAuthenticated()` is `false`, `authGuard` returns `false`, preventing immediate route activation. At this point, a higher-level component (e.g., `app.component.ts`) is expected to observe `AuthService.isAuthenticated()` and redirect the user to a login screen or initiate `authService.login()`.
    ### 4.2 Initiating Google OAuth Login
    
    1.  **Login Trigger:** A higher-level component (e.g., `app.component.ts`) observes that `AuthService.isAuthenticated()` is `false` and explicitly calls `authService.login()`.
    2.  **Frontend Requests Google Auth URL:**
        *   `AuthService.login()` makes an HTTP GET request to the backend endpoint: `GET ${API_URL}/auth/google/login`.
        *   This request is allowed by the CORS configuration in `backend/main.py`.
    3.  **Backend (`auth.py`) Constructs Google Auth URL:**
        *   The `google_login()` endpoint in `backend/api/v1/auth.py` receives the request.
        *   It constructs a comprehensive Google OAuth URL using:
            *   `settings.GOOGLE_CLIENT_ID`
            *   `settings.GOOGLE_REDIRECT_URI` (which points back to the backend's `/api/v1/auth/google/callback` endpoint)
            *   `response_type=code`
            *   `scope=openid email profile`
            *   `access_type=offline`
            *   `prompt=consent`
        *   It returns this URL in a JSON response: `{"auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."}`.
    4.  **Frontend Redirects to Google:**
        *   Upon receiving the `auth_url` from the backend, `AuthService.login()` performs a full browser redirect: `window.location.href = response.auth_url;`.
        *   The user's browser is now directed to Google's authentication page, where they can log in to their Google account and grant permissions to the application.
        ### 4.3 Google Authentication & Callback

1.  **User Authenticates with Google:** The user interacts directly with Google's authentication page, logging in to their Google account and granting (or denying) the requested permissions (scopes: `openid email profile`).
2.  **Google Redirects to Backend Callback:** Upon successful authentication and authorization, Google redirects the user's browser back to the URI specified in `settings.GOOGLE_REDIRECT_URI`. This URI points to the backend's `google_callback` endpoint: `GET http://localhost:8000/api/v1/auth/google/callback?code=...`.
    *   The `code` query parameter contains an authorization code provided by Google.
3.  **Backend (`auth.py`) Processes Google Callback:** The `google_callback()` endpoint in `backend/api/v1/auth.py` is invoked.
    *   **Exchange Code for Tokens:** The backend makes a server-to-server POST request to Google's token endpoint (`https://oauth2.googleapis.com/token`), exchanging the received `code` for Google-issued `access_token` and `id_token` (using `settings.GOOGLE_CLIENT_ID`, `settings.GOOGLE_CLIENT_SECRET`, and `settings.GOOGLE_REDIRECT_URI`).
    *   **Retrieve User Information:** Using the Google `access_token`, the backend makes another server-to-server GET request to Google's `userinfo` endpoint (`https://www.googleapis.com/oauth2/v2/userinfo`) to fetch the user's detailed profile (email, name, picture_url, google_id).
    *   **User Management (Database):**
        *   The backend checks if a `User` with the retrieved email exists in the local database.
        *   If the user is new, a new `User` record is created (`backend/models/user.py`), and a `role` is assigned (defaulting to `USER`, or `ADMIN` if the email is in `settings.ADMIN_EMAIL_LIST`).
        *   If the user exists, their details (e.g., `google_id`, `name`, `picture_url`, `last_login_at`) are updated.
    *   **JWT Generation:** Calls `create_access_token` to generate an internal JWT. This JWT contains essential claims like the user's email (`sub`) and `role`, signed with `settings.SECRET_KEY`.
    *   **Backend Sets HttpOnly Cookie:** The backend prepares an `HttpOnly` cookie named `"auth_token"` with the newly created JWT as its value.
        *   `httponly=True` prevents client-side JavaScript from accessing the cookie, enhancing security.
        *   `secure=True` is set only in production (`settings.ENVIRONMENT == "production"`) to ensure the cookie is only sent over HTTPS.
                *   `samesite="none"` (in production) / `"lax"` (in development): This is critical for cross-origin cookie behavior. `SameSite=None` is required when cookies are sent from a different site (domain) in a cross-site context (e.g., frontend on `app.com`, backend on `api.app.com`). `SameSite=None` requires the `Secure` attribute to be set (which `secure=is_production` handles). In development, `SameSite=Lax` is typically sufficient.
        *   `path="/"` makes the cookie available for all paths on the domain.
    *   **Backend Redirects to Frontend Callback:**
        *   The backend issues a `RedirectResponse` (HTTP 307) to `settings.FRONTEND_URL/auth/callback`.
        *   The user's browser is now redirected back to the frontend application.

### 4.4 Frontend Callback Handling & Session Establishment

1.  **Browser Redirects to Frontend `CallbackComponent`:**
    *   The browser, having received the `RedirectResponse` from the backend, navigates to `http://localhost:4200/auth/callback` (or the configured `FRONTEND_URL/auth/callback`).
    *   The `CallbackComponent` (`frontend/src/app/features/auth/callback/callback.component.ts`) is loaded.
2.  **`CallbackComponent` Delegates to `AuthService`:**
    *   In its `ngOnInit`, `CallbackComponent` calls `handleCallback()`.
    *   `handleCallback()` now simply calls `this.authService.handleCallback()` *without* any arguments.
3.  **`AuthService.handleCallback()` Execution:**
    *   `AuthService.handleCallback()` directly calls `loadUser()`.
4.  **`AuthService.loadUser()` Verifies Session:**
    *   `loadUser()` constructs an HTTP GET request to `/api/v1/auth/me`.
    *   **Credential Inclusion:** This request *only* includes `withCredentials: true` to send the `auth_token` HttpOnly cookie that the backend set during the OAuth callback. The previous development workaround of sending a `dev_access_token` from `localStorage` as an `Authorization` header is no longer active in the current `loadUser()` implementation.
    *   The backend's `/api/v1/auth/me` endpoint receives this request. `get_current_user` (backend dependency) will use the HttpOnly cookie to authenticate the user and retrieve their data.
5.  **`AuthService` Updates Frontend State & Navigates:**
    *   If the `/api/v1/auth/me` call is successful, the `AuthService` receives the `User` object.
    *   `this.userSignal.set(user)` is called, updating the frontend's authentication state to reflect the logged-in user.
    *   `authService.isAuthenticated()` now returns `true`.
    *   Finally, `AuthService` navigates the user to the `/home` route (`this.router.navigate(['/home'])`), completing the login process.
    *   If `loadUser()` fails (e.g., token invalid, backend issue), an error is set, and the user is redirected to the root (`/`).
    ### 4.5 User Session Verification (`/auth/me`)

This step describes how the application verifies an existing user session after initial login or when accessing protected resources. It primarily revolves around the `/api/v1/auth/me` endpoint.

1.  **Purpose:**
    *   To allow the frontend to retrieve the currently authenticated user's details.
    *   To act as a general mechanism for verifying session validity when the application loads or when a guarded route is accessed.
2.  **Frontend Initiates Request:**
    *   The `AuthService.loadUser()` method (called during application initialization, after OAuth callback, or potentially by other components) makes an HTTP GET request to `GET ${API_URL}/auth/me`.
    *   This request is sent with `withCredentials: true` (to automatically include the `auth_token` HttpOnly cookie). The previous development workaround of sending a `dev_access_token` from `localStorage` as an `Authorization` header is no longer active in the current `loadUser()` implementation.
3.  **Backend (`auth.py`) Handles `/me` Endpoint:**
    *   The `get_me` endpoint in `backend/api/v1/auth.py` is invoked.
    *   It uses the `current_user: User = Depends(get_current_user)` dependency.
4.  **`get_current_user` Dependency Execution:**
    *   The `get_current_user` function attempts to extract a JWT from either the `auth_token` cookie or the `Authorization` header of the incoming request.
    *   It then decodes and validates this JWT using `settings.SECRET_KEY` and `settings.ALGORITHM`.
    *   If the token is valid, it extracts the user's email from the token's payload.
    *   It queries the database to retrieve the corresponding `User` object.
    *   If the user is found and is active, the `User` object is returned, and the `get_me` endpoint can proceed.
    *   If the token is invalid, expired, or the user is not found/inactive, `get_current_user` raises an `HTTPException` (e.g., 401 Unauthorized), which prevents the `get_me` endpoint from executing its logic and returns an error response to the frontend.
5.  **Backend Returns User Data:** If `get_current_user` successfully authenticates the request, `get_me` returns a JSON object containing the `current_user`'s details (id, email, name, role, etc.).
6.  **Frontend Updates State:**
    *   `AuthService.loadUser()` receives the user data.
    *   `this.userSignal.set(user)` is updated, reflecting the authenticated user's details across the frontend.
    *   If the request to `/auth/me` fails (e.g., due to an invalid session/token), `AuthService` sets `userSignal` to `null` and handles the error accordingly (e.g., setting `errorSignal` or redirecting).

This entire process ensures that the frontend's perception of the user's authentication status is always synchronized with the backend's session validity.

### 4.6 Logout Flow

The logout process involves both the frontend and backend to invalidate the user's session and clear local authentication state.

1.  **Frontend Initiates Logout:**
    *   A user action (e.g., clicking a "Logout" button) triggers a call to `AuthService.logout()` in the frontend.
2.  **Frontend Requests Backend Logout:**
    *   `AuthService.logout()` makes an HTTP POST request to `${API_URL}/auth/logout`.
    *   This request includes `withCredentials: true` to ensure the `auth_token` HttpOnly cookie is sent, allowing the backend to identify and invalidate the correct session.
3.  **Backend (`auth.py`) Processes Logout Request:**
    *   The `logout()` endpoint in `backend/api/v1/auth.py` is invoked.
    *   **Cookie Deletion:** The backend creates a `Response` object and uses `response.delete_cookie(key="auth_token", path="/", httponly=True, samesite="lax")` to instruct the user's browser to remove the `auth_token` cookie. This effectively invalidates the session from the browser's perspective.
    *   **Return:** Returns a JSON response indicating successful logout.
4.  **Frontend Clears Local State:**
    *   Upon successful completion of the backend logout request (or even if it fails, to ensure local state consistency), `AuthService.logout()` locally clears the user's authentication data:
        *   `this.userSignal.set(null)`: Resets the user signal, marking the user as logged out.
        *   `this.errorSignal.set(null)`: Clears any authentication-related errors.
        *   The `dev_access_token` in `localStorage` would also typically be removed at this stage, though not explicitly shown in the `logout` method provided.

After this flow, the user is considered logged out, and any subsequent attempts to access protected routes will trigger the authentication process again.

---

## 5. Key Parameters and Variables

This section consolidates the critical parameters and variables that govern the authentication flow across both the frontend and backend.

### Frontend Parameters (`frontend/src/environments/environment.ts`)
*   **`environment.apiUrl`**:
    *   **Value:** `http://localhost:8000/api/v1` (in development)
    *   **Description:** The base URL for the backend API that the frontend communicates with. This is dynamically inserted into frontend service calls (e.g., in `AuthService`).

### Backend Configuration Parameters (`backend/core/config.py`)
*   **`settings.ENVIRONMENT`**:
    *   **Value:** `development` (or `production`)
    *   **Description:** Determines the application's operating environment, influencing behavior like development workarounds and cookie `secure` flags.
*   **`settings.ALLOWED_ORIGINS`**:
    *   **Value:** E.g., `['http://localhost:4200', 'http://localhost:3000']`
    *   **Description:** A list of frontend origins permitted to make cross-origin requests to the backend. Configured in `main.py`'s `CORSMiddleware`.
*   **`settings.SECRET_KEY`**:
    *   **Description:** Cryptographic key for signing and verifying JWTs. **Critical for security.**
*   **`settings.ALGORITHM`**:
    *   **Value:** `HS256`
    *   **Description:** The algorithm used for JWT signing.
*   **`settings.ACCESS_TOKEN_EXPIRE_MINUTES`**:
    *   **Value:** `30` (minutes)
    *   **Description:** The expiration time for generated JWTs.
*   **`settings.GOOGLE_CLIENT_ID`**:
    *   **Description:** Your application's client ID from Google Cloud Console.
*   **`settings.GOOGLE_CLIENT_SECRET`**:
    *   **Description:** Your application's client secret from Google Cloud Console. **Must be kept secret.**
*   **`settings.GOOGLE_REDIRECT_URI`**:
    *   **Value:** `http://localhost:8000/api/v1/auth/google/callback`
    *   **Description:** The URI Google redirects to after OAuth, pointing to the backend's callback endpoint. Must match Google Console settings exactly.
*   **`settings.FRONTEND_URL`**:
    *   **Value:** `http://localhost:4200`
    *   **Description:** The base URL of the frontend application. Used by the backend for redirects back to the frontend.
*   **`settings.ADMIN_EMAIL_LIST`**:
    *   **Description:** A list of email addresses that are granted admin privileges.

### Dynamic Backend Parameters (`backend/api/v1/auth.py`)
*   **`auth_token` (HttpOnly Cookie)**:
    *   **Description:** The name of the HttpOnly cookie set by the backend after successful OAuth. Contains the JWT for session management.
    *   **Parameters:** `httponly=True`, `secure` (conditional on `settings.ENVIRONMENT`), `samesite="none"` (in production) / `"lax"` (in development), `path="/"`, `max_age` (from `ACCESS_TOKEN_EXPIRE_MINUTES`).
*   **`code` (Google OAuth Parameter)**:
    *   **Description:** The authorization code received from Google during the OAuth callback. Exchanged for access tokens.
*   **`jwt_token` (Internal Variable)**:
    *   **Description:** The internally generated JWT string, created by `create_access_token` and placed into the `auth_token` cookie or URL hash fragment.

These parameters collectively define the security posture, external integrations, and operational behavior of the application's authentication system.

---

## 6. Known Issues/Considerations

This section outlines known challenges or important considerations related to the current authentication implementation.

### 6.1 Cross-Origin Cookie Issues in Local Development

*   **Problem:** When the frontend (e.g., `http://localhost:4200`) and backend (e.g., `http://localhost:8000`) run on different ports on `localhost`, browsers often apply strict SameSite cookie policies. Even with `samesite="lax"`, `HttpOnly` cookies set by the backend (`localhost:8000`) may not always be sent by the browser to subsequent XHR/fetch requests originating from the frontend (`localhost:4200`) back to the backend. This can lead to the frontend failing to establish an authenticated session.
*   **Current State:** The previously implemented development workaround (passing JWT via URL hash fragment and storing in `localStorage`) has been removed from both frontend and backend. The application now *solely relies* on `HttpOnly` cookies for session management across all environments, including local development.
*   **Consideration:** If users encounter persistent login issues in local development due to browsers blocking cross-origin `HttpOnly` cookies, they may need to configure their browser settings to allow third-party cookies for `localhost` or explore local proxy solutions to ensure both frontend and backend appear to be on the same origin.

### 6.2 JWT Expiration and Refresh

*   **Consideration:** The current implementation uses `ACCESS_TOKEN_EXPIRE_MINUTES` to define the JWT's lifespan. Once this token expires, the user will become unauthenticated.
*   **Current State:** There is no explicit JWT refresh mechanism implemented. Users will need to re-authenticate via the Google OAuth flow once their token expires.
*   **Future Improvement:** For a better user experience, a silent token refresh mechanism (e.g., using a refresh token, or periodically re-authenticating with Google if allowed) could be implemented.

### 6.3 CORS Configuration

*   **Consideration:** The `CORS_ALLOWED_ORIGINS` setting in `backend/core/config.py` is critical. If not correctly configured, especially in production, the frontend will be unable to communicate with the backend, and the authentication flow will fail.
*   **Best Practice:** In production, `CORS_ALLOWED_ORIGINS` should be explicitly set to the exact domain(s) of the deployed frontend application, rather than relying on broad defaults or wildcard (`*`) settings.

This documentation concludes the analysis of the authentication flow.