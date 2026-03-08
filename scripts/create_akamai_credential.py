import os
import json
import requests

# === Config ===
API_URL = "https://csp.infoblox.com/api/iam/v2/keys"
TOKEN = os.environ.get("TF_VAR_ddi_api_key")
OUTPUT_FILE = "akamai_credential_id"
PARTICIPANT_ID = os.environ.get("INSTRUQT_PARTICIPANT_ID")

# Akamai credentials (from Instruqt secrets)
AKAMAI_CLIENT_SECRET = os.environ.get("AKAMAI_CLIENT_SECRET")
AKAMAI_HOST = os.environ.get("AKAMAI_HOST")
AKAMAI_ACCESS_TOKEN = os.environ.get("AKAMAI_ACCESS_TOKEN")
AKAMAI_CLIENT_TOKEN = os.environ.get("AKAMAI_CLIENT_TOKEN")

# === Validation ===
if not TOKEN:
    raise EnvironmentError("TF_VAR_ddi_api_key environment variable is not set.")
if not PARTICIPANT_ID:
    raise EnvironmentError("INSTRUQT_PARTICIPANT_ID environment variable is not set.")
if not all([AKAMAI_CLIENT_SECRET, AKAMAI_HOST, AKAMAI_ACCESS_TOKEN, AKAMAI_CLIENT_TOKEN]):
    raise EnvironmentError("Akamai credential environment variables are not fully set.")

# === Construct Payload ===
credential_name = f"Akamai-EdgeDNS-{PARTICIPANT_ID}"
print(f"Creating Akamai credential: {credential_name}")

payload = {
    "name": credential_name,
    "source_id": "akamai",
    "active": True,
    "key_data": {
        "client_secret": AKAMAI_CLIENT_SECRET,
        "host": AKAMAI_HOST,
        "access_token": AKAMAI_ACCESS_TOKEN,
        "client_token": AKAMAI_CLIENT_TOKEN
    },
    "key_type": "id_and_secret"
}

# === Headers ===
headers = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# === API Call ===
print("Creating Akamai credentials in Infoblox CSP...")

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
elif response.status_code == 409:
    print("Credential already exists (409 Conflict).")
    print(json.dumps(response_data, indent=2))
else:
    print("Error creating Akamai credential.")
