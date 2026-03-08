#!/usr/bin/env python3
"""
Fetches the default security policy from Infoblox CSP and clones it 3 times
(TD-Policy-1, TD-Policy-2, TD-Policy-3) for lab exercises.
Clones inherit all rules (threat feeds, custom lists) but not network scope
(DFPs, endpoint groups, user groups stay on the default catch-all policy).
"""

import os
import sys
import json
import requests

BASE_URL = "https://csp.infoblox.com"
POLICIES_ENDPOINT = f"{BASE_URL}/api/atcfw/v1/security_policies"

# Read-only and default-only fields to strip before cloning.
# Network scope (dfp_services, roaming_device_groups, user_groups) stays on
# the default policy since DFPs/groups are exclusive per non-default policy.
STRIP_FIELDS = {
    "id", "created_time", "updated_time", "policy_id", "is_default",
    "agents", "dfps", "migration_status", "scope_expr", "tags",
    "user_groups", "roaming_device_groups", "dfp_services",
    "net_address_dfps", "network_lists", "precedence", "description",
}

CLONE_CONFIGS = [
    {"name": "TD-Policy-1", "precedence": 1},
    {"name": "TD-Policy-2", "precedence": 2},
    {"name": "TD-Policy-3", "precedence": 3},
]


def get_api_key():
    api_key = os.environ.get("TF_VAR_ddi_api_key")
    if not api_key:
        print("ERROR: TF_VAR_ddi_api_key not set in environment.")
        sys.exit(1)
    return api_key


def fetch_default_policy(headers):
    print("Fetching security policies...")
    resp = requests.get(POLICIES_ENDPOINT, headers=headers)
    resp.raise_for_status()
    results = resp.json().get("results", [])

    for policy in results:
        if policy.get("is_default"):
            print(f"Found default policy: '{policy.get('name')}' (id={policy.get('id')})")
            return policy

    print("ERROR: No default security policy found.")
    sys.exit(1)


def clone_policy(headers, base_policy, name, precedence):
    payload = {k: v for k, v in base_policy.items() if k not in STRIP_FIELDS}
    payload["name"] = name
    payload["precedence"] = precedence
    payload["is_default"] = False
    payload["description"] = "Cloned from Default Global Policy for lab exercise"
    payload["user_groups"] = []
    payload["roaming_device_groups"] = []
    payload["dfp_services"] = []
    payload["network_lists"] = []
    payload["net_address_dfps"] = []

    print(f"Creating policy '{name}' with precedence {precedence}...")
    resp = requests.post(POLICIES_ENDPOINT, headers=headers, json=payload)
    if resp.status_code == 409:
        print(f"  Policy '{name}' already exists, skipping.")
        return None
    resp.raise_for_status()
    result = resp.json().get("results", resp.json())
    print(f"  Created successfully (id={result.get('id', 'n/a')})")
    return result


def main():
    api_key = get_api_key()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {api_key}",
    }

    default_policy = fetch_default_policy(headers)

    for config in CLONE_CONFIGS:
        clone_policy(headers, default_policy, config["name"], config["precedence"])

    # Verify final state
    print("\nFinal policy list:")
    resp = requests.get(POLICIES_ENDPOINT, headers=headers)
    resp.raise_for_status()
    for p in sorted(resp.json()["results"], key=lambda x: x["precedence"]):
        default = " (DEFAULT)" if p.get("is_default") else ""
        rules = len(p.get("rules", []))
        print(f"  prec={p['precedence']}  name='{p['name']}'{default}  rules={rules}")

    print("\nDone.")


if __name__ == "__main__":
    main()
