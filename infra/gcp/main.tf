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
resource "google_compute_network" "vpc_network" {
  name                    = "equity-alpha-engine-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "equity-alpha-engine-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc_network.id
}

# -----------------------------
# Reserve IP range for private Cloud SQL
# -----------------------------
resource "google_compute_global_address" "private_ip_range" {
  name          = "cloudsql-private-ip-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc_network.id
}

# -----------------------------
# VPC Connector for Cloud Run
# -----------------------------
resource "google_vpc_access_connector" "connector" {
  name          = var.vpc_connector_name
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc_network.name
  min_instances = 2
  max_instances = 10
}

# -----------------------------
# Private service connection for Cloud SQL
# -----------------------------
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}

# -----------------------------
# Cloud SQL instance (Postgres)
# -----------------------------
resource "google_sql_database_instance" "postgres_instance" {
  name             = var.cloud_sql_instance_name
  database_version = var.database_version
  region           = var.region

  settings {
    tier = "db-f1-micro"
    disk_autoresize = true
    disk_size       = 10
    disk_type       = "PD_SSD"

    backup_configuration {
      enabled    = true
      start_time = "02:00"
    }

    maintenance_window {
      day  = 7
      hour = 3
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.vpc_network.id
    }
  }

  deletion_protection = false
}

# -----------------------------
# Cloud SQL database
# -----------------------------
resource "google_sql_database" "database" {
  name     = "equity_alpha_engine"
  instance = google_sql_database_instance.postgres_instance.name
}

# -----------------------------
# Cloud Storage bucket
# -----------------------------
resource "google_storage_bucket" "cache_bucket" {
  name          = var.bucket_name
  location      = var.region
  storage_class = "STANDARD"
  versioning {
    enabled = false
  }
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
  labels = {
    environment = "production"
    project     = "equity-alpha-engine"
  }
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

data "google_vpc_access_connector" "existing_connector" {
  name    = "equity-vpc-connector-uk"
  region  = var.region
  project = var.project_id
}

resource "google_vpc_access_connector" "connector" {
  count         = data.google_vpc_access_connector.existing_connector.name != "" ? 0 : 1
  name          = var.vpc_connector_name
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc_network.name
  min_instances = 2
  max_instances = 10
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
    "roles/storage.objectAdmin",
    "roles/cloudsql.client"
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
  value = google_storage_bucket.cache_bucket.name
}

output "vpc_connector_name" {
  value = data.google_vpc_access_connector.existing_connector.name != "" ? data.google_vpc_access_connector.existing_connector.name : google_vpc_access_connector.connector[0].name
}

output "cloud_sql_connection_name" {
  value = google_sql_database_instance.postgres_instance.connection_name
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
