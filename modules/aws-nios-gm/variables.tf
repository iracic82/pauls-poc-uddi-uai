variable "vpc_cidr" {
  description = "CIDR block for the NIOS VPC"
  type        = string
  default     = "10.100.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block for the public subnet"
  type        = string
  default     = "10.100.0.0/24"
}

variable "mgmt_ip" {
  description = "Private IP for the MGMT NIC"
  type        = string
  default     = "10.100.0.10"
}

variable "lan1_ip" {
  description = "Private IP for the LAN1 NIC"
  type        = string
  default     = "10.100.0.11"
}

variable "ami_id" {
  description = "AMI ID for the NIOS Grid Master"
  type        = string
  default     = "ami-0038ccc4c1a0034fb"
}

variable "instance_type" {
  description = "EC2 instance type for the Grid Master"
  type        = string
  default     = "m5.2xlarge"
}

variable "admin_password" {
  description = "Password for the NIOS admin account"
  type        = string
  sensitive   = true
}

variable "key_name" {
  description = "Name of the AWS key pair"
  type        = string
  default     = "pauls-poc-key"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
