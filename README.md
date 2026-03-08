# Paul's POC — UDDI & Universal Asset Insights

Terraform + scripts for Paul's POC lab demonstrating **Infoblox Universal DDI (UDDI)** as a single source of truth across on-prem NIOS and Azure cloud environments.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    UDDI (10.0.0.0/8)                    │
│               Single Source of Truth                     │
├──────────────┬──────────────────┬───────────────────────┤
│  NIOS GM     │  Azure VNet1     │  Azure VNet2          │
│  10.1.0.0/16 │  10.2.0.0/16     │  10.3.0.0/16          │
│  (managed)   │  (discovered)    │  (discovered)         │
│              │                  │                       │
│  On-prem DC  │  web + app       │  db + mgmt            │
│  AWS eu-cen  │  North Europe    │  North Europe         │
└──────────────┴──────────────────┴───────────────────────┘
```

### Key Concept

The Azure team does **not** use the UDDI API for subnet allocation. Instead, **Universal Asset Insights (UAI)** discovers Azure VNet IPs and populates them into UDDI automatically — creating a single source of truth without changing Azure workflows.

## What Gets Deployed

### AWS (eu-central-1)
| Resource | Details |
|---|---|
| NIOS Grid Master | AMI `ami-0038ccc4c1a0034fb`, dual-NIC (MGMT + LAN1) |
| VPC | `10.100.0.0/16` with public subnet |
| Security Group | Ports 443, 22, 53, 2114 + ICMP |
| SSH Key | TLS-generated, saved locally |

### Azure (North Europe)
| Resource | Details |
|---|---|
| VNet1 (`10.2.0.0/16`) | web subnet (`10.2.1.0/24`) + app subnet (`10.2.2.0/24`) |
| VNet2 (`10.3.0.0/16`) | db subnet (`10.3.1.0/24`) + mgmt subnet (`10.3.2.0/24`) |
| Ubuntu VMs (x4) | `Standard_B1s`, static IPs: `10.2.1.10`, `10.2.2.10`, `10.3.1.10`, `10.3.2.10` |
| NSG | SSH (22), HTTP (80/443), ICMP |
| SSH Key | TLS-generated RSA 4096, saved locally |

### NIOS IPAM & DNS (populated via WAPI)
| Component | Details |
|---|---|
| Network containers | `10.0.0.0/8` (UDDI), `10.1.0.0/16` (on-prem) |
| Networks | 16 subnets under `10.1.x.x` (servers, workstations, DMZ, mgmt, dev) |
| Fixed addresses | 23 hosts with MAC reservations |
| DHCP ranges | 8 ranges for workstations, wireless, VoIP, dev |
| DNS zone | `datacenter.local` with 21 A records + 4 CNAMEs |

## Terraform Structure

```
.
├── main.tf              # Root module — calls child modules
├── providers.tf         # AWS, AzureRM, TLS, Local providers
├── variables.tf         # aws_region, admin_password, azure_location
├── outputs.tf           # GM IP, Azure VM IPs, SSH key paths
├── modules/
│   ├── aws-nios-gm/     # VPC, subnets, SG, NIOS GM instance
│   └── azure-vnets/     # VNets, subnets, NSG, Ubuntu VMs
└── scripts/             # Python scripts for CSP setup and WAPI config
```

## Required Environment Variables

| Variable | Purpose |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS credentials |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `ARM_CLIENT_ID` | Azure SPN |
| `ARM_CLIENT_SECRET` | Azure SPN |
| `ARM_SUBSCRIPTION_ID` | Azure subscription |
| `ARM_TENANT_ID` | Azure tenant |
| `TF_VAR_admin_password` | NIOS admin password |

## Usage

```bash
terraform init
terraform apply -auto-approve

# After GM boots, populate IPAM and DNS:
cd scripts
python3 deploy_ipam_data.py
python3 deploy_dns_zones.py
```

## Lab Flow

1. **Setup** — Terraform deploys NIOS GM (AWS) + Azure VNets with VMs
2. **CSP Registration** — GM joins Infoblox Cloud Services Portal via join token
3. **IPAM Population** — `deploy_ipam_data.py` creates 10.1.0.0/16 subnets in NIOS
4. **DNS Population** — `deploy_dns_zones.py` creates `datacenter.local` zone in NIOS
5. **Cloud Discovery** — UAI discovers Azure 10.2.0.0/16 and 10.3.0.0/16 into UDDI
6. **Unified View** — UDDI shows all three /16s under 10.0.0.0/8 as single source of truth
