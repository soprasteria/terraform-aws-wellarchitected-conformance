# Lambda function for generating HTML reports of Well-Architected compliance data
module "lambda_function_wa_report_generator" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git?ref=f7866811bc1429ce224bf6a35448cb44aa5155e7"

  function_name = "well_architected_report_generator"
  description   = "Generates HTML reports from AWS Config compliance data for Well-Architected Framework Reviews"
  handler       = "main.lambda_handler"
  runtime       = var.lambda_python_runtime
  timeout       = var.lambda_timeout

  source_path = [
    {
      path             = "${path.module}/src/wa_report_generator"
      pip_requirements = true
    }
  ]

  environment_variables = {
    LOG_LEVEL                       = var.lambda_log_level
    TIMEZONE                        = var.lambda_timezone
    SECURITY_CONFORMANCE_PACK       = var.deploy_security_conformance_pack ? var.security_conformance_pack_name : ""
    RELIABILITY_CONFORMANCE_PACK    = var.deploy_reliability_conformance_pack ? var.reliability_conformance_pack_name : ""
    COST_OPTIMIZATION_CONFORMANCE_PACK = var.deploy_cost_optimization_conformance_pack ? var.cost_optimization_conformance_pack_name : ""
    S3_BUCKET_NAME                  = module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_id
  }

  attach_policy_statements = true
  policy_statements = {
    config = {
      effect = "Allow",
      actions = [
        "config:DescribeConformancePackCompliance",
        "config:GetComplianceDetailsByConfigRule",
      ],
      resources = ["*"]
    },
    s3 = {
      effect = "Allow",
      actions = [
        "s3:PutObject",
      ],
      resources = ["${module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_arn}/Reports/*"]
    },
    sts = {
      effect = "Allow",
      actions = [
        "sts:GetCallerIdentity",
      ],
      resources = ["*"]
    }
  }

  cloudwatch_logs_retention_in_days = var.lambda_cloudwatch_logs_retention_in_days
  tags = {
    Name = "well_architected_report_generator"
  }
}
