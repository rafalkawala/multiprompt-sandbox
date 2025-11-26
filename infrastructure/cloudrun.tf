# Cloud Run services will be deployed by Cloud Build with actual container images
# This file only contains IAM configuration for the services

# Get project number for default service account
data "google_project" "project" {
  project_id = var.gcp_project_id
}

# Data sources for existing secrets (created outside Terraform)
data "google_secret_manager_secret" "secret_key" {
  project   = var.gcp_project_id
  secret_id = "multiprompt-secret-key"
}

data "google_secret_manager_secret" "google_client_id" {
  project   = var.gcp_project_id
  secret_id = "google-client-id"
}

data "google_secret_manager_secret" "google_client_secret" {
  project   = var.gcp_project_id
  secret_id = "google-client-secret"
}

data "google_secret_manager_secret" "gemini_api_key" {
  project   = var.gcp_project_id
  secret_id = "multiprompt-gemini-api-key"
}

data "google_secret_manager_secret" "admin_emails" {
  project   = var.gcp_project_id
  secret_id = "multiprompt-admin-emails"
}

# Allow the backend service account to access secrets
resource "google_secret_manager_secret_iam_member" "backend_secret_accessor" {
  project   = google_secret_manager_secret.db_password_secret.project
  secret_id = google_secret_manager_secret.db_password_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_secret_key_accessor" {
  project   = data.google_secret_manager_secret.secret_key.project
  secret_id = data.google_secret_manager_secret.secret_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_google_client_id_accessor" {
  project   = data.google_secret_manager_secret.google_client_id.project
  secret_id = data.google_secret_manager_secret.google_client_id.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_google_client_secret_accessor" {
  project   = data.google_secret_manager_secret.google_client_secret.project
  secret_id = data.google_secret_manager_secret.google_client_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_gemini_api_key_accessor" {
  project   = data.google_secret_manager_secret.gemini_api_key.project
  secret_id = data.google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend_sa.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_admin_emails_accessor" {
  project   = data.google_secret_manager_secret.admin_emails.project
  secret_id = data.google_secret_manager_secret.admin_emails.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend_sa.email}"
}
