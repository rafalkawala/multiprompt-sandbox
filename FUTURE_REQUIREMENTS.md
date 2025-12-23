# Future Requirements Analysis

This document outlines potential future requirements for the MLLM Benchmarking Platform, focusing on statistical rigor, advanced data management, and enterprise-grade features.

## 1. Statistical Sampling & Confidence Estimation

**Requirement:** Calculate the estimated statistically correct sample size for annotations to achieve a specific labeling accuracy with a defined confidence level.

**Rationale:** Annotating 100% of a large dataset is often cost-prohibitive. Users need to know the minimum number of images they need to label to be "X% confident that the model's accuracy is within Y% of the true value."

**Implementation Details:**
*   **Scientific Basis:**
    *   **Cochran's Formula (Simple Proportion):**
        *   $n = \frac{Z^2 \cdot p \cdot (1-p)}{e^2}$
        *   Where $Z$ is the Z-score (e.g., 1.96 for 95% CI), $p$ is the estimated proportion (use 0.5 for conservative estimate), and $e$ is the margin of error.
    *   **Finite Population Correction:**
        *   $n_{adjusted} = \frac{n}{1 + \frac{n-1}{N}}$ (where $N$ is the total dataset size).
    *   **Advanced Metrics (Accuracy, Sensitivity, Specificity):**
        *   Use **Wald Interval** for large samples or **Agresti-Coull Interval** for smaller samples or proportions close to 0/1.
        *   **F1-Score Confidence:** Requires an iterative approach or bootstrapping since it's a harmonic mean of two proportions (Precision/Recall). See *Whittle et al. (2025)* for closed-form solutions.
*   **UI Features:**
    *   **"Labeling Planner" Calculator:** User inputs desired Confidence Level (90%, 95%, 99%) and Margin of Error (e.g., 3%, 5%). System outputs required sample count.
    *   **"Accuracy Confidence Interval" in Results:** Display accuracy as "92.5% ± 3.1% (95% CI)".

## 2. Active Learning for Annotation

**Requirement:** Intelligent selection of the "most informative" images for human labeling.

**Rationale:** Random sampling is unbiased but inefficient. Active learning prioritizes images where the model is confused, maximizing accuracy gains per labeled image.

**Implementation Details:**
*   **Uncertainty Sampling:** Select images where the model's confidence scores (for top classes) are low or close together (high entropy).
*   **Disagreement Sampling:** If multiple models (e.g., Gemini Pro vs. Claude) give different predictions, prioritize these for human review.
*   **Diversity Sampling:** Use image embeddings (clustering) to ensure the labeled set covers all visual clusters (e.g., different lighting, angles, product types).

## 3. Data Drift & Distribution Shift Detection

**Requirement:** Detect when new production images differ significantly from the reference/training dataset.

**Rationale:** Retail environments change (new packaging, seasonal displays). If the input distribution shifts, accuracy estimates become invalid.

**Implementation Details:**
*   **Embedding Analysis:** Calculate centroid and variance of reference dataset embeddings. Flag new batches that deviate statistically (e.g., using Maximum Mean Discrepancy or Wasserstein distance).
*   **Out-of-Distribution (OOD) Detection:** Flag "anomaly" images that don't look like anything in the verified dataset.

## 4. Adversarial Robustness & Safety Testing

**Requirement:** Automatically test models against adversarial inputs and visual jailbreaks.

**Rationale:** Vision LLMs are vulnerable to "visual prompt injection" where text embedded in an image (e.g., "Ignore previous instructions") overrides system prompts.

**Implementation Details:**
*   **Visual Jailbreak Suite:** Integrate datasets like *HarmBench* or *JailbreakBench* to test if models can be tricked into generating harmful content via image inputs.
*   **Robustness Metrics:** Track Attack Success Rate (ASR) against standard attacks (e.g., GCG, PGD in embedding space).
*   **Input Sanitization:** Implement "Robust Tokenization Filters" (as proposed in *AdversariaLLM*) to detect and block unreachable token sequences often used in adversarial attacks.

## 5. Synthetic Data Generation

**Requirement:** Augment datasets with synthetic "hard negatives" and edge cases.

**Rationale:** Real-world data collection is slow. Generative models can create rare scenarios (e.g., "shattered glass on shelf") to stress-test vision models.

**Implementation Details:**
*   **Diffusion + LLM Pipeline:** Use an LLM (e.g., Gemini) to generate detailed prompts for a diffusion model (e.g., Imagen/Stable Diffusion) to create synthetic images of specific defects or product arrangements.
*   **Style Transfer:** modifying existing ground truth images to simulate different lighting/weather conditions (domain randomization).

## 6. Continuous Evaluation (CI/CD for MLLMs)

**Requirement:** Integrate evaluation into the software delivery lifecycle.

**Rationale:** Prompt engineering is code. Changes to prompts or model versions should trigger automated regression tests.

**Implementation Details:**
*   **GitHub Actions / GitLab CI Integration:** A CLI tool or webhook that triggers an "Experiment Run" on a "Golden Dataset" whenever a Pull Request modifies a prompt file.
*   **Quality Gates:** Block deployment if accuracy drops below a defined threshold (e.g., 95%) or if latency exceeds limits.
*   **Regression Reports:** "This PR improved accuracy on 'Soda Cans' by 2% but degraded 'Cereal Boxes' by 5%."

## 7. Cost Estimation & Budgeting

**Requirement:** Advanced forecasting of experiment costs.

**Rationale:** Running thousands of images through GPT-4o or Gemini 1.5 Pro is expensive. Users need to budget before execution.

**Implementation Details:**
*   **Token Estimation:** Pre-calculate image tokens (based on resolution) and prompt tokens.
*   **Budget Alerts:** "This experiment will cost approximately $50.00. Proceed?"
*   **Rate Limit Optimization:** Smart throttling to maximize throughput without hitting provider quotas (429 errors).

## 8. Explainability (XAI) for Vision

**Requirement:** Visualize *why* a model made a specific prediction.

**Rationale:** "Black box" decisions are hard to trust in enterprise settings.

**Implementation Details:**
*   **Attention Maps:** Visualize which parts of the image the model attended to when generating the token (e.g., overlaying a heatmap on the product when predicting "Out of Stock").
*   **Saliency Maps:** Gradient-based visualization of pixel importance.

## 9. Inter-Annotator Agreement & Quality Control

**Requirement:** Support multiple annotators per image and measure agreement.

**Rationale:** Human labelers make mistakes. For "Gold Standard" benchmarks, consensus is needed.

**Implementation Details:**
*   **Cohen's Kappa / Fleiss' Kappa:** Calculate agreement metrics between annotators.
*   **Consensus Workflow:** If annotators disagree, route to a "Super Admin" for final decision.
*   **Annotator "Honeypots":** Randomly inject known ground-truth images to test annotator accuracy.

## 10. Collaboration & Role Management

**Requirement:** Granular permissions and team workspaces.

**Rationale:** Enterprise teams have distinct roles (Labeler, Data Scientist, Manager).

**Implementation Details:**
*   **Workspace Isolation:** Separate datasets/experiments by team/department.
*   **Audit Logs:** Track who changed a label or prompt and when.
