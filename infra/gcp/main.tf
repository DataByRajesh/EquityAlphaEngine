# -----------------------------
# Terraform configuration for EquityAlphaEngine GCP infrastructure
# -----------------------------
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# -----------------------------
# VPC Network & Subnet
# -----------------------------
data "google_compute_network" "vpc_network" {
  name = "equity-alpha-engine-vpc"
}

data "google_compute_subnetwork" "subnet" {
  name   = "equity-alpha-engine-subnet"
  region = var.region
}

# -----------------------------
# Reserve IP range for private Cloud SQL
# -----------------------------
data "google_compute_global_address" "private_ip_range" {
  name = "cloudsql-private-ip-range"
}

# -----------------------------
# VPC Connector for Cloud Run
# -----------------------------
resource "google_vpc_access_connector" "connector" {
  name          = var.vpc_connector_name
  region        = var.region
  ip_cidr_range = "10.8.1.0/28"
  network       = data.google_compute_network.vpc_network.name
  subnet        = data.google_compute_subnetwork.subnet.name
  min_instances = 2
  max_instances = 10
}

# -----------------------------
# Private service connection for Cloud SQL
# -----------------------------
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = data.google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [data.google_compute_global_address.private_ip_range.name]
}





# -----------------------------
# Cloud SQL instance (Postgres)
# -----------------------------
data "google_sql_database_instance" "postgres_instance" {
  name = var.cloud_sql_instance_name
}

# -----------------------------
# Cloud SQL database
# -----------------------------
resource "google_sql_database" "database" {
  name     = "equity_alpha_engine"
  instance = data.google_sql_database_instance.postgres_instance.name
}

# -----------------------------
# Cloud Storage bucket
# -----------------------------
data "google_storage_bucket" "cache_bucket" {
  name = var.bucket_name
}

# -----------------------------
# Service Account (idempotent)
# -----------------------------
data "google_service_account" "existing_sa" {
  project    = var.project_id
  account_id = "equity-alpha-engine-sa"
}

resource "google_service_account" "service_account" {
  count        = try(length([data.google_service_account.existing_sa.email]), 0) == 0 ? 1 : 0
  account_id   = "equity-alpha-engine-sa"
  display_name = "Equity Alpha Engine Service Account"
}

# -----------------------------
# Local to reference SA email
# -----------------------------
locals {
  sa_email = try(data.google_service_account.existing_sa.email, google_service_account.service_account[0].email)
}

# -----------------------------
# Service Account Key (only for new SA)
# -----------------------------
resource "google_service_account_key" "sa_key" {
  count              = length(google_service_account.service_account) > 0 ? 1 : 0
  service_account_id = google_service_account.service_account[0].name
  public_key_type    = "TYPE_X509_PEM_FILE"
  key_algorithm      = "KEY_ALG_RSA_2048"
}

# -----------------------------
# IAM roles for SA
# -----------------------------
locals {
  iam_roles = [
    "roles/secretmanager.secretAccessor",
    "roles/secretmanager.admin",
    "roles/artifactregistry.admin",
    "roles/storage.objectAdmin",
    "roles/cloudsql.client",
    "roles/run.admin"
  ]
}

resource "google_project_iam_member" "sa_roles" {
  for_each = toset(local.iam_roles)
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${local.sa_email}"
}

# -----------------------------
# Outputs
# -----------------------------
output "service_account_email" {
  value = local.sa_email
}

output "service_account_key_json" {
  value       = try(google_service_account_key.sa_key[0].private_key, "")
  description = "Private key for the SA (sensitive)"
  sensitive   = true
}

output "service_account_key_id" {
  value = try(google_service_account_key.sa_key[0].id, "")
}

output "bucket_name" {
  value = data.google_storage_bucket.cache_bucket.name
}

output "vpc_connector_name" {
  value = google_vpc_access_connector.connector.name
}

output "cloud_sql_connection_name" {
  value = data.google_sql_database_instance.postgres_instance.connection_name
}

# -----------------------------
# Variables
# -----------------------------
variable "project_id" {
  description = "The GCP project ID"
  type        = string
  default     = "equity-alpha-engine-uk"
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "europe-west2"
}

variable "bucket_name" {
  description = "Cloud Storage bucket name"
  type        = string
  default     = "equity-alpha-engine-bucket"
}

variable "vpc_connector_name" {
  description = "VPC connector name"
  type        = string
  default     = "equity-vpc-connector-uk"
}

variable "cloud_sql_instance_name" {
  description = "Cloud SQL instance name"
  type        = string
  default     = "equity-db"
}

variable "database_version" {
  description = "Database version for Cloud SQL"
  type        = string
  default     = "POSTGRES_17"
}
