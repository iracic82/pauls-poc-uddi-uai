# ===========================================================
# Pauls-POC Lab - Root Module
# ===========================================================
# UDDI manages 10.0.0.0/8
# NIOS (AWS GM) manages 10.1.0.0/16 on-prem
# Azure VNets 10.2.0.0/16 + 10.3.0.0/16 discovered by UAI
# ===========================================================

module "aws_nios_gm" {
  source = "./modules/aws-nios-gm"

  admin_password = var.admin_password

  tags = {
    Project = "Pauls-POC"
    Owner   = "Infoblox-Lab"
  }
}

module "azure_vnets" {
  source = "./modules/azure-vnets"

  location = var.azure_location

  tags = {
    Project = "Pauls-POC"
    Owner   = "Infoblox-Lab"
  }
}
