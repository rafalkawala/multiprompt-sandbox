output "project_id" {
  description = "The ID of the created GCP project."
  value       = google_project.project.project_id
}

output "project_number" {
  description = "The number of the created GCP project."
  value       = google_project.project.number
}

output "uploads_bucket_name" {
  description = "The name of the GCS bucket for uploads."
  value       = google_storage_bucket.uploads.name
}

output "uploads_bucket_url" {
  description = "The URL of the GCS bucket for uploads."
  value       = google_storage_bucket.uploads.url
}
