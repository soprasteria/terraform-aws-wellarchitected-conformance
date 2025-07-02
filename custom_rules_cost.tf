# COST02
module "lambda_function_wa_conformance_cost_02_account_structure_implemented" {
  source                            = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git?ref=f7866811bc1429ce224bf6a35448cb44aa5155e7"
  trigger_on_package_timestamp      = false
  function_name                     = "WA-COST02-BP03-Implement-an-account-structure"
  description                       = "AWS Config Custom Rule which checks for the AWS account being a member account in AWS Organizations with consolidated billing enabled."
  handler                           = "index.lambda_handler"
  runtime                           = var.lambda_python_runtime
  source_path                       = "src/cost02_account_structure_implemented/index.py"
  attach_policy_statements          = true
  timeout                           = var.lambda_timeout
  cloudwatch_logs_retention_in_days = var.lambda_cloudwatch_logs_retention_in_days
  policy_statements = {
    statement = {
      effect = "Allow"
      actions = [
        "organizations:DescribeOrganization",
        "config:PutEvaluations"
      ]
      resources = ["*"]
    }
  }

  tags = {
    Name    = "Well-Architected-Conformance-COST02-BP03-Implement-an-account-structure",
    Service = local.tag_service
  }
}

# COST03
# AWS Lambda function based on module from terraform-aws-modules
module "lambda_function_wa_conformance_cost_03_aws_budgets" {
  source                            = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git?ref=f7866811bc1429ce224bf6a35448cb44aa5155e7"
  trigger_on_package_timestamp      = false
  function_name                     = "WA-COST03-BP05-AWS-Budgets"
  description                       = "AWS Config Custom Rule which checks for AWS Budgets setup according to WAF COST03-BP05."
  handler                           = "index.lambda_handler"
  runtime                           = var.lambda_python_runtime
  source_path                       = "src/cost03_aws_budgets/index.py"
  attach_policy_statements          = true
  timeout                           = var.lambda_timeout
  cloudwatch_logs_retention_in_days = var.lambda_cloudwatch_logs_retention_in_days
  policy_statements = {
    statement = {
      effect = "Allow"
      actions = [
        "budgets:DescribeBudgets",
        "budgets:ViewBudget",
        "config:PutEvaluations"
      ]
      resources = ["*"]
    }
  }

  tags = {
    Name    = "Well-Architected-Conformance-COST03-BP05-AWS-Budgets",
    Service = local.tag_service
  }
}

# AWS Lambda function based on module from terraform-aws-modules
module "lambda_function_wa_conformance_cost_03_aws_cost_anomaly_detection" {
  source                            = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git?ref=f7866811bc1429ce224bf6a35448cb44aa5155e7"
  trigger_on_package_timestamp      = false
  function_name                     = "WA-COST03-BP05-AWS-Cost-Anomaly-Detection"
  description                       = "AWS Config Custom Rule which checks for AWS Cost Anomaly Detection setup according to WAF COST03-BP05."
  handler                           = "index.lambda_handler"
  runtime                           = var.lambda_python_runtime
  source_path                       = "src/cost03_aws_cost_anomaly_detection/index.py"
  attach_policy_statements          = true
  timeout                           = var.lambda_timeout
  cloudwatch_logs_retention_in_days = var.lambda_cloudwatch_logs_retention_in_days
  policy_statements = {
    statement = {
      effect = "Allow"
      actions = [
        "ce:GetAnomalyMonitors",
        "config:PutEvaluations"
      ]
      resources = ["*"]
    }
  }

  tags = {
    Name = "Well-Architected-Conformance-COST03-BP05-AWS-Cost-Anomaly-Detection"
  }
}

# AWS Lambda function based on module from terraform-aws-modules
module "lambda_function_wa_conformance_cost_03_add_organization_information_to_cost_and_usage" {
  source                            = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git?ref=f7866811bc1429ce224bf6a35448cb44aa5155e7"
  trigger_on_package_timestamp      = false
  function_name                     = "WA-COST03-BP02-Add-Organization-info-to-cost-and-usage"
  description                       = "AWS Config Custom Rule which checks if the AWS account is a member of AWS Organizations and at least one Tagging Policy is enabled."
  handler                           = "index.lambda_handler"
  runtime                           = var.lambda_python_runtime
  source_path                       = "src/cost03_add_organization_information_to_cost_and_usage/index.py"
  attach_policy_statements          = true
  timeout                           = var.lambda_timeout
  cloudwatch_logs_retention_in_days = var.lambda_cloudwatch_logs_retention_in_days
  policy_statements = {
    statement = {
      effect = "Allow"
      actions = [
        "organizations:DescribeEffectivePolicy",
        "organizations:ListPoliciesForTarget",
        "organizations:DescribeOrganization",
        "config:PutEvaluations"
      ]
      resources = ["*"]
    }
  }

  tags = {
    Name    = "Well-Architected-Conformance-COST03-BP05-AWS-Cost-Anomaly-Detection",
    Service = local.tag_service
  }
}

# AWS Lambda function based on module from terraform-aws-modules
module "lambda_function_wa_conformance_cost_04_ec2_instances_without_auto_scaling" {
  source                            = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git?ref=f7866811bc1429ce224bf6a35448cb44aa5155e7"
  trigger_on_package_timestamp      = false
  function_name                     = "WA-COST04-BP04-Decommision-Resources_Automatically"
  description                       = "AWS Config Custom Rule which checks for EC2 instances not associated with Auto Scaling Groups."
  handler                           = "index.lambda_handler"
  runtime                           = var.lambda_python_runtime
  source_path                       = "src/cost_04_ec2_instances_without_auto_scaling/index.py"
  attach_policy_statements          = true
  timeout                           = 120
  cloudwatch_logs_retention_in_days = var.lambda_cloudwatch_logs_retention_in_days
  policy_statements = {
    statement = {
      effect = "Allow"
      actions = [
        "config:PutEvaluations",
        "ec2:DescribeRegions",
        "ec2:DescribeInstances",
        "autoscaling:DescribeAutoScalingInstances",

      ]
      resources = ["*"]
    }
  }

  tags = {
    Name    = "Well-Architected-Conformance-COST04-BP04-Decommision-Resources_Automatically",
    Service = local.tag_service
  }
}


# Lambda permissions for AWS Config
resource "aws_lambda_permission" "config_permissions" {
  for_each = toset([
    module.lambda_function_wa_conformance_cost_02_account_structure_implemented.lambda_function_name,
    module.lambda_function_wa_conformance_cost_03_aws_budgets.lambda_function_name,
    module.lambda_function_wa_conformance_cost_03_aws_cost_anomaly_detection.lambda_function_name,
    module.lambda_function_wa_conformance_cost_03_add_organization_information_to_cost_and_usage.lambda_function_name,
    module.lambda_function_wa_conformance_cost_04_ec2_instances_without_auto_scaling.lambda_function_name
  ])

  statement_id   = "AllowConfigInvoke"
  action         = "lambda:InvokeFunction"
  function_name  = each.value
  principal      = "config.amazonaws.com"
  source_account = local.aws_account_id
}


resource "aws_config_config_rule" "cost_01_aws_budgets" {
  name        = "cost01-cloud-financial-management_bp_aws-budgets"
  description = "Checks for AWS Budgets setup according to WAF COST01-BP05 Report and notify on cost optimization."

  source {
    owner             = "CUSTOM_LAMBDA"
    source_identifier = module.lambda_function_wa_conformance_cost_03_aws_budgets.lambda_function_arn

    source_detail {
      message_type                = "ScheduledNotification"
      maximum_execution_frequency = var.scheduled_config_custom_lambda_periodic_trigger_interval
    }
  }

  depends_on = [module.lambda_function_wa_conformance_cost_03_aws_budgets]
}

resource "aws_config_config_rule" "cost_02_account_structure_implemented" {
  name        = "cost02-govern-usage_bp_implement-an-account-structure"
  description = "Checks for the AWS account being a member account in AWS Organizations with consolidated billing enabled."

  source {
    owner             = "CUSTOM_LAMBDA"
    source_identifier = module.lambda_function_wa_conformance_cost_02_account_structure_implemented.lambda_function_arn

    source_detail {
      message_type                = "ScheduledNotification"
      maximum_execution_frequency = var.scheduled_config_custom_lambda_periodic_trigger_interval
    }
  }

  depends_on = [module.lambda_function_wa_conformance_cost_02_account_structure_implemented]
}

resource "aws_config_config_rule" "cost_03_organization_information_to_cost_and_usage" {
  name        = "cost03-monitor-usage_bp_organization-information-to-cost-and-usage-with-tags"
  description = "Checks for AWS Organization Tag Policies enabled and at least one Tag Policy applicable for the AWS account."

  source {
    owner             = "CUSTOM_LAMBDA"
    source_identifier = module.lambda_function_wa_conformance_cost_03_aws_budgets.lambda_function_arn

    source_detail {
      message_type                = "ScheduledNotification"
      maximum_execution_frequency = var.scheduled_config_custom_lambda_periodic_trigger_interval
    }
  }

  depends_on = [module.lambda_function_wa_conformance_cost_03_aws_budgets]
}

resource "aws_config_config_rule" "cost_03_aws_budgets" {
  name        = "cost03-monitor-usage_bp_aws-budgets"
  description = "Checks for AWS Budgets setup according to WAF COST03-BP05 Configure billing and cost management tools."

  source {
    owner             = "CUSTOM_LAMBDA"
    source_identifier = module.lambda_function_wa_conformance_cost_03_aws_budgets.lambda_function_arn

    source_detail {
      message_type                = "ScheduledNotification"
      maximum_execution_frequency = var.scheduled_config_custom_lambda_periodic_trigger_interval
    }
  }

  depends_on = [module.lambda_function_wa_conformance_cost_03_aws_budgets]
}

resource "aws_config_config_rule" "cost_03_aws_cost_anomaly_detection" {
  name        = "cost03-monitor-usage_bp_aws-cost-anomaly-detection"
  description = "Checks for AWS Cost Anomaly Detection setup according to WAF COST03-BP05 Configure billing and cost management tools."

  source {
    owner             = "CUSTOM_LAMBDA"
    source_identifier = module.lambda_function_wa_conformance_cost_03_aws_cost_anomaly_detection.lambda_function_arn

    source_detail {
      message_type                = "ScheduledNotification"
      maximum_execution_frequency = var.scheduled_config_custom_lambda_periodic_trigger_interval
    }
  }

  depends_on = [module.lambda_function_wa_conformance_cost_03_aws_cost_anomaly_detection]
}

resource "aws_config_config_rule" "cost_04_decommission_resources_automatically" {
  name        = "cost03-decomissioning-resources_bp_decommission-resources-automatically"
  description = "Checks for EC2 instances not associated with Auto Scaling Groups."

  source {
    owner             = "CUSTOM_LAMBDA"
    source_identifier = module.lambda_function_wa_conformance_cost_04_ec2_instances_without_auto_scaling.lambda_function_arn

    source_detail {
      message_type                = "ScheduledNotification"
      maximum_execution_frequency = var.scheduled_config_custom_lambda_periodic_trigger_interval
    }
  }

  depends_on = [module.lambda_function_wa_conformance_cost_04_ec2_instances_without_auto_scaling]
}
