output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = module.lambda_function_wa_tool_updater.lambda_function_arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = module.lambda_function_wa_tool_updater.lambda_function_name
}

output "lambda_role_arn" {
  description = "ARN of the IAM role for the Lambda function"
  value       = module.lambda_function_wa_tool_updater.lambda_role_arn
}
