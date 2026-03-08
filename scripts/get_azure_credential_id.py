#!/usr/bin/env python3
"""
Fetch the Azure cloud credential ID from Infoblox CSP and save to file.
Used before registering the Azure cloud discovery provider.

Required env vars: Infoblox_Token, INSTRUQT_PARTICIPANT_ID
"""

import os
import json
import requests

# === Config ===
TOKEN = os.environ.get("Infoblox_Token")
PARTICIPANT_ID = os.environ.get("INSTRUQT_PARTICIPANT_ID")
OUTPUT_FILE = "azure_cloud_credential_id"

if not TOKEN:
    raise EnvironmentError("Infoblox_Token environment variable is not set.")
if not PARTICIPANT_ID:
    raise EnvironmentError("INSTRUQT_PARTICIPANT_ID environment variable is not set.")

TARGET_NAME = f"Azure-Demo-Lab-{PARTICIPANT_ID}"
print(f"Looking for credential named: '{TARGET_NAME}'")

# === Request ===
url = "https://csp.infoblox.com/api/iam/v1/cloud_credential"
headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

print("Listing all cloud credentials...")

response = requests.get(url, headers=headers)
try:
    data = response.json()
except Exception:
    data = {"raw": response.text}

print(f"Status Code: {response.status_code}")

credentials = data.get("results", [])
print(f"Found {len(credentials)} credential(s) total.")

# === Filter by dynamic name ===
filtered = [c for c in credentials if c.get("name") == TARGET_NAME]

if filtered:
    cred_id = filtered[0]["id"]
    with open(OUTPUT_FILE, "w") as f:
        f.write(cred_id)
    print(f"Credential ID for '{TARGET_NAME}' saved to {OUTPUT_FILE}: {cred_id}")
else:
    print(f"WARNING: No credential found with name: '{TARGET_NAME}'")
    # List available names for debugging
    for c in credentials:
        print(f"  - {c.get('name', '?')}")
