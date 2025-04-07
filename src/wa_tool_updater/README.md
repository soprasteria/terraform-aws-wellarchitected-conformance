# Well-Architected Tool Updater

This Lambda function updates a Well-Architected Tool workload with compliance data from AWS Config Conformance Packs.

## Functionality

The Lambda function:

1. Processes each conformance pack (Security, Reliability, Cost Optimization)
2. Loops through all rules in sequence (SEC01, SEC02, REL01, COO01, etc.)
3. For each rule, collects resource compliance data including:
   - Resource type
   - Resource ID
   - Compliance status (COMPLIANT or NON_COMPLIANT)
4. Updates the corresponding question in the Well-Architected Tool workload with this information
5. Appends new data to preserve the history of compliance changes

## Usage

The Lambda function can be triggered manually or on a schedule. It expects the following event parameters:

```json
{
  "workload_id": "your-workload-id",
  "dry_run": false
}
```

- `workload_id`: ID of the Well-Architected Tool workload to update
- `dry_run`: Whether to run in dry-run mode (no actual updates)

## Dynamic Question Mapping

The Lambda function dynamically generates question mappings for each Well-Architected pillar by:

1. Calling `wellarchitected:list_answers` for the specified workload and pillar
2. **Preserving the original order** of questions as returned by the Well-Architected Tool API
3. Mapping each question to a numerical index (01, 02, etc.) based on its original position
4. Creating rule prefixes (SEC01, REL01, COST01) that correspond to these indices
5. Using this dynamic mapping to connect Config rules to Well-Architected questions

### Key Benefits

- **Automatic Adaptation**: The function automatically adapts to changes in the Well-Architected Framework without requiring manual updates to the question mapping
- **Reduced Maintenance**: No need to maintain a static mapping dictionary as questions are mapped dynamically
- **Better Scalability**: Easily handles new questions added to the Well-Architected Framework
- **Framework Integrity**: Preserves the original order of questions as defined in the Well-Architected Framework
- **Consistent Mapping**: Questions are mapped based on their actual position in the framework, not by sorting their IDs

### Implementation Details

The function includes:

- A `get_question_mapping()` function that dynamically generates the mapping for each pillar while preserving the original order
- Regular expression patterns to extract rule prefixes from Config rule names
- Improved error handling and logging for better troubleshooting
- Support for paginated results when listing answers
- Detailed logging of the mapping process including original question positions

## Mapping Configuration

The Lambda function uses the following mapping:

- `PILLAR_MAPPING`: Maps conformance pack prefixes to Well-Architected pillars

## Permissions

The Lambda function requires the following permissions:

- `config:DescribeConformancePackCompliance`
- `config:GetComplianceDetailsByConfigRule`
- `wellarchitected:GetAnswer`
- `wellarchitected:UpdateAnswer`
- `wellarchitected:ListAnswers`

## Deployment

This Lambda function is deployed as part of the terraform-aws-wellarchitected-conformance module. See the [main README](../../README.md) for more information.
