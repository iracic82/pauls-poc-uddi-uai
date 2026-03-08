# ===========================================================
# AWS NIOS Grid Master Module
# Manages 10.1.0.0/16 (on-prem data center block via NIOS)
# ===========================================================

data "aws_availability_zones" "available" {
  state = "available"
}

# --- VPC & Networking ---

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = merge(var.tags, { Name = "Infoblox-Lab" })
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.subnet_cidr
  map_public_ip_on_launch = true
  availability_zone       = data.aws_availability_zones.available.names[0]
  tags = merge(var.tags, { Name = "public-subnet" })
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
  tags   = merge(var.tags, { Name = "igw" })
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
  tags = merge(var.tags, { Name = "public-rt" })
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public_rt.id
}

# --- Security Group ---

resource "aws_security_group" "nios_sg" {
  name        = "nios-gm-sg"
  description = "Allow HTTPS, DNS, SSH to NIOS GM"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "nios-gm-sg" })
}

# --- Key Pair ---

resource "tls_private_key" "gm" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "gm" {
  key_name   = var.key_name
  public_key = tls_private_key.gm.public_key_openssh
}

resource "local_sensitive_file" "private_key_pem" {
  filename        = "${path.root}/pauls-poc-key.pem"
  content         = tls_private_key.gm.private_key_pem
  file_permission = "0400"
}

# --- Dual-NIC Grid Master ---

resource "aws_network_interface" "gm_mgmt" {
  subnet_id       = aws_subnet.public.id
  private_ips     = [var.mgmt_ip]
  security_groups = [aws_security_group.nios_sg.id]
  tags = merge(var.tags, { Name = "gm-mgmt-nic" })
}

resource "aws_network_interface" "gm_lan1" {
  subnet_id       = aws_subnet.public.id
  private_ips     = [var.lan1_ip]
  security_groups = [aws_security_group.nios_sg.id]
  tags = merge(var.tags, { Name = "gm-lan1-nic" })
}

resource "aws_instance" "gm" {
  ami           = var.ami_id
  instance_type = var.instance_type
  key_name      = aws_key_pair.gm.key_name

  network_interface {
    network_interface_id = aws_network_interface.gm_mgmt.id
    device_index         = 0
  }
  network_interface {
    network_interface_id = aws_network_interface.gm_lan1.id
    device_index         = 1
  }

  user_data = <<-EOF
#infoblox-config
temp_license: nios IB-V825 enterprise dns dhcp cloud
remote_console_enabled: y
default_admin_password: "${var.admin_password}"
lan1:
  v4_addr: 10.100.0.11
  v4_netmask: 255.255.255.0
  v4_gw: 10.100.0.1
mgmt:
  v4_addr: 10.100.0.10
  v4_netmask: 255.255.255.0
  v4_gw: 10.100.0.1
EOF

  tags = merge(var.tags, { Name = "Infoblox-GM" })

  depends_on = [aws_internet_gateway.gw]
}

# --- Elastic IP on LAN1 ---

resource "aws_eip" "gm_eip" {
  domain = "vpc"
  tags   = merge(var.tags, { Name = "gm-eip" })
}

resource "aws_eip_association" "gm_eip_assoc" {
  network_interface_id = aws_network_interface.gm_lan1.id
  allocation_id        = aws_eip.gm_eip.id
  private_ip_address   = var.lan1_ip

  depends_on = [aws_instance.gm]
}
