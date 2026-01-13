# Wizard Flow Documentation

## Overview
The Wizard is an overlay-based guided experience designed to help users start with the platform based on their business needs.

## Flows & Content

### 1. Validate Model Feasibility (Small Data)
*   **Target Audience**: Users with a small dataset and a specific question.
*   **Description**: "I have a dataset and a specific question. I want to check if AI models can answer it accurately before I invest more time."
*   **Steps**: Upload -> Label -> Benchmark.
*   **Key Action**: "Start Validation"

### 2. Analyze Large Dataset (Sampling)
*   **Target Audience**: Users with massive image collections.
*   **Description**: "I have a massive collection of images. I want to sample a subset to estimate cost and performance for the whole batch."
*   **Steps**: Upload -> **Sample** -> Label -> Eval.
*   **Special Step**: Includes a "Sample Data" step (Random/Manual selection) not present in other flows.
*   **Key Action**: "Start Analysis"

### 3. Develop & Optimize Prompt (Golden Set)
*   **Target Audience**: Users refining prompt engineering.
*   **Description**: "I want to craft the perfect prompt for an automated workflow. Iterate on a 'Golden Set' of difficult images."
*   **Steps**: Upload -> Label (Golden Set) -> **Iterate**.
*   **Key Action**: "Start Developing"

## User Experience & Re-use
The wizard leverages existing platform capabilities while providing a streamlined interface:
*   **Project Creation**: Uses a simplified inline form that calls the central `ProjectsService`.
*   **Data Upload**: Uses a simplified inline drag-and-drop zone calling `ProjectsService`.
*   **Labeling**: The wizard **does not** rebuild the labeling tool. Instead, it opens the existing Labeling Interface (at `/projects/:id/datasets/:id/annotate`) in a new window/tab, ensuring users get the full feature set.
*   **Evaluation**: The final step navigates users to the existing Evaluation or Project Dashboard, passing context to pre-fill or start the appropriate task.

## Entry Points
*   **Auto-Start**: Opens automatically on login if `wizard_do_not_show` is not set in `localStorage`.
*   **Toolbar Trigger**: Wand icon (`auto_fix_high`) in the top navigation bar.
*   **Dashboard**: "Start Wizard" button on the Home page.

## Technical Verification
A Playwright script is available to verify the UI flows in isolation (mocking backend responses).

**Location**: `backend/tests/e2e/test_wizard_flow.py`

**Running the test**:
1.  Ensure the Frontend is running (`ng serve`).
2.  Run the script:
    ```bash
    python backend/tests/e2e/test_wizard_flow.py
    ```

**What it verifies**:
*   Auto-start logic (dialog appears on reload).
*   Presence of all three business flow options.
*   Navigation from Selection to Step 1 (Project Creation).
