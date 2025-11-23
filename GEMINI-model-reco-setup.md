# Recommended Gemini Model Setup for Local Development and Cloud Deployment

This document outlines the recommended configuration for using Gemini models, distinguishing between local development and cloud deployment environments to ensure secure and flexible authentication.

**Goal:**
-   **Local Development:** Utilize a Google API Key for quick and easy authentication.
-   **Cloud Deployment:** Leverage Google Cloud's Service Principal mechanism, avoiding direct API key management for enhanced security and operational simplicity.

---

## 1. Local Development with API Key

For local development, using a Google API Key is often the most straightforward method for authenticating with Gemini models.

### Steps:

1.  **Obtain a Google API Key:**
    *   Navigate to [Google AI Studio](https://aistudio.google.com/app/apikey) or the Google Cloud Console.
    *   Create or select an existing API Key.
    *   Ensure the API Key has the necessary permissions to access the Gemini API (e.g., `Vertex AI User` role).

2.  **Set as Environment Variable:**
    *   Store your API key securely in an environment variable named `GOOGLE_API_KEY`. This is a common practice to avoid hardcoding sensitive information.
    *   Example (Linux/macOS):
        ```bash
        export GOOGLE_API_KEY="YOUR_API_KEY_HERE"
        ```
    *   Example (Windows PowerShell):
        ```powershell
        $env:GOOGLE_API_KEY="YOUR_API_KEY_HERE"
        ```

3.  **Initialize Gemini Model:**
    *   Your application's Gemini client or wrapper (like the `GeminiModel` class found in the codebase) should automatically pick up the `GOOGLE_API_KEY` from the environment.
    *   If you're using the official Google Generative AI Python SDK, it typically auto-detects the API key from the `GOOGLE_API_KEY` environment variable.

    *Relevant Snippet Example:*
    The `_prompt_for_google_api_key` function suggests the use of the `GOOGLE_API_KEY` environment variable:
    ```python
    def _prompt_for_google_api_key(
        google_api_key: Optional[str],
    ) -> str:
      """Prompts user for Google API key."""
      google_api_key = google_api_key or os.environ.get("GOOGLE_API_KEY", None)

      google_api_key = _prompt_str(
          "Enter Google API key",
          prior_msg=_GOOGLE_API_MSG,
          default_value=google_api_key,
      )
      return google_api_key
    ```
    And your custom `GeminiModel` class likely leverages this implicit authentication:
    ```python
    class GeminiModel:
        # ...
        def __init__(
            self,
            model_name: str = "gemini-2.0-flash-001",
            # ...
        ):
            # ... model initialization will implicitly use GOOGLE_API_KEY if set
            self.model = GenerativeModel(model_name=model_name)
    ```

---

## 2. Cloud Deployment with Service Principal

For cloud environments (e.g., Google Cloud Run, Google Kubernetes Engine, Vertex AI Endpoints), it is highly recommended to use a Google Cloud Service Account (Service Principal) for authentication. This eliminates the need to manage API keys directly within your deployed application, enhancing security and leveraging cloud-native IAM capabilities.

### Steps:

1.  **Create a Google Cloud Service Account:**
    *   In the Google Cloud Console, navigate to `IAM & Admin` > `Service Accounts`.
    *   Create a new service account dedicated to your application.
    *   Download the JSON key file **only if** you are deploying to a non-Google Cloud environment or need explicit key file authentication (which is generally discouraged for Google Cloud-native deployments).

2.  **Grant Necessary IAM Roles:**
    *   Assign the service account appropriate IAM roles. For Gemini model access, the `Vertex AI User` role (or more granular roles like `Vertex AI Generative AI User`) is typically required.
    *   Additional roles might be needed depending on other Google Cloud services your application interacts with.

3.  **Attach Service Account to Compute Resource:**
    *   **Google Cloud Run:** When deploying a service to Cloud Run, specify the created service account in the service configuration. Cloud Run services automatically run with the permissions of the attached service account.
    *   **Google Kubernetes Engine (GKE):** For GKE workloads, you can associate a Kubernetes Service Account with a Google Cloud Service Account using Workload Identity. Pods running with the configured Kubernetes Service Account will then automatically authenticate as the linked Google Cloud Service Account.
    *   **Other Google Cloud Services (e.g., Compute Engine, Cloud Functions):** Similar mechanisms exist to associate a service account with your compute instance or function.

    *Relevant Snippet Examples:*
    The `service_account_scheme_credential` and `to_cloud_run` functions in your codebase indicate integration with Google Cloud services and service account usage:

    ```python
    def service_account_scheme_credential(
        config: ServiceAccount,
    ) -> Tuple[AuthScheme, AuthCredential]:
      """Creates AuthScheme and AuthCredential for Google Service Account.
      Returns a bearer token scheme, and a service account credential.
      """
      auth_scheme = HTTPBearer(bearerFormat="JWT")
      auth_credential = AuthCredential(
          auth_type=AuthCredentialTypes.SERVICE_ACCOUNT, service_account=config
      )
      return auth_scheme, auth_credential
    ```

    The `to_cloud_run` function specifically handles deployments to Cloud Run, where a service account would be implicitly used by the deployed container:

    ```python
    def to_cloud_run(
        *,
        agent_folder: str,
        project: Optional[str],
        region: Optional[str],
        service_name: str,
        # ... other parameters
    ):
      # ... deployment logic ...
      subprocess.run(
          [
              'gcloud',
              'run',
              'deploy',
              service_name,
              '--source',
              temp_folder,
              '--project',
              project,
              # ... other gcloud run deploy arguments
          ],
          check=True,
      )
    ```
    When `gcloud run deploy` is executed, you would typically specify the service account via `--service-account=SERVICE_ACCOUNT_EMAIL`.

### Benefits:
-   **Enhanced Security:** No sensitive API keys are embedded in your application code or configuration files, reducing the risk of accidental exposure.
-   **Simplified Key Management:** Google Cloud handles credential rotation and management for service accounts.
-   **Fine-grained Access Control:** IAM roles allow precise control over what services and resources your application can access.

By following these recommendations, you can establish a robust and secure authentication strategy for your Gemini model integrations across different deployment environments.