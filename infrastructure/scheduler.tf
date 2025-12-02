# Cloud Scheduler for automated labelling jobs
# Triggers check-scheduled-jobs endpoint every 15 minutes

# Enable Cloud Scheduler API
resource "google_project_service" "cloudscheduler" {
  service = "cloudscheduler.googleapis.com"

  disable_on_destroy = false
}

# Cloud Scheduler job to trigger labelling jobs check
resource "google_cloud_scheduler_job" "labelling_jobs_trigger" {
  name        = "labelling-jobs-trigger"
  description = "Triggers check for scheduled labelling jobs every 15 minutes"
  schedule    = "*/15 * * * *"  # Every 15 minutes
  time_zone   = "UTC"
  region      = var.region

  http_target {
    uri         = "${var.backend_url}/api/v1/internal/tasks/check-scheduled-jobs"
    http_method = "POST"

    oidc_token {
      service_account_email = google_service_account.backend_sa.email
      audience              = var.backend_url
    }
  }

  depends_on = [
    google_project_service.cloudscheduler,
    google_cloud_run_service.backend
  ]
}
