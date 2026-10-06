variable "aws_region" { type = string }
variable "environment" { type = string; validation { condition = contains(["dev", "stage", "prod"], var.environment); error_message = "Use dev, stage, or prod." } }
variable "image_digest" { type = string; validation { condition = startswith(var.image_digest, "sha256:"); error_message = "Deploy an immutable sha256 digest." } }

