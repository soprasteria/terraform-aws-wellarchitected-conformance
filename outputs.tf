output "well_architected_conformance_pack_security_arn" {
  value = var.deploy_security_conformance_pack ? aws_config_conformance_pack.well_architected_conformance_pack_security[0].arn : null
}

output "well_architected_conformance_pack_reliability_arn" {
  value = var.deploy_reliability_conformance_pack ? aws_config_conformance_pack.well_architected_conformance_pack_reliability[0].arn : null
}

output "well_architected_conformance_pack_cost_optimization_arn" {
  value = var.deploy_cost_optimization_conformance_pack ? aws_config_conformance_pack.well_architected_conformance_pack_cost_optimization[0].arn : null
}

output "well_architected_conformance_pack_iam_arn" {
  value = var.deploy_iam_conformance_pack ? aws_config_conformance_pack.well_architected_conformance_pack_iam[0].arn : null
}

output "well_architected_report_generator_lambda_function_arn" {
  description = "ARN of the Well-Architected Report Generator Lambda function"
  value       = module.lambda_function_wa_report_generator.lambda_function_arn
}

output "well_architected_report_generator_lambda_function_name" {
  description = "Name of the Well-Architected Report Generator Lambda function"
  value       = module.lambda_function_wa_report_generator.lambda_function_name
}

output "well_architected_reports_s3_bucket_name" {
  description = "Name of the S3 bucket for Well-Architected compliance reports"
  value       = module.wa_reports_s3_bucket.s3_bucket_id
}

output "well_architected_reports_s3_bucket_arn" {
  description = "ARN of the S3 bucket for Well-Architected compliance reports"
  value       = module.wa_reports_s3_bucket.s3_bucket_arn
}
