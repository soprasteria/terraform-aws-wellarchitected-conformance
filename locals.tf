locals {
  aws_account_id                          = data.aws_caller_identity.current.account_id
  url_template_body_wa_security_pillar    = "https://raw.githubusercontent.com/awslabs/aws-config-rules/refs/heads/master/aws-config-conformance-packs/Operational-Best-Practices-for-AWS-Well-Architected-Security-Pillar.yaml"
  url_template_body_wa_reliability_pillar = "https://raw.githubusercontent.com/awslabs/aws-config-rules/refs/heads/master/aws-config-conformance-packs/Operational-Best-Practices-for-AWS-Well-Architected-Reliability-Pillar.yaml"
  url_template_body_wa_iam                = "https://raw.githubusercontent.com/awslabs/aws-config-rules/refs/heads/master/aws-config-conformance-packs/Operational-Best-Practices-for-AWS-Identity-and-Access-Management.yaml"
  tag_service                             = "Well-Architected-Conformance"
}
