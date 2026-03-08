# ===========================================================
# Root Outputs
# ===========================================================

# --- AWS NIOS Grid Master ---

output "gm_public_ip" {
  description = "Public IP of NIOS Grid Master (LAN1 EIP)"
  value       = module.aws_nios_gm.gm_public_ip
}

output "gm_instance_id" {
  description = "Instance ID of the NIOS Grid Master"
  value       = module.aws_nios_gm.gm_instance_id
}

output "aws_private_key_path" {
  description = "Path to the AWS PEM file"
  value       = module.aws_nios_gm.private_key_pem_path
}

# --- Azure VNets ---

output "vnet1_web_vm_public_ip" {
  description = "Public IP of VNet1 web VM"
  value       = module.azure_vnets.vnet1_web_vm_public_ip
}

output "vnet2_db_vm_public_ip" {
  description = "Public IP of VNet2 db VM"
  value       = module.azure_vnets.vnet2_db_vm_public_ip
}

output "azure_ssh_key_path" {
  description = "Path to the Azure SSH private key PEM file"
  value       = module.azure_vnets.ssh_private_key_path
}
