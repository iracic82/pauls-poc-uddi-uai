# ===========================================================
# Azure VNets Module
# vnet1: 10.2.0.0/16 (web + app) - discovered by UAI into UDDI
# vnet2: 10.3.0.0/16 (db + mgmt)  - discovered by UAI into UDDI
# ===========================================================

# --- Resource Group ---

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# --- TLS Key for SSH ---

resource "tls_private_key" "ssh" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "local_file" "ssh_private_key" {
  filename        = "${path.root}/azure-ssh-key.pem"
  content         = tls_private_key.ssh.private_key_pem
  file_permission = "0400"
}

# ===========================================================
# VNet1 - 10.2.0.0/16 (web + app)
# ===========================================================

resource "azurerm_virtual_network" "vnet1" {
  name                = "vnet1"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.2.0.0/16"]
  tags                = var.tags
}

resource "azurerm_subnet" "vnet1_web" {
  name                 = "web-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.vnet1.name
  address_prefixes     = ["10.2.1.0/24"]
}

resource "azurerm_subnet" "vnet1_app" {
  name                 = "app-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.vnet1.name
  address_prefixes     = ["10.2.2.0/24"]
}

# ===========================================================
# VNet2 - 10.3.0.0/16 (db + mgmt)
# ===========================================================

resource "azurerm_virtual_network" "vnet2" {
  name                = "vnet2"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.3.0.0/16"]
  tags                = var.tags
}

resource "azurerm_subnet" "vnet2_db" {
  name                 = "db-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.vnet2.name
  address_prefixes     = ["10.3.1.0/24"]
}

resource "azurerm_subnet" "vnet2_mgmt" {
  name                 = "mgmt-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.vnet2.name
  address_prefixes     = ["10.3.2.0/24"]
}

# ===========================================================
# NSG - shared across all VMs
# ===========================================================

resource "azurerm_network_security_group" "main" {
  name                = "pauls-poc-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

resource "azurerm_network_security_rule" "allow_ssh" {
  name                        = "Allow-SSH"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "22"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.main.name
  network_security_group_name = azurerm_network_security_group.main.name
}

resource "azurerm_network_security_rule" "allow_https" {
  name                        = "Allow-HTTPS"
  priority                    = 110
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.main.name
  network_security_group_name = azurerm_network_security_group.main.name
}

resource "azurerm_network_security_rule" "allow_icmp" {
  name                        = "Allow-ICMP"
  priority                    = 120
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Icmp"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.main.name
  network_security_group_name = azurerm_network_security_group.main.name
}

# ===========================================================
# Public IPs - web (vnet1) and db (vnet2) only
# ===========================================================

resource "azurerm_public_ip" "vnet1_web" {
  name                = "vnet1-web-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_public_ip" "vnet2_db" {
  name                = "vnet2-db-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

# ===========================================================
# NICs
# ===========================================================

# VNet1 - Web VM NIC (with public IP)
resource "azurerm_network_interface" "vnet1_web" {
  name                = "vnet1-web-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.vnet1_web.id
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.2.1.10"
    public_ip_address_id          = azurerm_public_ip.vnet1_web.id
  }
}

# VNet1 - App VM NIC (no public IP)
resource "azurerm_network_interface" "vnet1_app" {
  name                = "vnet1-app-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.vnet1_app.id
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.2.2.10"
  }
}

# VNet2 - DB VM NIC (with public IP)
resource "azurerm_network_interface" "vnet2_db" {
  name                = "vnet2-db-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.vnet2_db.id
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.3.1.10"
    public_ip_address_id          = azurerm_public_ip.vnet2_db.id
  }
}

# VNet2 - Mgmt VM NIC (no public IP)
resource "azurerm_network_interface" "vnet2_mgmt" {
  name                = "vnet2-mgmt-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.vnet2_mgmt.id
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.3.2.10"
  }
}

# ===========================================================
# NSG -> NIC Associations
# ===========================================================

resource "azurerm_network_interface_security_group_association" "vnet1_web" {
  network_interface_id      = azurerm_network_interface.vnet1_web.id
  network_security_group_id = azurerm_network_security_group.main.id
}

resource "azurerm_network_interface_security_group_association" "vnet1_app" {
  network_interface_id      = azurerm_network_interface.vnet1_app.id
  network_security_group_id = azurerm_network_security_group.main.id
}

resource "azurerm_network_interface_security_group_association" "vnet2_db" {
  network_interface_id      = azurerm_network_interface.vnet2_db.id
  network_security_group_id = azurerm_network_security_group.main.id
}

resource "azurerm_network_interface_security_group_association" "vnet2_mgmt" {
  network_interface_id      = azurerm_network_interface.vnet2_mgmt.id
  network_security_group_id = azurerm_network_security_group.main.id
}

# ===========================================================
# Linux VMs - Ubuntu 22.04 LTS Gen2, Standard_B1s
# ===========================================================

# VNet1 - Web VM
resource "azurerm_linux_virtual_machine" "vnet1_web" {
  name                            = "vnet1-web-vm"
  location                        = azurerm_resource_group.main.location
  resource_group_name             = azurerm_resource_group.main.name
  size                            = "Standard_B1s"
  admin_username                  = var.admin_username
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.vnet1_web.id]
  tags                            = var.tags

  admin_ssh_key {
    username   = var.admin_username
    public_key = tls_private_key.ssh.public_key_openssh
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }
}

# VNet1 - App VM
resource "azurerm_linux_virtual_machine" "vnet1_app" {
  name                            = "vnet1-app-vm"
  location                        = azurerm_resource_group.main.location
  resource_group_name             = azurerm_resource_group.main.name
  size                            = "Standard_B1s"
  admin_username                  = var.admin_username
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.vnet1_app.id]
  tags                            = var.tags

  admin_ssh_key {
    username   = var.admin_username
    public_key = tls_private_key.ssh.public_key_openssh
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }
}

# VNet2 - DB VM
resource "azurerm_linux_virtual_machine" "vnet2_db" {
  name                            = "vnet2-db-vm"
  location                        = azurerm_resource_group.main.location
  resource_group_name             = azurerm_resource_group.main.name
  size                            = "Standard_B1s"
  admin_username                  = var.admin_username
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.vnet2_db.id]
  tags                            = var.tags

  admin_ssh_key {
    username   = var.admin_username
    public_key = tls_private_key.ssh.public_key_openssh
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }
}

# VNet2 - Mgmt VM
resource "azurerm_linux_virtual_machine" "vnet2_mgmt" {
  name                            = "vnet2-mgmt-vm"
  location                        = azurerm_resource_group.main.location
  resource_group_name             = azurerm_resource_group.main.name
  size                            = "Standard_B1s"
  admin_username                  = var.admin_username
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.vnet2_mgmt.id]
  tags                            = var.tags

  admin_ssh_key {
    username   = var.admin_username
    public_key = tls_private_key.ssh.public_key_openssh
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }
}
