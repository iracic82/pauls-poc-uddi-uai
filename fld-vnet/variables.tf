variable "fld_vnet_cidr" {
  description = "CIDR block allocated by Infoblox Forward Looking Delegation (e.g. 10.4.0.0/16)"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "northeurope"
}

variable "resource_group_name" {
  description = "Name of the Azure resource group for the FLD VNet"
  type        = string
  default     = "fld-vnet-rg"
}

variable "vnet_name" {
  description = "Name of the Azure VNet provisioned from the FLD CIDR"
  type        = string
  default     = "fld-vnet"
}
