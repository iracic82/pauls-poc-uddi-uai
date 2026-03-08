#!/usr/bin/env python3
"""
Deletes the TD-Policy-1, TD-Policy-2, TD-Policy-3 security policies.
Before deletion, removes any DFP associations to avoid 403 errors.
Skips the Default Global Policy and any other non-TD policies.
"""

import os
import sys
import json
import requests

BASE_URL = "https://csp.infoblox.com"
POLICIES_ENDPOINT = f"{BASE_URL}/api/atcfw/v1/security_policies"

TD_POLICY_NAMES = {"TD-Policy-1", "TD-Policy-2", "TD-Policy-3"}

# Read-only fields to strip when updating a policy via PUT
READONLY_FIELDS = {
    "id", "created_time", "updated_time", "is_default",
    "agents", "dfps", "migration_status", "scope_expr", "tags",
}


def get_api_key():
    api_key = os.environ.get("TF_VAR_ddi_api_key")
    if not api_key:
        print("ERROR: TF_VAR_ddi_api_key not set in environment.")
        sys.exit(1)
    return api_key


def main():
    api_key = get_api_key()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {api_key}",
    }

    print("Fetching security policies...")
    resp = requests.get(POLICIES_ENDPOINT, headers=headers)
    resp.raise_for_status()

    td_policies = [p for p in resp.json()["results"] if p["name"] in TD_POLICY_NAMES]

    if not td_policies:
        print("No TD-Policies found. Nothing to delete.")
        return

    # Remove DFP/scope associations first to avoid 403 on delete
    for p in td_policies:
        if p.get("dfp_services") or p.get("roaming_device_groups") or p.get("network_lists"):
            print(f"Clearing scope from '{p['name']}' (id={p['id']})...")
            payload = {k: v for k, v in p.items() if k not in READONLY_FIELDS}
            payload["dfp_services"] = []
            payload["dfps"] = []
            payload["network_lists"] = []
            payload["roaming_device_groups"] = []
            payload["user_groups"] = []
            payload["net_address_dfps"] = []
            r = requests.put(f"{POLICIES_ENDPOINT}/{p['id']}", headers=headers, json=payload)
            r.raise_for_status()

    # Delete all TD policies
    ids = [p["id"] for p in td_policies]
    names = [p["name"] for p in td_policies]
    print(f"Deleting {', '.join(names)} (ids={ids})...")
    resp = requests.delete(POLICIES_ENDPOINT, headers=headers, json={"ids": ids})
    resp.raise_for_status()
    print("Deleted successfully.")

    # Verify
    print("\nRemaining policies:")
    resp = requests.get(POLICIES_ENDPOINT, headers=headers)
    resp.raise_for_status()
    for p in sorted(resp.json()["results"], key=lambda x: x["precedence"]):
        default = " (DEFAULT)" if p.get("is_default") else ""
        print(f"  prec={p['precedence']}  name='{p['name']}'{default}")

    print("\nDone.")


if __name__ == "__main__":
    main()
