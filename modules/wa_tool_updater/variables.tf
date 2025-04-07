variable "lambda_runtime" {
  description = "Runtime for the Lambda function"
  type        = string
  default     = "python3.12"
}

variable "lambda_timeout" {
  description = "Timeout for the Lambda function in seconds"
  type        = number
  default     = 60
}

variable "lambda_memory_size" {
  description = "Memory size for the Lambda function in MB"
  type        = number
  default     = 128
}

variable "cloudwatch_logs_retention_in_days" {
  description = "CloudWatch Logs retention in days"
  type        = number
  default     = 90
}

variable "enable_scheduled_execution" {
  description = "Enable scheduled execution of the Lambda function"
  type        = bool
  default     = false
}

variable "schedule_expression" {
  description = "Schedule expression for the CloudWatch Events rule"
  type        = string
  default     = "rate(1 day)"
}

variable "workload_id" {
  description = "ID of the Well-Architected Tool workload to update"
  type        = string
  default     = ""
}

variable "dry_run" {
  description = "Whether to run in dry-run mode (no actual updates)"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
