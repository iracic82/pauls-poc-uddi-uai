#!/usr/bin/env python3
"""
Create Azure cloud credential in Infoblox CSP using Instruqt Azure SPN details.
Saves the credential ID to file for use by register_azure_discovery.py.

Required env vars: TF_VAR_ddi_api_key, INSTRUQT_PARTICIPANT_ID,
  INSTRUQT_AZURE_SUBSCRIPTION_INFOBLOX_TENANT_TENANT_ID,
  INSTRUQT_AZURE_SUBSCRIPTION_INFOBLOX_TENANT_SPN_ID,
  INSTRUQT_AZURE_SUBSCRIPTION_INFOBLOX_TENANT_SPN_PASSWORD
"""

import os
import json
import sys
import requests

# === Config ===
API_URL = "https://csp.infoblox.com/api/iam/v2/keys"
TOKEN = os.environ.get("TF_VAR_ddi_api_key")
OUTPUT_FILE = "azure_cloud_credential_id"

TENANT_ID = os.environ.get("INSTRUQT_AZURE_SUBSCRIPTION_INFOBLOX_TENANT_TENANT_ID")
CLIENT_ID = os.environ.get("INSTRUQT_AZURE_SUBSCRIPTION_INFOBLOX_TENANT_SPN_ID")
CLIENT_SECRET = os.environ.get("INSTRUQT_AZURE_SUBSCRIPTION_INFOBLOX_TENANT_SPN_PASSWORD")
PARTICIPANT_ID = os.environ.get("INSTRUQT_PARTICIPANT_ID")

# === Validation ===
if not TOKEN:
    raise EnvironmentError("TF_VAR_ddi_api_key environment variable is not set.")
if not TENANT_ID or not CLIENT_ID or not CLIENT_SECRET:
    raise EnvironmentError("Azure environment variables are not fully set.")
if not PARTICIPANT_ID:
    raise EnvironmentError("INSTRUQT_PARTICIPANT_ID environment variable is not set.")

# === Construct dynamic credential name ===
credential_name = f"Azure-Demo-Lab-{PARTICIPANT_ID}"
print(f"Creating credential with name: {credential_name}")

# === Construct Payload ===
payload = {
    "name": credential_name,
    "source_id": "azure",
    "active": True,
    "key_data": {
        "tenant_id": TENANT_ID,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    },
    "key_type": "id_and_secret"
}

# === Headers ===
headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# === API Call ===
print("Creating Azure credentials in Infoblox CSP...")

response = requests.post(API_URL, headers=headers, data=json.dumps(payload))

try:
    response_data = response.json()
except Exception:
    response_data = {"raw": response.text}

print(f"Status Code: {response.status_code}")
print("Full API Response:")
print(json.dumps(response_data, indent=2))

# === Handle response and extract ID ===
if response.status_code in [200, 201]:
    result = response_data.get("results", {})
    credential_id = result.get("id")
    if credential_id:
        with open(OUTPUT_FILE, "w") as f:
            f.write(credential_id)
        print(f"Credential ID saved to {OUTPUT_FILE}: {credential_id}")
    else:
        print("WARNING: Credential ID not found in response.")
        print(json.dumps(response_data, indent=2))
elif response.status_code == 409:
    print("Credential already exists (409 Conflict).")
    print(json.dumps(response_data, indent=2))
else:
    print("ERROR: Failed to create Azure credential.")
    print(json.dumps(response_data, indent=2))
    sys.exit(1)
