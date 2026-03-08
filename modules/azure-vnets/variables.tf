variable "location" {
  description = "Azure region"
  type        = string
  default     = "northeurope"
}

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
  default     = "pauls-poc-rg"
}

variable "admin_username" {
  description = "Admin username for Linux VMs"
  type        = string
  default     = "azureuser"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
