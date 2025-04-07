provider "aws" {
  region = "us-east-1" # Change to your preferred region
}

module "wa_tool_updater" {
  source = "../../modules/wa_tool_updater"

  # Lambda configuration
  lambda_runtime     = "python3.12"
  lambda_timeout     = 120
  lambda_memory_size = 256

  # CloudWatch Logs configuration
  cloudwatch_logs_retention_in_days = 90

  # Scheduled execution configuration
  enable_scheduled_execution = true
  schedule_expression        = "rate(1 day)"

  # Well-Architected Tool configuration
  workload_id = "your-workload-id" # Replace with your actual workload ID
  dry_run     = false              # Set to true for testing

  # Tags
  tags = {
    Environment = "dev"
    Project     = "well-architected-conformance"
  }
}
