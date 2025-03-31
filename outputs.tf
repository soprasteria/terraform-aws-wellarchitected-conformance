output "well_architected_conformance_pack_security_arn" {
  value = one(aws_config_conformance_pack.well_architected_conformance_pack_security[*].arn)
}

output "well_architected_conformance_pack_reliability_arn" {
  value = one(aws_config_conformance_pack.well_architected_conformance_pack_reliability[*].arn)
}

output "well_architected_conformance_pack_iam_arn" {
  value = one(aws_config_conformance_pack.well_architected_conformance_pack_iam[*].arn)
}

output "well_architected_conformance_pack_cost_optimization_arn" {
  value = one(aws_config_conformance_pack.well_architected_conformance_pack_cost_optimization[*].arn)
}

output "well_architected_conformance_pack_security_template_arn" {
  value = aws_s3_object.cloudformation_wa_config_security_template.arn
}
