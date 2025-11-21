# --- VPC Network ---

resource "google_compute_network" "vpc" {
  project                 = google_project.project.project_id
  name                    = var.vpc_network_name
  auto_create_subnetworks = false
}

# --- Private Service Access for Cloud SQL ---

# Reserve an IP range for the private services to connect to.
resource "google_compute_global_address" "private_ip_alloc" {
  project       = google_project.project.project_id
  name          = "private-ip-alloc-for-services"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  ip_version    = "IPV4"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

# Establish the private connection.
resource "google_service_networking_connection" "private_vpc_connection" {
  project                 = google_project.project.project_id
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]

  depends_on = [google_project_service.project_services]
}

# --- Serverless VPC Access Connector ---

resource "google_vpc_access_connector" "vpc_connector" {
  project  = google_project.project.project_id
  name     = "${var.vpc_network_name}-connector"
  region   = var.gcp_region
  network  = google_compute_network.vpc.name
  ip_cidr_range = "10.8.0.0/28" # Standard range for the connector

  depends_on = [google_project_service.project_services]
}
