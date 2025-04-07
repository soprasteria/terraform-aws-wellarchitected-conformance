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

output "well_architected_conformance_pack_security_template_arn" {
  value = aws_s3_object.cloudformation_wa_config_security_template.id
}

output "wa_tool_updater_lambda_arn" {
  value = var.deploy_wa_tool_updater ? module.wa_tool_updater[0].lambda_function_arn : null
}

output "wa_tool_updater_lambda_name" {
  value = var.deploy_wa_tool_updater ? module.wa_tool_updater[0].lambda_function_name : null
}
