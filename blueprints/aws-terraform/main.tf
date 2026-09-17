locals { name = "factory-service-${var.environment}" }

resource "aws_cloudwatch_log_group" "service" {
  name              = "/service/${local.name}"
  retention_in_days = var.environment == "prod" ? 90 : 14
  kms_key_id        = aws_kms_key.logs.arn
}

resource "aws_kms_key" "logs" {
  description             = "Log encryption for ${local.name}"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

output "approved_image_digest" { value = var.image_digest }

