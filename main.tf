# AWS Config Delivery Channel to S3
resource "aws_config_delivery_channel" "well_architected" {
  name           = "well_architected_config_delivery_channel"
  s3_bucket_name = module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_id
  depends_on     = [aws_config_configuration_recorder.well_architected]
}

resource "aws_kms_key" "aws_config_well_architected_recorder_s3_bucket" {
  description             = "KMS key for S3 bucket aws-config-recorder-module-${local.aws_account_id}"
  is_enabled              = true
  enable_key_rotation     = true
  deletion_window_in_days = 7
  policy                  = <<POLICY
  {
    "Version": "2012-10-17",
    "Id": "default",
    "Statement": [
      {
        "Sid": "DefaultAllow",
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::${local.aws_account_id}:root"
        },
        "Action": "kms:*",
        "Resource": "*"
      }
    ]
  }
POLICY
}

module "aws_config_well_architected_recorder_s3_bucket" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-s3-bucket.git?ref=8a0b697adfbc673e6135c70246cff7f8052ad95a"
  bucket = "aws-config-recorder-module-${local.aws_account_id}"
  acl    = "private"

  control_object_ownership = true
  object_ownership         = "ObjectWriter"

  versioning = {
    enabled = true
  }
  allowed_kms_key_arn = aws_kms_key.aws_config_well_architected_recorder_s3_bucket.arn
  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        kms_master_key_id = aws_kms_key.aws_config_well_architected_recorder_s3_bucket.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }
  tags = {
    Name    = "Well-Architected-Config-Recorder-Bucket",
    Service = local.tag_service
  }
}

# AWS Config Configuration Recorder with recording_frequency set by input variable
resource "aws_config_configuration_recorder" "well_architected" {
  name     = "well-architected"
  role_arn = aws_iam_role.config_role.arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }

  recording_mode {
    recording_frequency = var.recording_frequency
  }
}

# AWS Config retention configuration: Number of days AWS Config stores your historical information.
resource "aws_config_retention_configuration" "example" {
  retention_period_in_days = 400
}

# Manages status (recording / stopped) of an AWS Config Configuration Recorder.
resource "aws_config_configuration_recorder_status" "well_architected" {
  name       = aws_config_configuration_recorder.well_architected.name
  is_enabled = true
  depends_on = [aws_config_delivery_channel.well_architected]
}

data "aws_iam_policy_document" "well_architected_config_assume_role" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["config.amazonaws.com"]
    }
    actions = ["sts:AssumeRole"]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceAccount"
      values   = [local.aws_account_id]
    }
  }
}

data "aws_iam_policy_document" "config_policy_well_architected_recorder" {
  statement {
    effect  = "Allow"
    actions = ["s3:PutObject", "s3:PutObjectAcl"]
    resources = [
      "${module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_arn}/*"
    ]
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
  }
  statement {
    effect  = "Allow"
    actions = ["s3:GetBucketAcl"]
    resources = [
      module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_arn
    ]
  }
}

resource "aws_iam_role_policy" "config_policy_well_architected_recorder" {
  role   = aws_iam_role.config_role.id
  name   = "well-architected-config-conformance-packs-policy"
  policy = data.aws_iam_policy_document.config_policy_well_architected_recorder.json
}

resource "aws_iam_role_policy_attachment" "config_role_attachment" {
  role       = aws_iam_role.config_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}

resource "aws_iam_role" "config_role" {
  name               = "well-architected-config-conformance-pack-role"
  assume_role_policy = data.aws_iam_policy_document.well_architected_config_assume_role.json
}

# Render templates to file on S3 to avoid template_body file limitation of 51,200 bytes
resource "aws_s3_object" "cloudformation_wa_config_security_template" {
  bucket       = module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_id
  key          = "Cloudformation/wa-config-security.yaml"
  content      = data.util_replace.transformed_wa_security_pillar.replaced
  content_type = "application/yaml"
}

resource "aws_s3_object" "cloudformation_wa_config_reliability_template" {
  bucket       = module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_id
  key          = "Cloudformation/wa-config-reliability.yaml"
  content      = data.util_replace.transformed_wa_reliability_pillar.replaced
  content_type = "application/yaml"
}

resource "aws_s3_object" "cloudformation_wa_config_iam_template" {
  bucket       = module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_id
  key          = "Cloudformation/wa-config-iam.yaml"
  content      = data.http.template_body_wa_iam_pillar.response_body
  content_type = "application/yaml"
}

resource "aws_s3_object" "cloudformation_wa_config_cost_optimization_template" {
  bucket = module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_id
  key    = "Cloudformation/wa-config-cost-optimization.yaml"
  etag   = filemd5("${path.module}/templates/aws_config_conformance_pack_cost_optimization.tftpl")
  content = templatefile("${path.module}/templates/aws_config_conformance_pack_cost_optimization.tftpl", {
    maximum_execution_frequency                                                        = var.scheduled_config_custom_lambda_periodic_trigger_interval
    lambda_function_wa_conformance_cost_aws_budgets_arn                                = module.lambda_function_wa_conformance_cost_03_aws_budgets.lambda_function_arn
    lambda_function_wa_conformance_cost_aws_cost_anomaly_detection_arn                 = module.lambda_function_wa_conformance_cost_03_aws_cost_anomaly_detection.lambda_function_arn
    lambda_function_wa_conformance_cost_account_structure_implemented_arn              = module.lambda_function_wa_conformance_cost_03_aws_cost_anomaly_detection.lambda_function_arn
    lambda_function_wa_conformance_ec2_instances_without_auto_scaling                  = module.lambda_function_wa_conformance_cost_04_ec2_instances_without_auto_scaling.lambda_function_arn
    lambda_function_wa_conformance_cost_add_organization_information_to_cost_and_usage = module.lambda_function_wa_conformance_cost_03_add_organization_information_to_cost_and_usage.lambda_function_arn
  })
  content_type = "application/yaml"
}

# Takes the source Cloudformation file from S3, generates an AWS Config Conformance pack which behind the scenes creates an AWS managed Cloudformation stack.
resource "aws_config_conformance_pack" "well_architected_conformance_pack_security" {
  count           = var.deploy_security_conformance_pack ? 1 : 0
  name            = "Well-Architected-Security"
  template_s3_uri = "s3://${module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_id}/${aws_s3_object.cloudformation_wa_config_security_template.key}"
  depends_on      = [aws_config_configuration_recorder.well_architected]
}

resource "aws_config_conformance_pack" "well_architected_conformance_pack_reliability" {
  count           = var.deploy_reliability_conformance_pack ? 1 : 0
  name            = "Well-Architected-Reliability"
  template_s3_uri = "s3://${module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_id}/${aws_s3_object.cloudformation_wa_config_reliability_template.key}"
  depends_on      = [aws_config_configuration_recorder.well_architected]

  lifecycle {
    replace_triggered_by = [
      aws_s3_object.cloudformation_wa_config_reliability_template.etag
    ]
  }
}

resource "aws_config_conformance_pack" "well_architected_conformance_pack_iam" {
  count           = var.deploy_iam_conformance_pack ? 1 : 0
  name            = "Well-Architected-IAM"
  template_s3_uri = "s3://${module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_id}/${aws_s3_object.cloudformation_wa_config_iam_template.key}"
  depends_on      = [aws_config_configuration_recorder.well_architected]

  lifecycle {
    replace_triggered_by = [
      aws_s3_object.cloudformation_wa_config_iam_template.etag
    ]
  }
}

resource "aws_config_conformance_pack" "well_architected_conformance_pack_cost_optimization" {
  count           = var.deploy_cost_optimization_conformance_pack ? 1 : 0
  name            = "Well-Architected-Cost-Optimization"
  template_s3_uri = "s3://${module.aws_config_well_architected_recorder_s3_bucket.s3_bucket_id}/${aws_s3_object.cloudformation_wa_config_cost_optimization_template.key}"
  depends_on      = [aws_config_configuration_recorder.well_architected]

  #  lifecycle {
  #    replace_triggered_by = [
  #      aws_s3_object.cloudformation_wa_config_cost_optimization_template.etag
  #    ]
  #  }
}
