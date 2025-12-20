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
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}

variable "retention_days_raw" {
  description = "Number of days to retain raw data"
  type        = number
  default     = 365
}

variable "retention_days_processed" {
  description = "Number of days to retain processed data"
  type        = number
  default     = 180
}

variable "retention_days_curated" {
  description = "Number of days to retain curated data"
  type        = number
  default     = 90
}

variable "enable_versioning" {
  description = "Enable S3 versioning for buckets"
  type        = bool
  default     = true
}

variable "enable_encryption" {
  description = "Enable server-side encryption"
  type        = bool
  default     = true
}
