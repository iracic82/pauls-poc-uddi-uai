#!/usr/bin/env python3

import os
import sys
import json
import time
import requests

CSP_URL = os.getenv("BLOXONE_CSP_URL", "https://csp.infoblox.com").rstrip("/")
API_KEY = os.getenv("BLOXONE_API_KEY")

TARGET_ADDRESS = "10.0.0.0"
TARGET_CIDR = 8
TARGET_TAG_KEY = "owner"
TARGET_TAG_VALUE = "pdh"

FLD_CIDR = 16
FLD_COUNT = 1
FLD_NAME = f"fld-{TARGET_ADDRESS.replace('.', '-')}-{FLD_CIDR}-{int(time.time())}"

FLD_CIDR_FILE = os.getenv("FLD_CIDR_FILE", "/root/infoblox-lab/pauls-poc/fld_cidr.txt")

if not API_KEY:
    print("ERROR: set BLOXONE_API_KEY", file=sys.stderr)
    sys.exit(1)

session = requests.Session()
session.headers.update({
    "Authorization": f"Token {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
})

def ddi_get(path, params=None):
    url = f"{CSP_URL}/api/ddi/v1/{path.lstrip('/')}"
    r = session.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def ddi_post(path, body):
    url = f"{CSP_URL}/api/ddi/v1/{path.lstrip('/')}"
    r = session.post(url, json=body, timeout=30)
    r.raise_for_status()
    return r.json()

def find_matching_block():
    data = ddi_get("federation/federated_block")
    results = data.get("results", [])

    matches = []
    for block in results:
        tags = block.get("tags") or {}
        if (
            block.get("address") == TARGET_ADDRESS
            and int(block.get("cidr", -1)) == TARGET_CIDR
            and tags.get(TARGET_TAG_KEY) == TARGET_TAG_VALUE
        ):
            matches.append(block)

    if not matches:
        raise RuntimeError(
            f"No federated block found for {TARGET_ADDRESS}/{TARGET_CIDR} "
            f"with tag {TARGET_TAG_KEY}={TARGET_TAG_VALUE}"
        )

    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple federated blocks matched {TARGET_ADDRESS}/{TARGET_CIDR} "
            f"with tag {TARGET_TAG_KEY}={TARGET_TAG_VALUE}; refine the lookup"
        )

    return matches[0]

def create_next_available_fld():
    block = find_matching_block()

    body = {
        "count": FLD_COUNT,
        "cidr": FLD_CIDR,
        "name": FLD_NAME,
        "tags": {
            TARGET_TAG_KEY: TARGET_TAG_VALUE
        }
    }

    result = ddi_post("federation/create_next_available_fld", body)

    print("Matched federated block:")
    print(json.dumps({
        "id": block.get("id"),
        "address": block.get("address"),
        "cidr": block.get("cidr"),
        "federated_realm": block.get("federated_realm"),
        "tags": block.get("tags"),
    }, indent=2))

    print("\nFLD create response:")
    print(json.dumps(result, indent=2))

    # Extract the allocated CIDR and write it for downstream consumers (Terraform)
    fld_objects = result.get("results", result if isinstance(result, list) else [])
    if not fld_objects:
        print("WARNING: could not extract FLD objects from response", file=sys.stderr)
        return

    fld = fld_objects[0]
    allocated_cidr = f"{fld['address']}/{fld['cidr']}"

    os.makedirs(os.path.dirname(FLD_CIDR_FILE), exist_ok=True)
    with open(FLD_CIDR_FILE, "w") as f:
        f.write(allocated_cidr)

    print(f"\nFLD allocated CIDR: {allocated_cidr}")
    print(f"Written to: {FLD_CIDR_FILE}")

if __name__ == "__main__":
    create_next_available_fld()
