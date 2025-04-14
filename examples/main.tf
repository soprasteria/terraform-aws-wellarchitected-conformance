module "well_architected_config_conformance_pack" {
  source                                    = "git::https://github.com/soprasteria/terraform-aws-wellarchitected-conformance.git?ref=c006f439fc07d2e898cc7f67c5e7bcad1dcbd2e8"
  recording_frequency                       = "DAILY"
  deploy_security_conformance_pack          = true
  deploy_reliability_conformance_pack       = true
  deploy_cost_optimization_conformance_pack = true
  deploy_iam_conformance_pack               = false
}