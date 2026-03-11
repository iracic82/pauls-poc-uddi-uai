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
import time
import requests

# === Config ===
API_URL = "https://csp.infoblox.com/api/iam/v2/keys"
CLOUD_CRED_URL = "https://csp.infoblox.com/api/iam/v1/cloud_credential"
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

# === Handle response ===
if response.status_code in [200, 201]:
    print("Azure key created successfully.")
elif response.status_code == 409:
    print("Azure key already exists, continuing to fetch cloud credential ID.")
else:
    print("ERROR: Failed to create Azure credential.")
    print(json.dumps(response_data, indent=2))
    sys.exit(1)

# === Fetch cloud credential ID from /api/iam/v1/cloud_credential ===
# The /api/iam/v2/keys endpoint returns a UUID, but discovery needs the
# blox0.iam.cloudcredential.* format from /api/iam/v1/cloud_credential.
# There's a propagation delay, so we poll.
print("Waiting for Azure Cloud Credential to appear (up to 2 minutes)...")
timeout = 120
interval = 10
waited = 0
credential_id = None

while waited < timeout:
    try:
        cred_response = requests.get(CLOUD_CRED_URL, headers=headers)
        if cred_response.status_code == 200:
            creds = cred_response.json().get("results", [])
            for cred in creds:
                if cred.get("credential_type") == "Microsoft Azure":
                    credential_id = cred.get("id")
                    break
        if credential_id:
            break
    except requests.RequestException as e:
        print(f"Error fetching credentials: {e}")

    print(f"  Still waiting... {waited}s elapsed")
    time.sleep(interval)
    waited += interval

if credential_id:
    with open(OUTPUT_FILE, "w") as f:
        f.write(credential_id)
    print(f"Cloud Credential ID saved to {OUTPUT_FILE}: {credential_id}")
else:
    print("ERROR: Timed out waiting for Azure Cloud Credential.")
    sys.exit(1)
