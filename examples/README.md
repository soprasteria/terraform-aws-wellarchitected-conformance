# Complete Example with Well-Architected Tool Integration

This example demonstrates how to deploy the terraform-aws-wellarchitected-conformance module with Well-Architected Tool integration.

## Usage

```hcl
provider "aws" {
  region = "us-east-1"  # Change to your preferred region
}

module "well_architected_conformance" {
  source = "../../"

  # AWS Config recording configuration
  recording_frequency = "DAILY"  # Use DAILY to reduce costs

  # Deploy conformance packs
  deploy_security_conformance_pack          = true
  deploy_reliability_conformance_pack       = true
  deploy_cost_optimization_conformance_pack = true
  deploy_iam_conformance_pack               = true
}
```

## Prerequisites

Before deploying this example, you need:

1. An AWS account with appropriate permissions

## Features

This example deploys:

1. AWS Config Conformance Packs for Security, Reliability, Cost Optimization, and IAM
2. A Lambda function that updates a specified Well-Architected Tool workload with compliance data

## Notes

- The Lambda function will append new compliance data to the Notes field of each question in your Well-Architected Tool workload
- The compliance data includes resource type, resource ID, and compliance status
- Each update is timestamped to preserve the history of compliance changes
