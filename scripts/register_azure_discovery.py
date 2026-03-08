#!/usr/bin/env python3
"""
Register Azure cloud discovery provider in Infoblox CSP.
Discovers Azure VNets/subnets/VMs into UDDI via UAI.

Required env vars: Infoblox_Token, INSTRUQT_AZURE_SUBSCRIPTION_INFOBLOX_TENANT_SUBSCRIPTION_ID, INSTRUQT_PARTICIPANT_ID
Required file: azure_cloud_credential_id (created by get_azure_credential_id.py)
"""

import os
import json
import requests

# === Configuration ===
API_URL = "https://csp.infoblox.com/api/cloud_discovery/v2/providers"
TOKEN = os.environ.get("Infoblox_Token")
RESTRICTED_ACCOUNT_ID = os.environ.get("INSTRUQT_AZURE_SUBSCRIPTION_INFOBLOX_TENANT_SUBSCRIPTION_ID")
PARTICIPANT_ID = os.environ.get("INSTRUQT_PARTICIPANT_ID")
CLOUD_CREDENTIAL_FILE = "azure_cloud_credential_id"

# === Validation ===
if not TOKEN:
    raise EnvironmentError("Infoblox_Token environment variable is not set.")
if not RESTRICTED_ACCOUNT_ID:
    raise EnvironmentError("INSTRUQT_AZURE_SUBSCRIPTION_INFOBLOX_TENANT_SUBSCRIPTION_ID is not set.")
if not PARTICIPANT_ID:
    raise EnvironmentError("INSTRUQT_PARTICIPANT_ID environment variable is not set.")
if not os.path.exists(CLOUD_CREDENTIAL_FILE):
    raise FileNotFoundError(f"Credential ID file '{CLOUD_CREDENTIAL_FILE}' not found. Run get_azure_credential_id.py first.")

# === Load cloud_credential_id from file ===
with open(CLOUD_CREDENTIAL_FILE, "r") as f:
    CLOUD_CREDENTIAL_ID = f.read().strip()

# === Dynamic names ===
provider_name = f"Azure_Demo_Lab_{PARTICIPANT_ID}"
view_name = f"Azure_Demo_Lab_{PARTICIPANT_ID}"

# === Construct Payload ===
payload = {
    "name": provider_name,
    "provider_type": "Microsoft Azure",
    "account_preference": "single",
    "sync_interval": "15",
    "desired_state": "enabled",
    "credential_preference": {
        "credential_type": "static"
    },
    "destination_types_enabled": ["DNS", "IPAM"],
    "source_configs": [
        {
            "cloud_credential_id": CLOUD_CREDENTIAL_ID,
            "restricted_to_accounts": [RESTRICTED_ACCOUNT_ID],
            "credential_config": {
                "access_identifier": ""
            }
        }
    ],
    "additional_config": {
        "excluded_accounts": [],
        "forward_zone_enabled": False,
        "internal_ranges_enabled": True,
        "object_type": {
            "version": 1,
            "discover_new": True,
            "objects": [
                {
                    "category": {"id": "security", "excluded": False},
                    "resource_set": [{"id": "security_groups", "excluded": False}]
                },
                {
                    "category": {"id": "compute", "excluded": False},
                    "resource_set": [
                        {"id": "tenants", "excluded": False},
                        {"id": "azure_managementgroups_management_groups", "excluded": False},
                        {"id": "metrics", "excluded": False}
                    ]
                },
                {
                    "category": {"id": "networking-basics", "excluded": False},
                    "resource_set": [
                        {"id": "public-ips", "excluded": False},
                        {"id": "network-interfaces", "excluded": False},
                        {"id": "network-interface-ip-configurations", "excluded": False},
                        {"id": "network-nat-gateways", "excluded": False},
                        {"id": "network-vpn-gateways", "excluded": False},
                        {"id": "network-route-tables", "excluded": False},
                        {"id": "network-vnet-gateways", "excluded": False},
                        {"id": "private-link-service", "excluded": False},
                        {"id": "private-endpoints", "excluded": False},
                        {"id": "network-watcher-flow-logs", "excluded": False},
                        {"id": "network-watchers", "excluded": False},
                        {"id": "network-nat-gateways-connections", "excluded": False},
                        {"id": "network-nat-application-gateways", "excluded": False},
                        {"id": "azure_network_azure_firewalls", "excluded": False},
                        {"id": "azure_network_virtual_wans", "excluded": False},
                        {"id": "azure_network_virtual_hubs", "excluded": False}
                    ]
                },
                {
                    "category": {"id": "lbs", "excluded": False},
                    "resource_set": [{"id": "network-load-balancers", "excluded": False}]
                },
                {
                    "category": {"id": "azure-storage", "excluded": False},
                    "resource_set": [
                        {"id": "storage-containers", "excluded": False},
                        {"id": "storage-accounts", "excluded": False}
                    ]
                }
            ]
        }
    },
    "destinations": [
        {
            "destination_type": "DNS",
            "config": {
                "dns": {
                    "consolidated_zone_data_enabled": False,
                    "view_name": view_name,
                    "sync_type": "read_write",
                    "resolver_endpoints_sync_enabled": False
                }
            }
        },
        {
            "destination_type": "IPAM",
            "config": {
                "ipam": {
                    "ip_space": "",
                    "dhcp_server": ""
                }
            }
        }
    ]
}

# === HTTP Headers ===
headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# === Make the POST request ===
print(f"Registering Azure cloud provider '{provider_name}' with view '{view_name}'...")

response = requests.post(API_URL, headers=headers, data=json.dumps(payload))

try:
    response_data = response.json()
except Exception:
    response_data = {"raw": response.text}

print(f"Status Code: {response.status_code}")

if response.status_code == 201:
    print("Azure cloud provider registered successfully.")
elif response.status_code == 409:
    print("Provider already exists (409 Conflict).")
else:
    print(f"Failed to register Azure cloud provider.")
    print(json.dumps(response_data, indent=2))
