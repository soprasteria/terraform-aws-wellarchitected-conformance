# Lambda function for generating HTML reports of Well-Architected compliance data
module "lambda_function_wa_report_generator" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-lambda.git?ref=f7866811bc1429ce224bf6a35448cb44aa5155e7"

  function_name = "well_architected_report_generator"
  description   = "Generates HTML reports from AWS Config compliance data for Well-Architected Framework Reviews"
  handler       = "main.lambda_handler"
  runtime       = var.lambda_python_runtime
  timeout       = var.lambda_timeout

  source_path = [
    {
      path             = "${path.module}/src/wa_report_generator"
      pip_requirements = true
    }
  ]

  environment_variables = {
    LOG_LEVEL                       = var.lambda_log_level
    TIMEZONE                        = var.lambda_timezone
    SECURITY_CONFORMANCE_PACK       = var.deploy_security_conformance_pack ? var.security_conformance_pack_name : ""
    RELIABILITY_CONFORMANCE_PACK    = var.deploy_reliability_conformance_pack ? var.reliability_conformance_pack_name : ""
    COST_OPTIMIZATION_CONFORMANCE_PACK = var.deploy_cost_optimization_conformance_pack ? var.cost_optimization_conformance_pack_name : ""
    S3_BUCKET_NAME                  = module.wa_reports_s3_bucket.s3_bucket_id
  }

  attach_policy_statements = true
  policy_statements = {
    config = {
      effect = "Allow",
      actions = [
        "config:DescribeConformancePackCompliance",
        "config:GetComplianceDetailsByConfigRule",
      ],
      resources = ["*"]
    },
    s3 = {
      effect = "Allow",
      actions = [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      resources = [
        "${module.wa_reports_s3_bucket.s3_bucket_arn}",
        "${module.wa_reports_s3_bucket.s3_bucket_arn}/*"
      ]
    },
    sts = {
      effect = "Allow",
      actions = [
        "sts:GetCallerIdentity",
      ],
      resources = ["*"]
    },
    # KMS permissions for the dedicated reports bucket
    kms = {
      effect = "Allow",
      actions = [
        "kms:GenerateDataKey",
        "kms:Decrypt"
      ],
      resources = [aws_kms_key.wa_reports_kms_key.arn]
    },
    # Add Well-Architected Tool permissions to retrieve question titles
    wellarchitected = {
      effect = "Allow",
      actions = [
        "wellarchitected:ListAnswers",
        "wellarchitected:GetAnswer"
      ],
      resources = ["*"]
    }
  }

  cloudwatch_logs_retention_in_days = var.lambda_cloudwatch_logs_retention_in_days
  tags = {
    Name = "well_architected_report_generator"
  }
}

# KMS key for encrypting Well-Architected compliance reports
resource "aws_kms_key" "wa_reports_kms_key" {
  description             = "KMS key for Well-Architected compliance reports S3 bucket"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.aws_account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow use of the key for the Lambda function"
        Effect = "Allow"
        Principal = {
          AWS = module.lambda_function_wa_report_generator.lambda_role_arn
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name      = "wa-reports-kms-key"
    Terraform = "true"
  }
}

# KMS key alias for easier identification
resource "aws_kms_alias" "wa_reports_kms_alias" {
  name          = "alias/wa-reports-key"
  target_key_id = aws_kms_key.wa_reports_kms_key.key_id
}

# S3 bucket for storing Well-Architected compliance reports
module "wa_reports_s3_bucket" {
  source = "git::https://github.com/terraform-aws-modules/terraform-aws-s3-bucket.git?ref=8a0b697adfbc673e6135c70246cff7f8052ad95a"

  bucket = "${var.reports_bucket_name_prefix}-${local.aws_account_id}"
  acl    = "private"

  # Block all public access
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  # Enable versioning for audit trail
  versioning = {
    enabled = true
  }

  # Enable server-side encryption with KMS
  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        kms_master_key_id = aws_kms_key.wa_reports_kms_key.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }

  # Lifecycle rules for managing report versions
  lifecycle_rule = [
    {
      id      = "reports"
      enabled = true
      prefix  = "Reports/"

      noncurrent_version_expiration = {
        days = var.reports_retention_days
      }
    }
  ]

  # Force destroy for easier cleanup in dev/test environments
  # Set to false for production environments
  force_destroy = true

  tags = {
    Name        = "wa-compliance-reports"
    Environment = "all"
    Terraform   = "true"
  }
}
