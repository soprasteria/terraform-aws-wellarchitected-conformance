# terraform-aws-wellarchitected-conformance

# About
Are you Well-Architected? How do you measure it, specifically?

The purpose of this Terraform module is to help you try to answer that question in the form of AWS Config Conformance Packs.
For each pillar in the Well-Architected Framework, each best practice that is specific enough to be detected will report to be COMPLIANT or NON_COMPLIANT. Some best practices are harder to measure, like how a team evaluates culture and priorities and how to practice cloud financial management.
The best practices in Operational Excellence are not straight forward to detect, as implementation of observability may have subjective opinion on room for improvement or may be performed with 3rd party tools.
The main outcome of this module is to accelerate the Well-Architected Framework Review conversation, not to replace it with automation.

## Use-case
 - [AWS Security Hub](https://aws.amazon.com/security-hub/) with [AWS Foundational Security Best Practices](https://docs.aws.amazon.com/securityhub/latest/userguide/fsbp-standard.html) and/or [CIS AWS Foundations Benchmark](https://docs.aws.amazon.com/securityhub/latest/userguide/cis-aws-foundations-benchmark.html) is not available.
 - 3rd party tools such as [Prowler](https://prowler.com/) and [Steampipe](https://steampipe.io/) are not available or approved by your company.

 This Terraform module provisions AWS native services based on AWS Config, incl. a dedicated AWS Config Recorder, in addition to custom Lambda checks, in a standalone AWS Account.

## Usage
At least two days before your planned review, deploy the module as suggested in [examples/main.tf](examples/main.tf).
Compliance checks will update on a daily basis, to reduce unncessary costs for AWS Config Evaluations.

### Well-Architected Tool Integration
This module can also automatically update your Well-Architected Tool workload with compliance data from the AWS Config Conformance Packs. To enable this feature, set `deploy_wa_tool_updater = true` and provide your workload ID with `wa_tool_workload_id = "your-workload-id"`.

The Lambda function will:
1. Process each conformance pack (Security, Reliability, Cost Optimization)
2. Loop through all rules in sequence (SEC01, SEC02, REL01, REL02, COST01, etc.)
3. For each rule, list the resource type, resource ID, and compliance status in the Notes field of the corresponding best practice question in your Well-Architected Tool workload
4. Append new data to preserve the history of compliance changes

See [examples/complete/main.tf](examples/complete/main.tf) for a complete example with Well-Architected Tool integration.

The source code for the Lambda function is located in the [src/wa_tool_updater](src/wa_tool_updater) directory.


## Functionality

If you navigate to AWS Config - Conformance packs you will be presented with a dashboard with packs for the Security, Reliability and Cost Optimization Pillars.

![AWS Config Conformance Pack Dashboard](./gfx/screenshot-01.png)

You can view the compliance score trend for each pillar/pack:

![Well-Architected Framework Cost Optimization Pillar view](./gfx/screenshot-02.png)

You can also view the compliance status for each check, prefixed with the related best practice question, mapped to the [AWS Well-Architected Framework whitepaper](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-pillars-of-the-framework.html).

![Conformance Pack Rules](./gfx/screenshot-03.png)


<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.9 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 5 |
| <a name="requirement_util"></a> [util](#requirement\_util) | ~> 0.3.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 5 |
| <a name="provider_http"></a> [http](#provider\_http) | n/a |
| <a name="provider_util"></a> [util](#provider\_util) | ~> 0.3.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_aws_config_well_architected_recorder_s3_bucket"></a> [aws\_config\_well\_architected\_recorder\_s3\_bucket](#module\_aws\_config\_well\_architected\_recorder\_s3\_bucket) | git::https://github.com/terraform-aws-modules/terraform-aws-s3-bucket.git | 8a0b697adfbc673e6135c70246cff7f8052ad95a |
| <a name="module_lambda_function_wa_conformance_cost_02_account_structure_implemented"></a> [lambda\_function\_wa\_conformance\_cost\_02\_account\_structure\_implemented](#module\_lambda\_function\_wa\_conformance\_cost\_02\_account\_structure\_implemented) | git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git | f7866811bc1429ce224bf6a35448cb44aa5155e7 |
| <a name="module_lambda_function_wa_conformance_cost_03_add_organization_information_to_cost_and_usage"></a> [lambda\_function\_wa\_conformance\_cost\_03\_add\_organization\_information\_to\_cost\_and\_usage](#module\_lambda\_function\_wa\_conformance\_cost\_03\_add\_organization\_information\_to\_cost\_and\_usage) | git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git | f7866811bc1429ce224bf6a35448cb44aa5155e7 |
| <a name="module_lambda_function_wa_conformance_cost_03_aws_budgets"></a> [lambda\_function\_wa\_conformance\_cost\_03\_aws\_budgets](#module\_lambda\_function\_wa\_conformance\_cost\_03\_aws\_budgets) | git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git | f7866811bc1429ce224bf6a35448cb44aa5155e7 |
| <a name="module_lambda_function_wa_conformance_cost_03_aws_cost_anomaly_detection"></a> [lambda\_function\_wa\_conformance\_cost\_03\_aws\_cost\_anomaly\_detection](#module\_lambda\_function\_wa\_conformance\_cost\_03\_aws\_cost\_anomaly\_detection) | git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git | f7866811bc1429ce224bf6a35448cb44aa5155e7 |
| <a name="module_lambda_function_wa_conformance_cost_04_ec2_instances_without_auto_scaling"></a> [lambda\_function\_wa\_conformance\_cost\_04\_ec2\_instances\_without\_auto\_scaling](#module\_lambda\_function\_wa\_conformance\_cost\_04\_ec2\_instances\_without\_auto\_scaling) | git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git | f7866811bc1429ce224bf6a35448cb44aa5155e7 |
| <a name="module_wa_tool_updater"></a> [wa\_tool\_updater](#module\_wa\_tool\_updater) | ./modules/wa_tool_updater | n/a |

## Resources

| Name | Type |
|------|------|
| [aws_config_config_rule.cost_01_aws_budgets](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_config_rule) | resource |
| [aws_config_config_rule.cost_02_account_structure_implemented](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_config_rule) | resource |
| [aws_config_config_rule.cost_03_aws_budgets](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_config_rule) | resource |
| [aws_config_config_rule.cost_03_aws_cost_anomaly_detection](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_config_rule) | resource |
| [aws_config_config_rule.cost_03_organization_information_to_cost_and_usage](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_config_rule) | resource |
| [aws_config_config_rule.cost_04_decommission_resources_automatically](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_config_rule) | resource |
| [aws_config_configuration_recorder.well_architected](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_configuration_recorder) | resource |
| [aws_config_configuration_recorder_status.well_architected](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_configuration_recorder_status) | resource |
| [aws_config_conformance_pack.well_architected_conformance_pack_cost_optimization](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_conformance_pack) | resource |
| [aws_config_conformance_pack.well_architected_conformance_pack_iam](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_conformance_pack) | resource |
| [aws_config_conformance_pack.well_architected_conformance_pack_reliability](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_conformance_pack) | resource |
| [aws_config_conformance_pack.well_architected_conformance_pack_security](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_conformance_pack) | resource |
| [aws_config_delivery_channel.well_architected](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_delivery_channel) | resource |
| [aws_config_retention_configuration.example](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/config_retention_configuration) | resource |
| [aws_iam_role.config_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy.config_policy_well_architected_recorder](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_iam_role_policy_attachment.config_role_attachment](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_kms_key.aws_config_well_architected_recorder_s3_bucket](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/kms_key) | resource |
| [aws_lambda_permission.config_permissions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_permission) | resource |
| [aws_s3_object.cloudformation_wa_config_cost_optimization_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_object) | resource |
| [aws_s3_object.cloudformation_wa_config_iam_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_object) | resource |
| [aws_s3_object.cloudformation_wa_config_reliability_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_object) | resource |
| [aws_s3_object.cloudformation_wa_config_security_template](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_object) | resource |
| [aws_caller_identity.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity) | data source |
| [aws_iam_policy_document.config_policy_well_architected_recorder](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.well_architected_config_assume_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |
| [http_http.template_body_wa_iam_pillar](https://registry.terraform.io/providers/hashicorp/http/latest/docs/data-sources/http) | data source |
| [http_http.template_body_wa_reliability_pillar](https://registry.terraform.io/providers/hashicorp/http/latest/docs/data-sources/http) | data source |
| [http_http.template_body_wa_security_pillar](https://registry.terraform.io/providers/hashicorp/http/latest/docs/data-sources/http) | data source |
| [util_replace.transformed_wa_reliability_pillar](https://registry.terraform.io/providers/poseidon/util/latest/docs/data-sources/replace) | data source |
| [util_replace.transformed_wa_security_pillar](https://registry.terraform.io/providers/poseidon/util/latest/docs/data-sources/replace) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_config_custom_lambda_cloudwatch_logs_retention_in_days"></a> [config\_custom\_lambda\_cloudwatch\_logs\_retention\_in\_days](#input\_config\_custom\_lambda\_cloudwatch\_logs\_retention\_in\_days) | AWS Config Custom Lambda CloudWatch Logs retention in days. | `number` | `90` | no |
| <a name="input_config_custom_lambda_python_runtime"></a> [config\_custom\_lambda\_python\_runtime](#input\_config\_custom\_lambda\_python\_runtime) | Runtime for AWS Config Custom Lambda. | `string` | `"python3.12"` | no |
| <a name="input_config_custom_lambda_timeout"></a> [config\_custom\_lambda\_timeout](#input\_config\_custom\_lambda\_timeout) | Timeout for AWS Config Custom Lambda in seconds. | `number` | `30` | no |
| <a name="input_deploy_cost_optimization_conformance_pack"></a> [deploy\_cost\_optimization\_conformance\_pack](#input\_deploy\_cost\_optimization\_conformance\_pack) | Deploy AWS Config Conformance Pack for Cost Optimization. | `bool` | `true` | no |
| <a name="input_deploy_iam_conformance_pack"></a> [deploy\_iam\_conformance\_pack](#input\_deploy\_iam\_conformance\_pack) | Deploy AWS Config Conformance Pack for IAM. | `bool` | `true` | no |
| <a name="input_deploy_operational_excellence_conformance_pack"></a> [deploy\_operational\_excellence\_conformance\_pack](#input\_deploy\_operational\_excellence\_conformance\_pack) | Deploy AWS Config Conformance Pack for Operational Excellence. | `bool` | `true` | no |
| <a name="input_deploy_reliability_conformance_pack"></a> [deploy\_reliability\_conformance\_pack](#input\_deploy\_reliability\_conformance\_pack) | Deploy AWS Config Conformance Pack for Reliability. | `bool` | `true` | no |
| <a name="input_deploy_security_conformance_pack"></a> [deploy\_security\_conformance\_pack](#input\_deploy\_security\_conformance\_pack) | Deploy AWS Config Conformance Pack for Security. | `bool` | `true` | no |
| <a name="input_deploy_wa_tool_updater"></a> [deploy\_wa\_tool\_updater](#input\_deploy\_wa\_tool\_updater) | Deploy Lambda function to update Well-Architected Tool with conformance data. | `bool` | `false` | no |
| <a name="input_recording_frequency"></a> [recording\_frequency](#input\_recording\_frequency) | AWS Config Recording Frequency. Valid options: DAILY or CONTINUOUS. | `string` | `"DAILY"` | no |
| <a name="input_scheduled_config_custom_lambda_periodic_trigger_interval"></a> [scheduled\_config\_custom\_lambda\_periodic\_trigger\_interval](#input\_scheduled\_config\_custom\_lambda\_periodic\_trigger\_interval) | AWS Config Custom Lambda Periodic Trigger Interval. Default value of Twelve\_Hours ensures updates within the DAILY window. | `string` | `"Twelve_Hours"` | no |
| <a name="input_wa_tool_updater_dry_run"></a> [wa\_tool\_updater\_dry\_run](#input\_wa\_tool\_updater\_dry\_run) | Whether to run the Well-Architected Tool updater in dry-run mode (no actual updates). | `bool` | `true` | no |
| <a name="input_wa_tool_workload_id"></a> [wa\_tool\_workload\_id](#input\_wa\_tool\_workload\_id) | ID of the Well-Architected Tool workload to update. | `string` | `""` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_wa_tool_updater_lambda_arn"></a> [wa\_tool\_updater\_lambda\_arn](#output\_wa\_tool\_updater\_lambda\_arn) | n/a |
| <a name="output_wa_tool_updater_lambda_name"></a> [wa\_tool\_updater\_lambda\_name](#output\_wa\_tool\_updater\_lambda\_name) | n/a |
| <a name="output_well_architected_conformance_pack_cost_optimization_arn"></a> [well\_architected\_conformance\_pack\_cost\_optimization\_arn](#output\_well\_architected\_conformance\_pack\_cost\_optimization\_arn) | n/a |
| <a name="output_well_architected_conformance_pack_iam_arn"></a> [well\_architected\_conformance\_pack\_iam\_arn](#output\_well\_architected\_conformance\_pack\_iam\_arn) | n/a |
| <a name="output_well_architected_conformance_pack_reliability_arn"></a> [well\_architected\_conformance\_pack\_reliability\_arn](#output\_well\_architected\_conformance\_pack\_reliability\_arn) | n/a |
| <a name="output_well_architected_conformance_pack_security_arn"></a> [well\_architected\_conformance\_pack\_security\_arn](#output\_well\_architected\_conformance\_pack\_security\_arn) | n/a |
| <a name="output_well_architected_conformance_pack_security_template_arn"></a> [well\_architected\_conformance\_pack\_security\_template\_arn](#output\_well\_architected\_conformance\_pack\_security\_template\_arn) | n/a |
<!-- END_TF_DOCS -->

**Note**: The inputs and outputs sections are automatically generated by terraform-docs in a git pre-commit hook. This requires setup of [pre-commit-terraform](https://github.com/antonbabenko/pre-commit-terraform) . Follow the install instructions to use, including the dependencies setup. pre-commit ensures correct formatting, linting and generation of documentation. It also check's for trailing whitespace, merge conflics and mixed line endings. See [.pre-commit-config.yaml](./.pre-commit-config.yaml) for more information. A full guide to the pre-commit framework can be found [here](https://pre-commit.com/).


## Authors/contributors
Developed and maintained by Well-Architected enthusiasts in Sopra Steria, with no official company support. See [contributors.](https://github.com/soprasteria/terraform-aws-wellarchitected-conformance/graphs/contributors)
Accelerated by Amazon Q Developer.


## License
MIT licensed. For licensing information and disclaimer see [LICENSE.md](LICENSE.md).