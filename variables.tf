variable "recording_frequency" {
  description = "AWS Config Recording Frequency. Valid options: DAILY or CONTINUOUS."
  type        = string
  default     = "DAILY"
}

variable "scheduled_config_custom_lambda_periodic_trigger_interval" {
  description = "AWS Config Custom Lambda Periodic Trigger Interval. Default value of Twelve_Hours ensures updates within the DAILY window."
  type        = string
  default     = "Twelve_Hours"
}

variable "lambda_log_level" {
  description = "Lambda log level. Valid values [DEBUG,INFO,WARNING,ERROR]."
  type        = string
  default     = "INFO"
}

variable "config_custom_lambda_python_runtime" {
  description = "Runtime for AWS Config Custom Lambda."
  type        = string
  default     = "python3.12"
}

variable "config_custom_lambda_timeout" {
  description = "Timeout for AWS Config Custom Lambda in seconds."
  type        = number
  default     = 30
}

variable "config_custom_lambda_cloudwatch_logs_retention_in_days" {
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
  default     = true
}

variable "deploy_operational_excellence_conformance_pack" {
  description = "Deploy AWS Config Conformance Pack for Operational Excellence."
  type        = bool
  default     = true
}

variable "deploy_wa_tool_updater" {
  description = "Deploy Lambda function to update Well-Architected Tool with conformance data."
  type        = bool
  default     = false
}

variable "wa_tool_workload_id" {
  description = "ID of the Well-Architected Tool workload to update."
  type        = string
  default     = ""
}

variable "wa_tool_updater_dry_run" {
  description = "Whether to run the Well-Architected Tool updater in dry-run mode (no actual updates)."
  type        = bool
  default     = true
}
variable "wa_tool_updater_clean_notes" {
  description = "Whether to clean all notes in the Well-Architected Tool workload before updating."
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

variable "clean_notes" {
  description = "Whether to clean all notes in the Well-Architected Tool workload before updating"
  type        = bool
  default     = false
}