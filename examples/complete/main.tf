provider "aws" {
  region = "us-east-1" # Change to your preferred region
}

module "well_architected_conformance" {
  source = "../../"

  # AWS Config recording configuration
  recording_frequency = "DAILY" # Use DAILY to reduce costs

  # Deploy conformance packs
  deploy_security_conformance_pack               = true
  deploy_reliability_conformance_pack            = true
  deploy_cost_optimization_conformance_pack      = true
  deploy_iam_conformance_pack                    = true
  deploy_operational_excellence_conformance_pack = false # Not implemented yet

  # Well-Architected Tool Updater configuration
  deploy_wa_tool_updater  = true
  wa_tool_workload_id     = "your-workload-id" # Replace with your actual workload ID
  wa_tool_updater_dry_run = false              # Set to true for testing
}
