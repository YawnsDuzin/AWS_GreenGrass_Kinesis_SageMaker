# Terraform 변수 정의

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
  description = "배포 환경 (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment는 dev, staging, prod 중 하나여야 합니다."
  }
}

variable "kinesis_shard_count" {
  description = "Kinesis 스트림 샤드 수"
  type        = number
  default     = 2
}

variable "kinesis_retention_hours" {
  description = "Kinesis 데이터 보존 기간 (시간)"
  type        = number
  default     = 24
}

variable "enable_firehose" {
  description = "Kinesis Firehose 활성화 여부"
  type        = bool
  default     = true
}

variable "s3_lifecycle_days_ia" {
  description = "S3 IA로 전환 일수"
  type        = number
  default     = 30
}

variable "s3_lifecycle_days_glacier" {
  description = "S3 Glacier로 전환 일수"
  type        = number
  default     = 90
}

variable "dynamodb_ttl_days" {
  description = "DynamoDB TTL 일수"
  type        = number
  default     = 7
}

variable "tags" {
  description = "리소스에 추가할 태그"
  type        = map(string)
  default     = {}
}
