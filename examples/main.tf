module "well_architected_config_conformance_pack" {
  source                                    = "git::https://github.com/soprasteria/terraform-aws-wellarchitected-conformance.git?ref=741c7482536fca3270a15c9a8ce4910cd816003c"
  recording_frequency                       = "DAILY"
  deploy_security_conformance_pack          = true
  deploy_reliability_conformance_pack       = true
  deploy_iam_conformance_pack               = false
  deploy_cost_optimization_conformance_pack = true
}