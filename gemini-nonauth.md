# Handling Non-Authorized Google Users

This document outlines the current behavior when a Google-authenticated user logs in and does not exist in the system, and proposes changes to implement a new flow where such users are registered with a non-authorized role and prohibited from accessing the application until explicitly approved.

## 1. Current Behavior Analysis (Google OAuth New User)

Based on the analysis of `backend/api/v1/auth.py`, `backend/models/user.py`, and `backend/core/config.py`, here's what currently happens when a new user authenticates via Google:

1.  **Google Authentication**: The user successfully authenticates through Google OAuth.
2.  **User Lookup**: The system attempts to find an existing user in the database using their email address.
3.  **New User Creation**: If the user's email is *not* found in the database:
    *   Their role is determined by checking if their email is present in the `settings.ADMIN_EMAIL_LIST` from `backend/core/config.py`.
    *   If their email is in `ADMIN_EMAIL_LIST`, they are assigned the `ADMIN` role.
    *   Otherwise, they are assigned the `USER` role.
    *   The `is_active` flag for the new user is set to `True` by default.
    *   The new user record, with the assigned role and `is_active=True`, is saved to the PostgreSQL database.
4.  **JWT Issuance & Redirect**: A JSON Web Token (JWT) is generated for the newly created user (or existing user), containing their email and role. This token is set as an `HttpOnly` cookie, and the user is redirected to the frontend application.
5.  **Immediate Access**: Because the new user is created with `is_active=True` and either an `ADMIN` or `USER` role, they can immediately access protected application endpoints and functionality corresponding to their assigned role. There is no intermediate "pending" or "unauthorized" state.

## 2. Proposed New Flow for Non-Authorized Users

The goal is to modify the system so that new Google-authenticated users who do not exist in the system are registered, but are initially prevented from accessing the application until an administrator explicitly authorizes them.

**Proposed Flow:**

1.  User authenticates via Google OAuth.
2.  System checks if user's email exists in the database.
3.  If user *does not* exist:
    *   User is created in the database.
    *   Their `role` is automatically set to a new `UNAUTHORIZED` role.
    *   Their `is_active` status is set to `False`.
    *   A JWT is issued, and the user is redirected to the frontend (which can then display a "pending authorization" message).
4.  When the user attempts to access any protected API endpoint, the system will check their `role`. If it is `UNAUTHORIZED`, access will be denied with a `403 Forbidden` error.
5.  An administrator would then use the existing `/api/v1/users/{user_id}` PATCH endpoint to manually update the user's `role` and/or `is_active` status to grant access.

## 3. Enumeration of Files and Proposed Changes

To implement this new flow, the following files would need modifications:

### 3.1. `backend/models/user.py`

*   **Proposed Change**: Add a new member `UNAUTHORIZED` to the `UserRole` enum.
*   **Reason**: To represent the state of a user who has authenticated but is not yet permitted to access application features.

```python
# OLD:
# class UserRole(str, enum.Enum):
#     ADMIN = "admin"
#     USER = "user"
#     VIEWER = "viewer"

# NEW:
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    UNAUTHORIZED = "unauthorized" # <-- NEW role
```

### 3.2. `backend/api/v1/auth.py`

*   **Proposed Change 1**: Modify the user creation logic within the `google_callback` function. When a new user is detected (`if not user:`), their `role` should be set to `UserRole.UNAUTHORIZED.value` and `is_active` to `False`.
*   **Reason**: To ensure that new Google-authenticated users are initially registered in a non-authorized, inactive state.

```python
# OLD (snippet within google_callback, inside 'if not user:' block):
#             role = UserRole.ADMIN.value if email.lower() in settings.ADMIN_EMAIL_LIST else UserRole.USER.value
#             # Create new user
#             user = User(
#                 email=email,
#                 google_id=google_id,
#                 name=name,
#                 picture_url=picture,
#                 role=role,
#                 is_active=True # Always True for new users
#             )

# NEW (snippet within google_callback, inside 'if not user:' block):
            # For new users, assign 'UNAUTHORIZED' role and set is_active to False
            user = User(
                email=email,
                google_id=google_id,
                name=name,
                picture_url=picture,
                role=UserRole.UNAUTHORIZED.value, # <-- NEW: default to unauthorized
                is_active=False # <-- NEW: default to inactive
            )
```

*   **Proposed Change 2 (Corrected)**: Ensure the `get_current_user` dependency denies access to users where `is_active` is `False`. This implicitly handles `UNAUTHORIZED` users if they are created with `is_active=False`.
*   **Reason**: To enforce the access restriction for users with `is_active=False`, which now includes newly registered `UNAUTHORIZED` users, leveraging existing logic.

```python
# NEW (snippet within get_current_user - SIMPLIFIED):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    # The existing check for is_active is sufficient if UNAUTHORIZED users are created with is_active=False.
    # An UNAUTHORIZED user is considered an INACTIVE user for application access purposes.
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, # Changed status code to 403 as it's a permission issue
            detail="Account is inactive or pending authorization. Please contact an administrator."
        )
    # No need for an explicit 'if user.role == UserRole.UNAUTHORIZED.value:' check here,
    # as setting is_active=False for unauthorized users correctly handles access denial.
    return user
```

### 3.3. `backend/alembic/versions/` (New Migration File)

*   **Proposed Change**: A new Alembic migration script will be required to update the `userrole` enum in the PostgreSQL database to include the new `unauthorized` value.
*   **Reason**: Database schema must be updated to reflect the new `UserRole` enum definition in `backend/models/user.py`.

```python
# Example of the core change within an Alembic upgrade function:
# from alembic import op
# import sqlalchemy as sa
#
# def upgrade() -> None:
#     # Assuming 'userrole' is the name of the enum type in your PostgreSQL DB
#     op.execute("ALTER TYPE userrole ADD VALUE 'unauthorized'")
#
# def downgrade() -> None:
#     # This might be tricky for enum values that are already in use.
#     # A common strategy for downgrade is to recreate the enum without the new value,
#     # but this requires careful handling of columns that might use it.
#     # For simplicity in this plan, we'll omit a direct downgrade for enum removal,
#     # as it often requires more complex data migration.
#     pass
```

### 3.4. Frontend Considerations (No Code Changes in this scope)

*   The frontend application (`frontend/`) would need to be updated to gracefully handle the `403 Forbidden` response when an `UNAUTHORIZED` user attempts to access protected routes.
*   It should display a user-friendly message indicating that their account is pending authorization and to contact an administrator.
*   The `RedirectResponse` in `auth.py` to `settings.FRONTEND_URL/auth/callback` remains the same, but the frontend's callback handling would need to be aware of the user's `is_active` status or `role` to show the appropriate message.

---

## 4. Proposed GitHub Epics and Issues

To track the implementation of the "Non-Authorized User Flow" on GitHub, the following epic and associated issues are proposed, following the conventions found in `docs/issues-summary.md`. This feature is closely related to existing **Epic 4: User Authentication and Authorization**.

### New Epic: Implement User Account Provisioning & Authorization Workflow
**Labels**: `epic`, `backend`, `frontend`, `security`, `priority:high`

**Description**:
Enhance the user authentication process to introduce a provisioning workflow for new Google-authenticated users. Users will initially be registered in an `UNAUTHORIZED` and `inactive` state, preventing access to application features until an administrator explicitly grants them an active role.

**Parent Epic**: Epic 4: User Authentication and Authorization

**Tasks**:

-   **Issue**: Define `UNAUTHORIZED` Role in User Model
    *   **Labels**: `backend`, `enhancement`, `priority:high`
    *   **Description**: Add `UNAUTHORIZED` as a new value to the `UserRole` enum in `backend/models/user.py`.
    *   **Acceptance Criteria**: The `UserRole` enum includes `UNAUTHORIZED`.
-   **Issue**: Create Alembic Migration for `UNAUTHORIZED` Role
    *   **Labels**: `backend`, `database`, `enhancement`, `priority:high`
    *   **Description**: Generate and implement an Alembic migration to add the `unauthorized` value to the `userrole` enum type in the PostgreSQL database.
    *   **Acceptance Criteria**: Database schema is updated to support the new `UNAUTHORIZED` role.
-   **Issue**: Modify Google Callback for New User Provisioning
    *   **Labels**: `backend`, `authentication`, `enhancement`, `priority:high`
    *   **Description**: Update `google_callback` in `backend/api/v1/auth.py` to set `role=UserRole.UNAUTHORIZED.value` and `is_active=False` for newly registered Google users.
    *   **Acceptance Criteria**: New Google users are stored with `UNAUTHORIZED` role and `is_active=False`.
-   **Issue**: Enforce Authorization for Inactive/Unauthorized Users
    *   **Labels**: `backend`, `security`, `authentication`, `priority:high`
    *   **Description**: Ensure that `get_current_user` in `backend/api/v1/auth.py` correctly denies access to protected endpoints for users with `is_active=False` (which now includes `UNAUTHORIZED` users), returning a `403 Forbidden` status with an informative message.
    *   **Acceptance Criteria**: Inactive/Unauthorized users cannot access protected endpoints and receive a `403 Forbidden` response.
-   **Issue**: Frontend Handling for Unauthorized Users
    *   **Labels**: `frontend`, `UX`, `enhancement`, `priority:high`
    *   **Description**: Implement frontend logic to gracefully handle `403 Forbidden` responses for unauthorized users. Display a clear message instructing them to contact an administrator for account activation.
    *   **Acceptance Criteria**: Frontend provides a clear user experience for unauthorized users without crashing.
-   **Issue**: Admin UI for User Authorization
    *   **Labels**: `frontend`, `backend`, `admin-panel`, `enhancement`, `priority:medium`
    *   **Description**: Enhance the existing user management functionality (via `backend/api/v1/users.py` PATCH endpoint) to allow administrators to easily view, activate, and assign roles to pending/unauthorized users. This might include adding a filter for `UNAUTHORIZED` users in the admin user list.
    *   **Acceptance Criteria**: Administrators can view and manage `UNAUTHORIZED` users' roles and activation status.

**Success Criteria (for Epic)**:
-   New Google-authenticated users who do not exist in the system are automatically registered as `UNAUTHORIZED` and `inactive`.
-   `UNAUTHORIZED` users are prevented from accessing protected application features.
-   Administrators can activate and assign appropriate roles to `UNAUTHORIZED` users through the admin interface.
-   Frontend provides clear feedback to users regarding their authorization status.

**Timeline**: 1-2 weeks