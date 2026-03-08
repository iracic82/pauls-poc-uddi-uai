variable "aws_region" {
  description = "AWS region for the NIOS Grid Master"
  type        = string
  default     = "eu-central-1"
}

variable "admin_password" {
  description = "Password for the NIOS admin account"
  type        = string
  sensitive   = true
}

variable "azure_location" {
  description = "Azure region for VNets and VMs"
  type        = string
  default     = "northeurope"
}
