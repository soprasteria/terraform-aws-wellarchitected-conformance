variable "recording_frequency" {
  type        = string
  default     = "DAILY"
  description = "AWS Config Recording Frequency."

  validation {
    condition     = contains(["DAILY", "CONTINUOUS"], var.recording_frequency)
    error_message = "The recording_frequency must be either 'DAILY' or 'CONTINUOUS'."
  }
}

variable "config_custom_lambda_timeout" {
  type        = number
  default     = 30
  description = "Timeout for AWS Config Custom Lambda in seconds."
}

variable "config_custom_lambda_python_runtime" {
  type        = string
  default     = "python3.12"
  description = "Runtime for AWS Config Custom Lambda."
}

variable "config_custom_lambda_cloudwatch_logs_retention_in_days" {
  type        = number
  default     = 90
  description = "AWS Config Custom Lambda CloudWatch Logs retention in days."
}

variable "scheduled_config_custom_lambda_periodic_trigger_interval" {
  type        = string
  default     = "One_Hour"
  description = "AWS Config Custom Lambda Periodic Trigger Interval."
  validation {
    condition     = contains(["One_Hour", "Three_Hours", "Six_Hours", "Twelve_Hours", "TwentyFour_Hours"], var.scheduled_config_custom_lambda_periodic_trigger_interval)
    error_message = "The recording_frequency must one of \"One_Hour\", \"Three_Hours\", \"Six_Hours\", \"Twelve_Hours\", \"TwentyFour_Hours\""
  }
}

variable "deploy_operational_excellence_conformance_pack" {
  type        = bool
  default     = true
  description = "Deploy AWS Config Conformance Pack for Operational Excellence."
}

variable "deploy_security_conformance_pack" {
  type        = bool
  default     = true
  description = "Deploy AWS Config Conformance Pack for Security."
}

variable "deploy_reliability_conformance_pack" {
  type        = bool
  default     = true
  description = "Deploy AWS Config Conformance Pack for Reliability."
}

variable "deploy_iam_conformance_pack" {
  type        = bool
  default     = true
  description = "Deploy AWS Config Conformance Pack for IAM."
}
variable "deploy_cost_optimization_conformance_pack" {
  type        = bool
  default     = true
  description = "Deploy AWS Config Conformance Pack for Cost Optimization."
}
