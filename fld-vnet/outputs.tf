output "fld_vnet_cidr" {
  description = "The CIDR block allocated by Infoblox FLD and used for this VNet"
  value       = var.fld_vnet_cidr
}

output "fld_vnet_id" {
  description = "Azure resource ID of the FLD-driven VNet"
  value       = azurerm_virtual_network.fld.id
}

output "fld_vnet_name" {
  description = "Name of the FLD-driven VNet"
  value       = azurerm_virtual_network.fld.name
}

output "workload_a_subnet_cidr" {
  description = "CIDR of the workload-a subnet (first /24 of the FLD block)"
  value       = cidrsubnet(var.fld_vnet_cidr, 8, 1)
}

output "workload_b_subnet_cidr" {
  description = "CIDR of the workload-b subnet (second /24 of the FLD block)"
  value       = cidrsubnet(var.fld_vnet_cidr, 8, 2)
}

output "resource_group_name" {
  description = "Resource group containing the FLD VNet"
  value       = azurerm_resource_group.fld.name
}
