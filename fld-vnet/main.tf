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
# Infoblox is the IP source of truth; Terraform is the executor.
# ===========================================================

resource "azurerm_resource_group" "fld" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    Project    = "Pauls-POC"
    ManagedBy  = "infoblox-fld"
    Source     = "infoblox-uddi"
  }
}

# ===========================================================
# VNet — address space from FLD CIDR
# ===========================================================

resource "azurerm_virtual_network" "fld" {
  name                = var.vnet_name
  location            = azurerm_resource_group.fld.location
  resource_group_name = azurerm_resource_group.fld.name
  address_space       = [var.fld_vnet_cidr]

  tags = {
    Project    = "Pauls-POC"
    ManagedBy  = "infoblox-fld"
    Source     = "infoblox-uddi"
    FLD_CIDR   = var.fld_vnet_cidr
  }
}

# ===========================================================
# Subnets — carved dynamically from the FLD /16
#   workload-a: first  /24  e.g. 10.4.1.0/24
#   workload-b: second /24  e.g. 10.4.2.0/24
# ===========================================================

resource "azurerm_subnet" "workload_a" {
  name                 = "workload-a"
  resource_group_name  = azurerm_resource_group.fld.name
  virtual_network_name = azurerm_virtual_network.fld.name
  address_prefixes     = [cidrsubnet(var.fld_vnet_cidr, 8, 1)]
}

resource "azurerm_subnet" "workload_b" {
  name                 = "workload-b"
  resource_group_name  = azurerm_resource_group.fld.name
  virtual_network_name = azurerm_virtual_network.fld.name
  address_prefixes     = [cidrsubnet(var.fld_vnet_cidr, 8, 2)]
}
