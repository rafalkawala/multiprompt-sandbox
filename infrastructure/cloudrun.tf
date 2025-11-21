# --- Cloud Run Services ---

# Backend Service
resource "google_cloud_run_v2_service" "backend_service" {
  project  = google_project.project.project_id
  name     = var.backend_service_name
  location = var.gcp_region

  template {
    containers {
      image = "placeholder-image-backend" # This will be replaced by our CI/CD pipeline
      ports {
        container_port = 8000
      }
      
      # Pass database credentials securely as environment variables
      # The values are sourced from Secret Manager
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password_secret.secret_id
            version = "latest"
          }
        }
      }
    }

    # Connect the service to our private network
    vpc_access {
      connector = google_vpc_access_connector.vpc_connector.id
      egress    = "ALL_TRAFFIC"
    }
  }

  # Allow traffic only from internal sources and specific load balancers
  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  depends_on = [google_vpc_access_connector.vpc_connector]
}

# Frontend Service
resource "google_cloud_run_v2_service" "frontend_service" {
  project  = google_project.project.project_id
  name     = var.frontend_service_name
  location = var.gcp_region

  template {
    containers {
      image = "placeholder-image-frontend" # This will be replaced by our CI/CD pipeline
      ports {
        container_port = 80
      }
    }
  }

  # Allow public access to the frontend
  ingress = "INGRESS_TRAFFIC_ALL"
}

# --- IAM for Cloud Run ---

# Allow the backend service to access secrets
resource "google_secret_manager_secret_iam_member" "backend_secret_accessor" {
  project   = google_secret_manager_secret.db_password_secret.project
  secret_id = google_secret_manager_secret.db_password_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_cloud_run_v2_service.backend_service.service_account}"
}
