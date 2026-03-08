output "vnet1_web_vm_public_ip" {
  description = "Public IP of the VNet1 web VM"
  value       = azurerm_public_ip.vnet1_web.ip_address
}

output "vnet2_db_vm_public_ip" {
  description = "Public IP of the VNet2 db VM"
  value       = azurerm_public_ip.vnet2_db.ip_address
}

output "vnet1_id" {
  description = "ID of VNet1"
  value       = azurerm_virtual_network.vnet1.id
}

output "vnet2_id" {
  description = "ID of VNet2"
  value       = azurerm_virtual_network.vnet2.id
}

output "ssh_private_key_path" {
  description = "Path to the SSH private key PEM file"
  value       = local_file.ssh_private_key.filename
}

output "resource_group_name" {
  description = "Name of the Azure resource group"
  value       = azurerm_resource_group.main.name
}
