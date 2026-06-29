#!/usr/bin/env python3
"""
Create the root federated block (10.0.0.0/8, tag owner=pdh) that a
Forward Looking Delegation carves from.

Idempotent: if a matching block already exists, it is left untouched.
This represents the address pool that "UDDI manages" — the foundation
the FLD demo allocates from.
"""

import os
import sys
import json
import requests

CSP_URL = os.getenv("BLOXONE_CSP_URL", "https://csp.infoblox.com").rstrip("/")
API_KEY = os.getenv("BLOXONE_API_KEY") or os.getenv("TF_VAR_ddi_api_key")

POOL_ADDRESS = "10.0.0.0"
POOL_CIDR = 8
POOL_NAME = "pdh-root-pool"
TAG_KEY = "owner"
TAG_VALUE = "pdh"

if not API_KEY:
    print("ERROR: set BLOXONE_API_KEY (or TF_VAR_ddi_api_key)", file=sys.stderr)
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

def main():
    # Idempotency: skip if a matching block already exists
    existing = ddi_get("federation/federated_block").get("results", []) or []
    for b in existing:
        tags = b.get("tags") or {}
        if (
            b.get("address") == POOL_ADDRESS
            and int(b.get("cidr", -1)) == POOL_CIDR
            and tags.get(TAG_KEY) == TAG_VALUE
        ):
            print(
                f"Federated block {POOL_ADDRESS}/{POOL_CIDR} "
                f"(tag {TAG_KEY}={TAG_VALUE}) already exists: {b.get('id')}"
            )
            return

    # Top-level federated blocks must be parented to a federated realm
    realms = ddi_get("federation/federated_realm").get("results", []) or []
    if not realms:
        raise RuntimeError("No federated realm found; cannot create federated block")
    realm_id = realms[0]["id"]
    print(f"Using federated realm: {realm_id}")

    body = {
        "address": POOL_ADDRESS,
        "cidr": POOL_CIDR,
        "federated_realm": realm_id,
        "name": POOL_NAME,
        "tags": {TAG_KEY: TAG_VALUE},
    }

    result = ddi_post("federation/federated_block", body)
    block = result.get("result", result)
    print(
        f"Created federated block: {block.get('address')}/{block.get('cidr')} "
        f"id={block.get('id')}"
    )
    print(json.dumps(block.get("tags", {}), indent=2))

if __name__ == "__main__":
    main()
