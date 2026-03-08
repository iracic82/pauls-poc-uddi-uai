import os
import json
import requests
from akamai.edgegrid import EdgeGridAuth
from urllib.parse import urljoin

# === Configuration ===
AKAMAI_HOST = os.environ.get("AKAMAI_HOST")
AKAMAI_CLIENT_TOKEN = os.environ.get("AKAMAI_CLIENT_TOKEN")
AKAMAI_CLIENT_SECRET = os.environ.get("AKAMAI_CLIENT_SECRET")
AKAMAI_ACCESS_TOKEN = os.environ.get("AKAMAI_ACCESS_TOKEN")

ZONE = "acme.corp"

# Records to preserve (type, name)
PRESERVE = {
    ("NS", "acme.corp"),
    ("SOA", "acme.corp"),
    ("A", "app-demo.acme.corp"),
}

# === Validation ===
if not all([AKAMAI_HOST, AKAMAI_CLIENT_TOKEN, AKAMAI_CLIENT_SECRET, AKAMAI_ACCESS_TOKEN]):
    raise EnvironmentError("Akamai credential environment variables are not fully set.")

# === Setup EdgeGrid auth ===
base_url = f"https://{AKAMAI_HOST}"
session = requests.Session()
session.auth = EdgeGridAuth(
    client_token=AKAMAI_CLIENT_TOKEN,
    client_secret=AKAMAI_CLIENT_SECRET,
    access_token=AKAMAI_ACCESS_TOKEN,
)

# === List all record sets ===
print(f"Listing DNS records in zone '{ZONE}'...")
url = urljoin(base_url, f"/config-dns/v2/zones/{ZONE}/recordsets")
response = session.get(url)

if response.status_code != 200:
    print(f"Error listing records: {response.status_code}")
    print(response.text)
    exit(1)

data = response.json()
recordsets = data.get("recordsets", [])
print(f"Found {len(recordsets)} record sets.")

# === Delete non-preserved records ===
deleted = 0
skipped = 0

for rs in recordsets:
    rtype = rs.get("type", "")
    rname = rs.get("name", "")

    if (rtype, rname) in PRESERVE:
        print(f"  KEEP: {rname} ({rtype})")
        skipped += 1
        continue

    print(f"  DELETE: {rname} ({rtype})")
    del_url = urljoin(base_url, f"/config-dns/v2/zones/{ZONE}/names/{rname}/types/{rtype}")
    del_response = session.delete(del_url)

    if del_response.status_code in [200, 204]:
        print(f"    Deleted successfully.")
        deleted += 1
    else:
        print(f"    Failed: {del_response.status_code} - {del_response.text}")

print(f"\nCleanup complete: {deleted} deleted, {skipped} preserved.")
