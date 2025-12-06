# Responsive Web Design (RWD) Fix Report
**Date:** December 6, 2025
**Objective:** Identify minimum changes to enable proper RWD, specifically focusing on the reported mobile issues.

## 1. Summary of Analysis
The application's core responsive architecture (in `styles.scss` and `app.component.scss`) is actually sound, utilizing a standard `_breakpoints.scss` file with valid mixins.

The primary issue causing the "RWD not kicking in" on mobile (specifically for the login page) is a **CSS Box Model conflict** in the Login component.
*   **The Bug:** The login card has `width: 100%` AND `margin: 16px`. In CSS, `width: 100%` means "100% of the parent". Adding a 16px margin *outside* of that 100% width forces the element to be `100% + 32px` wide, causing it to overflow the viewport on small mobile screens (causing horizontal scroll or cutoff).

## 2. Minimum Required Changes

### A. Login Component Fix (Critical)
**File:** `frontend/src/app/features/auth/login/login.component.ts`

**Issue:**
```scss
.login-card {
  width: 100%;
  max-width: 400px;
  margin: 16px; // <--- This causes overflow on small screens
  // ...
}
```

**Required Change:**
Remove the margin from the card and instead add padding to the container to handle the spacing safely.

**New CSS (Logic):**
```scss
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f5f5;
  padding: 16px; // <--- ADD THIS: Handles safe spacing from edges
}

.login-card {
  width: 100%;
  max-width: 400px;
  // margin: 16px; <--- REMOVE THIS
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  border-radius: 8px;
}
```

### B. Global Breakpoint Standardization (Optional but Recommended)
**File:** `frontend/src/styles.scss` (and potentially others)

The investigation showed that while `_breakpoints.scss` exists, it might not be consistently imported. However, for the *minimum* fix to get mobile working, fixing the Login component overflow is the single impactful action. The global layout (`app.component.scss`) already appears to handle mobile padding correctly (`padding: 16px` vs `24px`).

## 3. Execution Plan
To fix the mobile view immediately:
1.  **Modify `frontend/src/app/features/auth/login/login.component.ts`**: Update the inline styles to move spacing from the child (`.login-card`) margin to the parent (`.login-container`) padding.

No other changes are strictly necessary to resolve the reported "mobile view not kicking in" for the login flow.
