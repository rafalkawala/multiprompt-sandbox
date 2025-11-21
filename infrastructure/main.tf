terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
  zone    = var.gcp_zone
}

resource "google_project" "project" {
  project_id      = var.gcp_project_id
  name            = var.gcp_project_name
  billing_account = var.gcp_billing_account
}

resource "google_project_service" "project_services" {
  project = google_project.project.project_id
  # Using a for_each loop to enable multiple services cleanly
  for_each = toset([
    "run.googleapis.com",            # Cloud Run
    "sqladmin.googleapis.com",       # Cloud SQL
    "storage-component.googleapis.com", # GCS
    "artifactregistry.googleapis.com", # Artifact Registry
    "cloudbuild.googleapis.com",     # Cloud Build
    "aiplatform.googleapis.com",     # Vertex AI
    "iam.googleapis.com",            # IAM
    "secretmanager.googleapis.com",  # Secret Manager
    "cloudkms.googleapis.com",       # Cloud KMS
    "vpcaccess.googleapis.com",      # Serverless VPC Access
    "compute.googleapis.com",        # Compute Engine (for VPC)
    "servicenetworking.googleapis.com" # Service Networking (for private SQL)
  ])
  service                    = each.key
  disable_dependent_services = false
  disable_on_destroy         = false
}

# --- Database (Cloud SQL) ---

resource "random_password" "db_password" {
  length  = 16
  special = true
}

resource "google_secret_manager_secret" "db_password_secret" {
  project   = google_project.project.project_id
  secret_id = "${var.db_user_name}-password"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password_secret_version" {
  secret      = google_secret_manager_secret.db_password_secret.id
  secret_data = random_password.db_password.result
}

resource "google_sql_database_instance" "db_instance" {
  project              = google_project.project.project_id
  name                 = var.db_instance_name
  database_version     = "POSTGRES_14"
  region               = var.gcp_region

  settings {
    tier = var.db_tier
    ip_configuration {
      ipv4_enabled    = false # Disable public IP
      private_network = google_compute_network.vpc.id
    }
  }

  # Deletion protection is disabled for easier cleanup in dev environments.
  deletion_protection = false

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_sql_database" "database" {
  project  = google_project.project.project_id
  instance = google_sql_database_instance.db_instance.name
  name     = var.db_name
}

resource "google_sql_user" "db_user" {
  project  = google_project.project.project_id
  instance = google_sql_database_instance.db_instance.name
  name     = var.db_user_name
  password = random_password.db_password.result
}
