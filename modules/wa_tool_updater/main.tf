module "lambda_function_wa_tool_updater" {
  source                            = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git?ref=f7866811bc1429ce224bf6a35448cb44aa5155e7"
  trigger_on_package_timestamp      = false
  function_name                     = "wa_tool_updater"
  description                       = "Updates Well-Architected Tool instances with AWS Config Conformance Pack compliance data"
  handler                           = "main.lambda_handler"
  runtime                           = var.lambda_runtime
  source_path                       = "${path.module}/../../src/wa_tool_updater"
  attach_policy_statements          = true
  timeout                           = var.lambda_timeout
  memory_size                       = var.lambda_memory_size
  cloudwatch_logs_retention_in_days = var.cloudwatch_logs_retention_in_days

  environment_variables = {
    LOG_LEVEL = "INFO"
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
        "wellarchitected:UpdateAnswer"
      ]
      resources = ["*"]
    }
  }

  tags = var.tags
}

# Optional: Create a CloudWatch Events rule to trigger the Lambda on a schedule
resource "aws_cloudwatch_event_rule" "wa_tool_updater_schedule" {
  count               = var.enable_scheduled_execution ? 1 : 0
  name                = "wa_tool_updater_schedule"
  description         = "Triggers the Well-Architected Tool Updater Lambda function"
  schedule_expression = var.schedule_expression
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "wa_tool_updater_target" {
  count     = var.enable_scheduled_execution ? 1 : 0
  rule      = aws_cloudwatch_event_rule.wa_tool_updater_schedule[0].name
  target_id = "wa_tool_updater"
  arn       = module.lambda_function_wa_tool_updater.lambda_function_arn

  input = jsonencode({
    workload_id = var.workload_id
    dry_run     = var.dry_run
  })
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
  count         = var.enable_scheduled_execution ? 1 : 0
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_function_wa_tool_updater.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.wa_tool_updater_schedule[0].arn
}
