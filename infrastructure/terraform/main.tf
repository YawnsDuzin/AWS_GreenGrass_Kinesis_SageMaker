# 건설현장 안전 모니터링 시스템 - Terraform 설정
# Raspberry Pi 4 (64-bit) 엣지 디바이스 기준

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "terraform-state-construction-safety"
    key            = "infrastructure/terraform.tfstate"
    region         = "ap-northeast-2"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# ============================================
# Variables
# ============================================
variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "프로젝트 이름"
  type        = string
  default     = "construction-safety"
}

variable "environment" {
  description = "배포 환경"
  type        = string
  default     = "dev"
}

# ============================================
# Kinesis Data Streams
# ============================================
resource "aws_kinesis_stream" "safety_detection" {
  name             = "${var.project_name}-detection-stream-${var.environment}"
  shard_count      = 2
  retention_period = 24

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = {
    Name = "${var.project_name}-detection-stream"
  }
}

# ============================================
# S3 Buckets
# ============================================
resource "aws_s3_bucket" "data" {
  bucket = "${var.project_name}-data-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "models" {
  bucket = "${var.project_name}-models-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

# ============================================
# DynamoDB
# ============================================
resource "aws_dynamodb_table" "safety_events" {
  name         = "${var.project_name}-events-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "severity"
    type = "S"
  }

  global_secondary_index {
    name            = "severity-index"
    hash_key        = "severity"
    range_key       = "sk"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

# ============================================
# SNS Topic
# ============================================
resource "aws_sns_topic" "alerts" {
  name         = "${var.project_name}-alerts-${var.environment}"
  display_name = "Safety Violation Alerts"
}

# ============================================
# IoT Core
# ============================================
resource "aws_iot_policy" "device_policy" {
  name = "${var.project_name}-device-policy-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "iot:Connect",
          "iot:Publish",
          "iot:Subscribe",
          "iot:Receive"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iot_topic_rule" "violations" {
  name        = "${replace(var.project_name, "-", "_")}_violations_${var.environment}"
  enabled     = true
  sql         = "SELECT * FROM 'construction/safety/+/violations'"
  sql_version = "2016-03-23"

  kinesis {
    stream_name = aws_kinesis_stream.safety_detection.name
    partition_key = "$${device_id}"
    role_arn    = aws_iam_role.iot_kinesis.arn
  }
}

# ============================================
# IAM Roles
# ============================================
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_kinesis" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole"
}

resource "aws_iam_role" "iot_kinesis" {
  name = "${var.project_name}-iot-kinesis-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "iot.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "iot_kinesis" {
  name = "kinesis-put"
  role = aws_iam_role.iot_kinesis.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ]
        Resource = aws_kinesis_stream.safety_detection.arn
      }
    ]
  })
}

resource "aws_iam_role" "greengrass" {
  name = "${var.project_name}-greengrass-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "greengrass.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "greengrass" {
  role       = aws_iam_role.greengrass.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGreengrassResourceAccessRolePolicy"
}

# ============================================
# Data Sources
# ============================================
data "aws_caller_identity" "current" {}

# ============================================
# Outputs
# ============================================
output "kinesis_stream_name" {
  description = "Kinesis Data Stream 이름"
  value       = aws_kinesis_stream.safety_detection.name
}

output "data_bucket_name" {
  description = "데이터 S3 버킷 이름"
  value       = aws_s3_bucket.data.id
}

output "dynamodb_table_name" {
  description = "DynamoDB 테이블 이름"
  value       = aws_dynamodb_table.safety_events.name
}

output "sns_topic_arn" {
  description = "SNS 알림 토픽 ARN"
  value       = aws_sns_topic.alerts.arn
}

output "greengrass_role_arn" {
  description = "GreenGrass IAM 역할 ARN"
  value       = aws_iam_role.greengrass.arn
}
