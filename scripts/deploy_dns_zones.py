#!/usr/bin/env python3
"""
Deploy DNS zone and records on NIOS Grid Master via WAPI.

Paul's POC — Single GM with datacenter.local zone for on-prem 10.1.x.x hosts.
UDDI manages 10.0.0.0/8. Azure 10.2/10.3 discovered by UAI separately.

Required env vars: GM_IP, TF_VAR_windows_admin_password
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

# ---------------------------
# Zone and record definitions
# ---------------------------

ZONE = "datacenter.local"

RECORDS = {
    "record:a": [
        # Servers (10.1.1.0/24)
        {"name": "www.datacenter.local", "ipv4addr": "10.1.1.10"},
        {"name": "app.datacenter.local", "ipv4addr": "10.1.1.20"},
        {"name": "db.datacenter.local", "ipv4addr": "10.1.1.30"},
        {"name": "mail.datacenter.local", "ipv4addr": "10.1.1.40"},
        {"name": "dns1.datacenter.local", "ipv4addr": "10.1.1.50"},
        {"name": "dns2.datacenter.local", "ipv4addr": "10.1.1.51"},
        # Infrastructure (10.1.2.0/24)
        {"name": "ftp.datacenter.local", "ipv4addr": "10.1.2.10"},
        {"name": "ntp.datacenter.local", "ipv4addr": "10.1.2.11"},
        {"name": "syslog.datacenter.local", "ipv4addr": "10.1.2.12"},
        # Auth (10.1.3.0/24)
        {"name": "ldap.datacenter.local", "ipv4addr": "10.1.3.10"},
        {"name": "radius.datacenter.local", "ipv4addr": "10.1.3.20"},
        {"name": "ad.datacenter.local", "ipv4addr": "10.1.3.30"},
        # DMZ (10.1.5.0/24)
        {"name": "proxy.datacenter.local", "ipv4addr": "10.1.5.10"},
        {"name": "waf.datacenter.local", "ipv4addr": "10.1.5.20"},
        {"name": "lb.datacenter.local", "ipv4addr": "10.1.5.30"},
        # Security (10.1.6.0/24)
        {"name": "ids.datacenter.local", "ipv4addr": "10.1.6.10"},
        {"name": "fw.datacenter.local", "ipv4addr": "10.1.6.20"},
        # Management (10.1.10.0/24)
        {"name": "switch-core.datacenter.local", "ipv4addr": "10.1.10.10"},
        {"name": "monitoring.datacenter.local", "ipv4addr": "10.1.10.50"},
        {"name": "logging.datacenter.local", "ipv4addr": "10.1.10.51"},
        {"name": "backup.datacenter.local", "ipv4addr": "10.1.10.60"},
    ],
    "record:cname": [
        {"name": "web.datacenter.local", "canonical": "www.datacenter.local"},
        {"name": "api.datacenter.local", "canonical": "app.datacenter.local"},
        {"name": "smtp.datacenter.local", "canonical": "mail.datacenter.local"},
        {"name": "grafana.datacenter.local", "canonical": "monitoring.datacenter.local"},
    ],
}


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


def wapi_post(gm_ip, wapi, path, payload):
    return requests.post(
        f"https://{gm_ip}/wapi/{wapi}/{path}",
        auth=(USERNAME, password), json=payload, verify=False, timeout=15,
    )


# ---------------------------
# Main
# ---------------------------

def main():
    print(f"=== Deploy DNS Zone — Paul's POC ({ZONE}) ===")
    print(f"\n{'='*50}")
    print(f"  GM: {gm_ip} -> {ZONE}")
    print(f"{'='*50}\n")

    wapi = find_wapi_version(gm_ip)
    if not wapi:
        print("  Cannot connect to GM — skipping\n")
        sys.exit(1)

    # Create zone
    print(f"  --- Zone ---")
    r = wapi_post(gm_ip, wapi, "zone_auth", {"fqdn": ZONE})
    if r.status_code == 201:
        log(f"Zone created: {ZONE}")
    elif r.status_code == 400 and "already exists" in r.text.lower():
        log(f"Zone already exists: {ZONE}")
    else:
        log(f"Zone {ZONE} — HTTP {r.status_code}: {r.text[:300]}", ok=False)
        print("  Skipping records — zone creation failed\n")
        sys.exit(1)

    # Create records
    print(f"\n  --- Records ---")
    for record_type, entries in RECORDS.items():
        for payload in entries:
            name = payload.get("name", "?")
            r = wapi_post(gm_ip, wapi, record_type, payload)
            if r.status_code == 201:
                log(f"{record_type:15s} {name}")
            elif r.status_code == 400 and "already exists" in r.text.lower():
                log(f"{record_type:15s} {name} (exists)")
            else:
                log(f"{record_type:15s} {name} — HTTP {r.status_code}: {r.text[:200]}", ok=False)

    print("\n=== DNS deployment complete ===")


if __name__ == "__main__":
    main()
