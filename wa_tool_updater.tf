module "lambda_function_wa_tool_updater" {
  source                            = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git?ref=f7866811bc1429ce224bf6a35448cb44aa5155e7"
  trigger_on_package_timestamp      = false
  function_name                     = "well_architected_tool_updater"
  description                       = "Updates Well-Architected Tool instances with AWS Config Conformance Pack compliance data"
  handler                           = "main.lambda_handler"
  runtime                           = var.lambda_python_runtime
  source_path                       = "${path.module}/src/wa_tool_updater"
  attach_policy_statements          = true
  timeout                           = var.lambda_timeout
  memory_size                       = 512
  cloudwatch_logs_retention_in_days = var.lambda_cloudwatch_logs_retention_in_days

  environment_variables = {
    LOG_LEVEL                          = var.lambda_log_level
    TIMEZONE                           = var.lambda_timezone
    SECURITY_CONFORMANCE_PACK          = var.security_conformance_pack_name
    RELIABILITY_CONFORMANCE_PACK       = var.reliability_conformance_pack_name
    COST_OPTIMIZATION_CONFORMANCE_PACK = var.cost_optimization_conformance_pack_name
  }

  policy_statements = {
    logs = {
      effect = "Allow"
      actions = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      resources = ["arn:aws:logs:*:*:*"]
    },
    config = {
      effect = "Allow"
      actions = [
        "config:DescribeConformancePackCompliance",
        "config:GetComplianceDetailsByConfigRule"
      ]
      resources = ["*"]
    },
    wellarchitected = {
      effect = "Allow"
      actions = [
        "wellarchitected:GetAnswer",
        "wellarchitected:ListAnswers",
        "wellarchitected:UpdateAnswer"
      ]
      resources = ["*"]
    }
  }

  tags = {
    Name = "Well-Architected-Tool-Updater"
  }
}
