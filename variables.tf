variable "recording_frequency" {
  description = "AWS Config Recording Frequency. Valid options: DAILY or CONTINUOUS."
  type        = string
  default     = "DAILY"
}

variable "aws_config_retention_period_in_days" {
  description = "Number of days AWS Config stores your historical information."
  type        = number
  default     = 180
}

variable "scheduled_config_custom_lambda_periodic_trigger_interval" {
  description = "AWS Config Custom Lambda Periodic Trigger Interval. Default value of Twelve_Hours ensures updates within the DAILY window. Valid Values: One_Hour | Three_Hours | Six_Hours | Twelve_Hours | TwentyFour_Hours"
  type        = string
  default     = "Twelve_Hours"
}

variable "lambda_log_level" {
  description = "Lambda log level. Valid values [DEBUG,INFO,WARNING,ERROR]."
  type        = string
  default     = "INFO"
}

variable "lambda_timezone" {
  description = "Timezone for Lambda functions. Uses pytz timezone names. Default is Europe/Paris (Central European Time)."
  type        = string
  default     = "Europe/Paris"
}

variable "lambda_python_runtime" {
  description = "Runtime for AWS Config Custom Lambda."
  type        = string
  default     = "python3.12"
}

variable "lambda_timeout" {
  description = "Timeout for AWS Config Custom Lambda in seconds."
  type        = number
  default     = 30
}

variable "lambda_cloudwatch_logs_retention_in_days" {
  description = "AWS Config Custom Lambda CloudWatch Logs retention in days."
  type        = number
  default     = 90
}

variable "deploy_security_conformance_pack" {
  description = "Deploy AWS Config Conformance Pack for Security."
  type        = bool
  default     = true
}

variable "deploy_reliability_conformance_pack" {
  description = "Deploy AWS Config Conformance Pack for Reliability."
  type        = bool
  default     = true
}

variable "deploy_cost_optimization_conformance_pack" {
  description = "Deploy AWS Config Conformance Pack for Cost Optimization."
  type        = bool
  default     = true
}

variable "deploy_iam_conformance_pack" {
  description = "Deploy AWS Config Conformance Pack for IAM."
  type        = bool
  default     = false
}

variable "security_conformance_pack_name" {
  description = "Name of the Security conformance pack"
  type        = string
  default     = "Well-Architected-Security"
}

variable "reliability_conformance_pack_name" {
  description = "Name of the Reliability conformance pack"
  type        = string
  default     = "Well-Architected-Reliability"
}

variable "cost_optimization_conformance_pack_name" {
  description = "Name of the Cost Optimization conformance pack"
  type        = string
  default     = "Well-Architected-Cost-Optimization"
}

variable "reports_bucket_name_prefix" {
  description = "Prefix for the S3 bucket name that stores Well-Architected compliance reports"
  type        = string
  default     = "well-architected-compliance-reports"
}

variable "reports_retention_days" {
  description = "Number of days to retain non-current versions of reports in the S3 bucket"
  type        = number
  default     = 90
}
