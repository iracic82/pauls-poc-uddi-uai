output "gm_public_ip" {
  description = "Elastic IP of the NIOS Grid Master (LAN1)"
  value       = aws_eip.gm_eip.public_ip
}

output "gm_instance_id" {
  description = "Instance ID of the NIOS Grid Master"
  value       = aws_instance.gm.id
}

output "gm_mgmt_private_ip" {
  description = "MGMT NIC private IP"
  value       = var.mgmt_ip
}

output "gm_lan1_private_ip" {
  description = "LAN1 NIC private IP"
  value       = var.lan1_ip
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_key_pem_path" {
  description = "Path to the PEM file for SSH access"
  value       = local_sensitive_file.private_key_pem.filename
}
