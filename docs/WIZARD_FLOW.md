# Wizard Flow Documentation

## Overview
The Wizard is an overlay-based guided experience designed to help users start with the platform based on their business needs.

## Flows
1. **Validate Model Feasibility**: For users with a small dataset who want to check if AI models can answer their specific question.
2. **Analyze Large Dataset**: For users with massive datasets who need to sample data before labeling and evaluating.
3. **Develop & Optimize Prompt**: For users focusing on prompt engineering using a "Golden Set".

## Entry Points
*   **Auto-Start**: The wizard opens automatically when a user logs in, unless they have opted out ("Do not show this on startup").
*   **Top-Left Trigger**: A "Start Wizard" button (wand icon) is available in the top application toolbar.
*   **Dashboard**: A "Start Wizard" button is available on the Home dashboard.

## Technical Implementation
*   **Component**: `WizardDialogComponent` (wrapping `WizardSelectionComponent` and `WizardShellComponent`).
*   **State**: `WizardService` manages the flow state and data.
*   **Dialog**: Uses `MatDialog` for the overlay experience.
*   **Persistence**: Uses `localStorage` key `wizard_do_not_show` to persist the user's preference to hide the auto-start wizard.

## Verification
To verify the flow:
1.  **Auto-Start**: clear `localStorage` and reload. The wizard should appear.
2.  **Opt-Out**: Check "Do not show..." and close. Reload. The wizard should NOT appear.
3.  **Manual Trigger**: Click the wand icon in the header. The wizard should appear.
4.  **Flows**: Click through the flows to ensure steps are rendered correctly within the dialog.
