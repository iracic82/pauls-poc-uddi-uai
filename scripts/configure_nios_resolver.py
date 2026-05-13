#!/usr/bin/env python3
"""
Configure the Grid-level DNS Resolver on NIOS via WAPI.

Mirrors Grid Properties Editor > DNS Resolver:
  - Enable DNS Resolver
  - Name Servers (upstream resolvers used by the appliance itself)
  - Search List

The setting is written on the `grid` object so it shows up in the Grid Properties
Editor and is inherited by all members. Any pre-existing member-level override
(`use_dns_resolver_setting=true` on the GM) is cleared first so the grid value
actually takes effect.

Paul's POC — single-GM grid. The resolver must be set BEFORE the GM joins CSP,
since the CSP hostname is resolved via this resolver.

Required env vars: GM_IP, TF_VAR_windows_admin_password
Optional env vars:
  DNS_RESOLVERS         comma-separated (default: 52.119.41.100)
  DNS_SEARCH_DOMAINS    comma-separated (default: empty)
  GM_MEMBER_NAME        member host_name (default: infoblox.localdomain)
"""

import os
import sys
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WAPI_VERSIONS = ["v2.14", "v2.13.1", "v2.13", "v2.12"]
USERNAME = "admin"

# ---------------------------
# Environment variables
# ---------------------------
gm_ip = os.getenv("GM_IP")
password = os.getenv("TF_VAR_windows_admin_password")

if not gm_ip:
    print("ERROR: GM_IP must be set")
    sys.exit(1)

if not password:
    print("ERROR: TF_VAR_windows_admin_password must be set")
    sys.exit(1)

resolvers_raw = os.getenv("DNS_RESOLVERS", "52.119.41.100")
search_raw = os.getenv("DNS_SEARCH_DOMAINS", "")
member_name = os.getenv("GM_MEMBER_NAME", "infoblox.localdomain")

RESOLVERS = [s.strip() for s in resolvers_raw.split(",") if s.strip()]
SEARCH_DOMAINS = [s.strip() for s in search_raw.split(",") if s.strip()]


# ---------------------------
# WAPI helpers
# ---------------------------

def log(msg, ok=True):
    tag = "OK" if ok else "FAIL"
    print(f"  [{tag}] {msg}")


def find_wapi_version(gm_ip):
    auth = (USERNAME, password)
    for v in WAPI_VERSIONS:
        try:
            r = requests.get(
                f"https://{gm_ip}/wapi/{v}/grid",
                auth=auth, verify=False, timeout=10,
            )
            if r.status_code == 200:
                log(f"WAPI version: {v}")
                return v
            elif r.status_code in (401, 403):
                log(f"Auth failed — HTTP {r.status_code}", ok=False)
                return None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            continue
    log("No supported WAPI version", ok=False)
    return None


def get_member_ref(gm_ip, wapi, host_name):
    r = requests.get(
        f"https://{gm_ip}/wapi/{wapi}/member",
        params={"host_name": host_name, "_return_fields": "host_name"},
        auth=(USERNAME, password), verify=False, timeout=15,
    )
    if r.status_code != 200:
        log(f"GET /member HTTP {r.status_code}: {r.text[:200]}", ok=False)
        return None
    rows = r.json()
    if not rows:
        # Fall back: take the first member in the grid
        r = requests.get(
            f"https://{gm_ip}/wapi/{wapi}/member",
            params={"_return_fields": "host_name"},
            auth=(USERNAME, password), verify=False, timeout=15,
        )
        rows = r.json() if r.status_code == 200 else []
        if not rows:
            log("No members found in grid", ok=False)
            return None
        log(f"host_name '{host_name}' not found — using first member '{rows[0].get('host_name')}'")
    return rows[0]["_ref"]


def put_ref(gm_ip, wapi, ref, payload):
    return requests.put(
        f"https://{gm_ip}/wapi/{wapi}/{ref}",
        auth=(USERNAME, password), json=payload, verify=False, timeout=20,
    )


def get_grid_ref(gm_ip, wapi):
    r = requests.get(
        f"https://{gm_ip}/wapi/{wapi}/grid",
        auth=(USERNAME, password), verify=False, timeout=15,
    )
    if r.status_code != 200 or not r.json():
        log(f"GET /grid HTTP {r.status_code}: {r.text[:200]}", ok=False)
        return None
    return r.json()[0]["_ref"]


def clear_member_override(gm_ip, wapi, member_ref):
    """Reset member back to inheriting the grid-level resolver setting."""
    r = put_ref(gm_ip, wapi, member_ref, {"use_dns_resolver_setting": False})
    if r.status_code == 200:
        log("Cleared member-level resolver override (inheriting grid)")
        return True
    log(f"Could not clear member override — HTTP {r.status_code}: {r.text[:200]}", ok=False)
    return False


# ---------------------------
# Main
# ---------------------------

def main():
    print("=== Configure NIOS Grid Resolver — Paul's POC ===")
    print(f"\n{'='*50}")
    print(f"  GM:             {gm_ip}")
    print(f"  Member:         {member_name}")
    print(f"  Resolvers:      {RESOLVERS}")
    print(f"  Search domains: {SEARCH_DOMAINS or '(none)'}")
    print(f"{'='*50}")

    if not RESOLVERS:
        log("DNS_RESOLVERS resolved to an empty list — refusing to clear resolvers", ok=False)
        sys.exit(1)

    wapi = find_wapi_version(gm_ip)
    if not wapi:
        print("  Cannot connect to GM — skipping\n")
        sys.exit(1)

    # --- 1) Clear any existing member-level override so the grid setting wins. ---
    member_ref = get_member_ref(gm_ip, wapi, member_name)
    if not member_ref:
        sys.exit(1)
    log(f"Member ref: {member_ref}")
    clear_member_override(gm_ip, wapi, member_ref)

    # --- 2) Write the resolver at the grid level (visible in Grid Properties Editor). ---
    grid_ref = get_grid_ref(gm_ip, wapi)
    if not grid_ref:
        sys.exit(1)
    log(f"Grid ref:   {grid_ref}")

    grid_payload = {
        "dns_resolver_setting": {
            "resolvers": RESOLVERS,
            "search_domains": SEARCH_DOMAINS,
        }
    }
    r = put_ref(gm_ip, wapi, grid_ref, grid_payload)
    if r.status_code != 200:
        log(f"Grid PUT failed — HTTP {r.status_code}: {r.text[:400]}", ok=False)
        sys.exit(1)
    log("Grid DNS Resolver configured")

    # --- 3) Read-back verification on grid. ---
    rb = requests.get(
        f"https://{gm_ip}/wapi/{wapi}/{grid_ref}",
        params={"_return_fields": "dns_resolver_setting"},
        auth=(USERNAME, password), verify=False, timeout=15,
    )
    if rb.status_code == 200:
        setting = (rb.json()[0] if isinstance(rb.json(), list) else rb.json()).get("dns_resolver_setting") or {}
        log(f"Verify grid: resolvers={setting.get('resolvers')}, "
            f"search_domains={setting.get('search_domains')}")
    else:
        log(f"Grid read-back failed — HTTP {rb.status_code}", ok=False)

    print("\n=== Resolver configuration complete ===")


if __name__ == "__main__":
    main()
