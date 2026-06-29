# ===========================================================
# FLD-driven Azure VNet
#
# Address space comes from Infoblox Forward Looking Delegation:
#   1. nextfld.py calls the Infoblox Federation API and claims
#      a /16 block from the 10.0.0.0/8 federated address space.
#   2. That CIDR is passed in as var.fld_vnet_cidr.
#   3. Terraform carves two /24 subnets dynamically using
#      cidrsubnet() — no hardcoded addresses anywhere.
#
# Subnets are declared INLINE (not as separate azurerm_subnet
# resources) so the VNet and its subnets are updated in a single
# atomic API call. This is what lets the CIDR change safely on a
# re-run: without it, Azure updates the VNet address space first,
# leaves the old subnets momentarily outside the new range, and
# fails with NetcfgSubnetRangeOutsideVnet.
#
# Infoblox is the IP source of truth; Terraform is the executor.
# ===========================================================

resource "azurerm_resource_group" "fld" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    Project   = "Pauls-POC"
    ManagedBy = "infoblox-fld"
    Source    = "infoblox-uddi"
  }
}

# ===========================================================
# VNet + inline subnets — all derived from the FLD CIDR
#   workload-a: first  /24  e.g. 10.8.1.0/24
#   workload-b: second /24  e.g. 10.8.2.0/24
# (azurerm 3.x inline subnet uses address_prefix, singular)
# ===========================================================

resource "azurerm_virtual_network" "fld" {
  name                = var.vnet_name
  location            = azurerm_resource_group.fld.location
  resource_group_name = azurerm_resource_group.fld.name
  address_space       = [var.fld_vnet_cidr]

  subnet {
    name           = "workload-a"
    address_prefix = cidrsubnet(var.fld_vnet_cidr, 8, 1)
  }

  subnet {
    name           = "workload-b"
    address_prefix = cidrsubnet(var.fld_vnet_cidr, 8, 2)
  }

  tags = {
    Project   = "Pauls-POC"
    ManagedBy = "infoblox-fld"
    Source    = "infoblox-uddi"
    FLD_CIDR  = var.fld_vnet_cidr
  }
}
