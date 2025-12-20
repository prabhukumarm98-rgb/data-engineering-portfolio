# Input variables for data lake configuration

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "dataplatform"
}

variable "account_id" {
  description = "AWS account ID"
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^\\d{12}$", var.account_id))
    error_message = "account_id must be a 12-digit AWS account number."
  }
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}

variable "retention_days_raw" {
  description = "Number of days to retain raw (bronze) data"
  type        = number
  default     = 365

  validation {
    condition     = var.retention_days_raw >= 30
    error_message = "retention_days_raw should be at least 30 days."
  }
}

variable "retention_days_processed" {
  description = "Number of days to retain processed (silver) data"
  type        = number
  default     = 180

  validation {
    condition     = var.retention_days_processed >= 30
    error_message = "retention_days_processed should be at least 30 days."
  }
}

variable "retention_days_curated" {
  description = "Number of days to retain curated (gold) data"
  type        = number
  default     = 90

  validation {
    condition     = var.retention_days_curated >= 30
    error_message = "retention_days_curated should be at least 30 days."
  }
}

variable "enable_versioning" {
  description = "Enable S3 versioning for buckets"
  type        = bool
  default     = true
}

variable "enable_encryption" {
  description = "Enable KMS-based server-side encryption"
  type        = bool
  default     = true
}
