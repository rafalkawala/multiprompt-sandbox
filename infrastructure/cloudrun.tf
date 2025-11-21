# Cloud Run services will be deployed by Cloud Build with actual container images
# This file only contains IAM configuration for the services

# Get project number for default service account
data "google_project" "project" {
  project_id = var.gcp_project_id
}

# Allow the default compute service account to access secrets
# Cloud Run services use this by default
resource "google_secret_manager_secret_iam_member" "backend_secret_accessor" {
  project   = google_secret_manager_secret.db_password_secret.project
  secret_id = google_secret_manager_secret.db_password_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}
