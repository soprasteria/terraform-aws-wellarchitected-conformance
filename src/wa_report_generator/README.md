# Well-Architected Report Generator

This Lambda function generates an HTML report from AWS Config Conformance Packs compliance data and uploads it to a dedicated S3 bucket.

## Functionality

The Lambda function:

1. Processes each conformance pack (Security, Reliability, Cost Optimization)
2. Retrieves question titles from the Well-Architected Tool API for more descriptive reports
3. Collects compliance data for all rules (SEC01, SEC02, REL01, COST01, etc.)
4. Organizes data by Well-Architected Framework Pillar and best practice
5. Generates an HTML report with:
   - Compliance scores for each pillar
   - Descriptive question titles from the Well-Architected Tool
   - Resource details including type, ID, and compliance status
   - Visual progress bars for compliance percentages
6. Uploads the report to a dedicated S3 bucket in the "Reports" folder

## Usage

The Lambda function should be invoked manually through the AWS Console or CLI. It expects the following event parameters:

```json
{
  "workload_id": "your-workload-id",
  "dry_run": 0
}
```

- `workload_id`: ID of the Well-Architected Tool workload (used to retrieve question titles)
- `dry_run`: Whether to run in dry-run mode (no actual uploads)

### AWS CLI Example

```bash
aws lambda invoke \
  --function-name well_architected_report_generator \
  --payload '{"workload_id":"your-workload-id","dry_run":0}' \
  response.json
```

### AWS Console Example

1. Navigate to the Lambda function in the AWS Console
2. Select the "Test" tab
3. Create a new test event with the following JSON:
   ```json
   {
     "workload_id": "your-workload-id",
     "dry_run": 0
   }
   ```
4. Click "Test" to invoke the function

## Environment Variables

The Lambda function uses the following environment variables:

- `LOG_LEVEL`: Logging level (default: INFO)
- `SECURITY_CONFORMANCE_PACK`: Name of the Security conformance pack
- `RELIABILITY_CONFORMANCE_PACK`: Name of the Reliability conformance pack
- `COST_OPTIMIZATION_CONFORMANCE_PACK`: Name of the Cost Optimization conformance pack
- `S3_BUCKET_NAME`: Name of the dedicated S3 bucket to store HTML reports
- `TIMEZONE`: Timezone for date/time formatting (default: Europe/Paris)

## HTML Report

The HTML report provides a comprehensive view of your Well-Architected compliance status:

- Organized by Well-Architected Framework Pillar
- Grouped by best practice (SEC01, SEC02, REL01, etc.) with descriptive titles
- Lists all resources with their compliance status
- Calculates compliance scores for each pillar
- Stored in the S3 bucket under the "Reports" folder

## Permissions

The Lambda function requires the following permissions:

- `config:DescribeConformancePackCompliance`
- `config:GetComplianceDetailsByConfigRule`
- `wellarchitected:ListAnswers`
- `wellarchitected:GetAnswer`
- `s3:PutObject` (for uploading HTML reports)
- `s3:GetObject` (for retrieving existing reports)
- `s3:ListBucket` (for listing reports)
- `sts:GetCallerIdentity` (for getting account ID)
- `kms:GenerateDataKey` (for encrypting reports)
- `kms:Decrypt` (for decrypting reports)

## Deployment

This Lambda function is deployed as part of the terraform-aws-wellarchitected-conformance module. See the [main README](../../README.md) for more information.
