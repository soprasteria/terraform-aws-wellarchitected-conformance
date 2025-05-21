# Well-Architected Report Generator

This Lambda function generates an HTML report from AWS Config Conformance Packs compliance data and uploads it to an S3 bucket.

## Functionality

The Lambda function:

1. Processes each conformance pack (Security, Reliability, Cost Optimization)
2. Collects compliance data for all rules (SEC01, SEC02, REL01, COST01, etc.)
3. Organizes data by Well-Architected Framework Pillar and best practice
4. Generates an HTML report with:
   - Compliance scores for each pillar
   - Resource details including type, ID, and compliance status
   - Visual progress bars for compliance percentages
5. Uploads the report to an S3 bucket in the "Reports" folder

## Usage

The Lambda function can be triggered manually or on a schedule. It expects the following event parameters:

```json
{
  "workload_id": "your-workload-id",
  "dry_run": 0
}
```

- `workload_id`: ID of the Well-Architected Tool workload (included for compatibility with wa_tool_updater)
- `dry_run`: Whether to run in dry-run mode (no actual uploads)

## Environment Variables

The Lambda function uses the following environment variables:

- `LOG_LEVEL`: Logging level (default: INFO)
- `SECURITY_CONFORMANCE_PACK`: Name of the Security conformance pack
- `RELIABILITY_CONFORMANCE_PACK`: Name of the Reliability conformance pack
- `COST_OPTIMIZATION_CONFORMANCE_PACK`: Name of the Cost Optimization conformance pack
- `S3_BUCKET_NAME`: Name of the S3 bucket to store HTML reports
- `TIMEZONE`: Timezone for date/time formatting (default: Europe/Paris)

## HTML Report

The HTML report provides a comprehensive view of your Well-Architected compliance status:

- Organized by Well-Architected Framework Pillar
- Grouped by best practice (SEC01, SEC02, REL01, etc.)
- Lists all resources with their compliance status
- Calculates compliance scores for each pillar
- Stored in the S3 bucket under the "Reports" folder

## Permissions

The Lambda function requires the following permissions:

- `config:DescribeConformancePackCompliance`
- `config:GetComplianceDetailsByConfigRule`
- `s3:PutObject` (for uploading HTML reports)
- `sts:GetCallerIdentity` (for getting account ID)

## Deployment

This Lambda function is deployed as part of the terraform-aws-wellarchitected-conformance module. See the [main README](../../README.md) for more information.
