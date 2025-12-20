# Production S3 Data Lake Configuration
# Used for 100TB+ analytics platform

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "data-eng-terraform-state"
    key    = "production/data-lake/terraform.tfstate"
    region = "us-east-1"
    
    # State locking for team collaboration
    dynamodb_table = "terraform-state-locks"
    encrypt        = true
  }
}

# Provider configuration with assume role for security
provider "aws" {
  region = var.aws_region
  
  assume_role {
    role_arn = "arn:aws:iam::${var.account_id}:role/TerraformExecutionRole"
  }
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "Data Platform"
      ManagedBy   = "Terraform"
      CostCenter  = "Data Engineering"
    }
  }
}


# S3 BUCKETS FOR DATA LAKE (LAYERED ARCHITECTURE)


# RAW/Bronze Layer - Landing zone for raw data
resource "aws_s3_bucket" "raw_data" {
  bucket = "${var.project_prefix}-raw-data-${var.environment}"
  
  tags = {
    DataLayer = "bronze"
    Retention = "30 days"
  }
}

resource "aws_s3_bucket_versioning" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "raw_data" {
  bucket = aws_s3_bucket.raw_data.id
  
  rule {
    id = "raw_data_transition"
    
    status = "Enabled"
    
    # Move to Standard-IA after 30 days
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    # Move to Glacier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
    
    # Delete after 365 days
    expiration {
      days = 365
    }
  }
}

# PROCESSED/Silver Layer - Cleaned, validated data
resource "aws_s3_bucket" "processed_data" {
  bucket = "${var.project_prefix}-processed-data-${var.environment}"
  
  tags = {
    DataLayer = "silver"
    Retention = "90 days"
  }
}

# CURATED/Gold Layer - Business-ready data
resource "aws_s3_bucket" "curated_data" {
  bucket = "${var.project_prefix}-curated-data-${var.environment}"
  
  tags = {
    DataLayer = "gold"
    Retention = "180 days"
  }
}


# IAM ROLES AND POLICIES FOR DATA ACCESS


# Role for Glue ETL jobs
resource "aws_iam_role" "glue_execution_role" {
  name = "GlueExecutionRole-${var.environment}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Service = "Glue"
  }
}

# Policy for Glue to access S3 buckets
resource "aws_iam_policy" "glue_s3_access" {
  name        = "GlueS3Access-${var.environment}"
  description = "Allows Glue to read/write from data lake buckets"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.raw_data.arn,
          "${aws_s3_bucket.raw_data.arn}/*",
          aws_s3_bucket.processed_data.arn,
          "${aws_s3_bucket.processed_data.arn}/*",
          aws_s3_bucket.curated_data.arn,
          "${aws_s3_bucket.curated_data.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_s3" {
  role       = aws_iam_role.glue_execution_role.name
  policy_arn = aws_iam_policy.glue_s3_access.arn
}


# GLUE CATALOG AND DATABASES


resource "aws_glue_catalog_database" "data_lake" {
  name = "${var.project_prefix}_data_lake_${var.environment}"
  
  parameters = {
    "description" = "Central data catalog for analytics"
  }
}

resource "aws_glue_crawler" "raw_crawler" {
  name          = "${var.project_prefix}-raw-crawler-${var.environment}"
  database_name = aws_glue_catalog_database.data_lake.name
  role          = aws_iam_role.glue_execution_role.arn
  
  s3_target {
    path = "s3://${aws_s3_bucket.raw_data.bucket}"
  }
  
  configuration = jsonencode({
    Version = 1.0
    Grouping = {
      TableLevelConfiguration = 2
    }
  })
  
  schedule = "cron(0 2 * * ? *)"  # Run daily at 2 AM
  
  tags = {
    Schedule = "daily"
  }
}


# SECURITY AND ENCRYPTION


# KMS key for bucket encryption
resource "aws_kms_key" "data_lake_key" {
  description             = "KMS key for data lake encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = {
    Purpose = "Data Encryption"
  }
}

resource "aws_kms_alias" "data_lake_key_alias" {
  name          = "alias/data-lake-key-${var.environment}"
  target_key_id = aws_kms_key.data_lake_key.key_id
}

# Enable default encryption on all buckets
resource "aws_s3_bucket_server_side_encryption_configuration" "raw_encryption" {
  bucket = aws_s3_bucket.raw_data.id
  
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.data_lake_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}


# MONITORING AND LOGGING


# S3 access logging
resource "aws_s3_bucket_logging" "raw_logging" {
  bucket = aws_s3_bucket.raw_data.id
  
  target_bucket = aws_s3_bucket.raw_data.id
  target_prefix = "logs/"
}

# CloudTrail for audit logging
resource "aws_cloudtrail" "data_lake_trail" {
  name                          = "${var.project_prefix}-data-lake-trail"
  s3_bucket_name                = aws_s3_bucket.raw_data.id
  s3_key_prefix                 = "cloudtrail/"
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true
  
  advanced_event_selector {
    name = "DataLakeEvents"
    
    field_selector {
      field  = "eventCategory"
      equals = ["Data"]
    }
    
    field_selector {
      field  = "resources.type"
      equals = ["AWS::S3::Object"]
    }
  }
  
  tags = {
    Compliance = "Enabled"
  }
}


# OUTPUTS FOR OTHER MODULES


output "raw_bucket_name" {
  value       = aws_s3_bucket.raw_data.bucket
  description = "Name of the raw data bucket"
}

output "processed_bucket_name" {
  value       = aws_s3_bucket.processed_data.bucket
  description = "Name of the processed data bucket"
}

output "curated_bucket_name" {
  value       = aws_s3_bucket.curated_data.bucket
  description = "Name of the curated data bucket"
}

output "glue_database_name" {
  value       = aws_glue_catalog_database.data_lake.name
  description = "Name of the Glue catalog database"
}

output "kms_key_arn" {
  value       = aws_kms_key.data_lake_key.arn
  description = "ARN of the KMS encryption key"
  sensitive   = true
}
