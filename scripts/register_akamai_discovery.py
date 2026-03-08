import os
import json
import requests

# === Configuration ===
BASE_URL = "https://csp.infoblox.com"
PROVIDERS_URL = f"{BASE_URL}/api/cloud_discovery/v2/providers"
TOKEN = os.environ.get("TF_VAR_ddi_api_key")
PARTICIPANT_ID = os.environ.get("INSTRUQT_PARTICIPANT_ID")
AKAMAI_CREDENTIAL_FILE = "akamai_credential_id"
AKAMAI_CONTRACT_ID = os.environ.get("AKAMAI_CONTRACT_ID")

# === Validation ===
if not TOKEN:
    raise EnvironmentError("TF_VAR_ddi_api_key environment variable is not set.")
if not PARTICIPANT_ID:
    raise EnvironmentError("INSTRUQT_PARTICIPANT_ID environment variable is not set.")
if not AKAMAI_CONTRACT_ID:
    raise EnvironmentError("AKAMAI_CONTRACT_ID environment variable is not set.")
if not os.path.exists(AKAMAI_CREDENTIAL_FILE):
    raise FileNotFoundError(f"Credential ID file '{AKAMAI_CREDENTIAL_FILE}' not found. Run create_akamai_credential.py first.")

# === Load credential ID from file ===
with open(AKAMAI_CREDENTIAL_FILE, "r") as f:
    AKAMAI_CREDENTIAL_ID = f.read().strip()

# === HTTP Headers ===
headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# === Dynamic names ===
provider_name = f"Akamai_EdgeDNS_{PARTICIPANT_ID}"
view_name = f"Akamai_EdgeDNS_{PARTICIPANT_ID}"

# === Construct Payload ===
payload = {
    "name": provider_name,
    "provider_type": "Akamai",
    "account_preference": "single",
    "sync_interval": "Auto",
    "desired_state": "enabled",
    "credential_preference": {
        "credential_type": "static"
    },
    "destination_types_enabled": ["DNS"],
    "source_configs": [
        {
            "cloud_credential_id": AKAMAI_CREDENTIAL_ID,
            "restricted_to_accounts": [AKAMAI_CONTRACT_ID],
            "credential_config": {}
        }
    ],
    "additional_config": {
        "excluded_accounts": [],
        "forward_zone_enabled": False,
        "internal_ranges_enabled": False,
        "federated_realms": []
    },
    "destinations": [
        {
            "destination_type": "IPAM/DHCP",
            "config": {
                "ipam": {
                    "disable_ipam_projection": True
                }
            }
        },
        {
            "destination_type": "DNS",
            "config": {
                "dns": {
                    "consolidated_zone_data_enabled": False,
                    "view_name": view_name,
                    "sync_type": "read_write",
                    "resolver_endpoints_sync_enabled": False,
                    "zone_filters": [
                        {
                            "action": "exclude",
                            "wildcards": ["akamai.sate.infoblox.com"]
                        }
                    ]
                }
            }
        }
    ]
}

# === Make the POST request ===
print(f"Registering Akamai discovery provider '{provider_name}'...")

response = requests.post(PROVIDERS_URL, headers=headers, data=json.dumps(payload))

try:
    response_data = response.json()
except Exception:
    response_data = {"raw": response.text}

print(f"Status Code: {response.status_code}")
print("Response:")
print(json.dumps(response_data, indent=2))

if response.status_code == 201:
    print("Akamai discovery provider registered successfully.")
elif response.status_code == 409:
    print("Provider already exists (409 Conflict).")
else:
    print("Failed to register Akamai discovery provider.")
