#!/usr/bin/env python3
"""
Configure the Grid Master member's DNS Resolver on NIOS via WAPI.

Mirrors Grid Properties Editor > DNS Resolver:
  - Enable DNS Resolver
  - Name Servers (upstream resolvers used by the appliance itself)
  - Search List

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


def put_member(gm_ip, wapi, ref, payload):
    return requests.put(
        f"https://{gm_ip}/wapi/{wapi}/{ref}",
        auth=(USERNAME, password), json=payload, verify=False, timeout=20,
    )


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

    ref = get_member_ref(gm_ip, wapi, member_name)
    if not ref:
        sys.exit(1)
    log(f"Member ref: {ref}")

    # NIOS member uses `use_dns_resolver_setting` (override-grid-default flag),
    # NOT `enable_dns_resolver` — the GUI "Enable DNS Resolver" checkbox maps to this.
    payload = {
        "use_dns_resolver_setting": True,
        "dns_resolver_setting": {
            "resolvers": RESOLVERS,
            "search_domains": SEARCH_DOMAINS,
        },
    }

    r = put_member(gm_ip, wapi, ref, payload)
    if r.status_code == 200:
        log("DNS Resolver configured")
    else:
        log(f"PUT failed — HTTP {r.status_code}: {r.text[:400]}", ok=False)
        sys.exit(1)

    # Read-back verification
    rb = requests.get(
        f"https://{gm_ip}/wapi/{wapi}/{ref}",
        params={"_return_fields": "host_name,use_dns_resolver_setting,dns_resolver_setting"},
        auth=(USERNAME, password), verify=False, timeout=15,
    )
    if rb.status_code == 200:
        data = rb.json()
        enabled = data.get("use_dns_resolver_setting")
        setting = data.get("dns_resolver_setting") or {}
        log(f"Verify: use_dns_resolver_setting={enabled}, "
            f"resolvers={setting.get('resolvers')}, "
            f"search_domains={setting.get('search_domains')}")
    else:
        log(f"Read-back failed — HTTP {rb.status_code}", ok=False)

    print("\n=== Resolver configuration complete ===")


if __name__ == "__main__":
    main()
