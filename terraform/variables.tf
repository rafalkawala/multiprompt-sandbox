variable "gcp_project_id" {
  description = "The desired, unique ID for the GCP project."
  type        = string
}

variable "gcp_project_name" {
  description = "The display name for the GCP project."
  type        = string
}

variable "gcp_billing_account" {
  description = "The ID of the GCP billing account to associate with the project."
  type        = string
}

variable "gcp_region" {
  description = "The GCP region where resources will be created."
  type        = string
  default     = "us-central1"
}

variable "gcp_zone" {
  description = "The GCP zone where resources will be created."
  type        = string
  default     = "us-central1-c"
}

variable "vpc_network_name" {
  description = "The name for the VPC network."
  type        = string
  default     = "mllm-sandbox-vpc"
}

variable "frontend_service_name" {
  description = "The name for the frontend Cloud Run service."
  type        = string
  default     = "mllm-frontend-svc"
}

variable "backend_service_name" {
  description = "The name for the backend Cloud Run service."
  type        = string
  default     = "mllm-backend-svc"
}

variable "db_instance_name" {
  description = "The name of the Cloud SQL instance."
  type        = string
  default     = "mllm-sandbox-db-instance"
}

variable "db_name" {
  description = "The name of the database to create."
  type        = string
  default     = "mllm_sandbox_db"
}

variable "db_user_name" {
  description = "The name of the database user."
  type        = string
  default     = "mllm_sandbox_user"
}

variable "db_tier" {
  description = "The machine type for the Cloud SQL instance. db-g1-small is a cost-effective choice for development."
  type        = string
  default     = "db-g1-small"
}
