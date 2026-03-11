#!/usr/bin/env python3
"""
Deploy IPAM data (network containers, networks, fixed addresses, DHCP ranges) on NIOS via WAPI.

Paul's POC — Single GM managing the on-prem 10.1.0.0/16 space.
NIOS is authoritative for 10.1.0.0/16 only. Azure subnets discovered by UAI.
Azure 10.2.0.0/16 and 10.3.0.0/16 are discovered by UAI (not managed here).

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
# IPAM definitions — On-prem data center (10.1.0.0/16)
# ---------------------------

CONTAINERS = [
    {"network": "10.1.0.0/16", "comment": "On-prem data center — NIOS managed"},
]

NETWORKS = [
    # Server subnets
    {"network": "10.1.1.0/24", "comment": "DC — servers (web, app, db, mail, dns)"},
    {"network": "10.1.2.0/24", "comment": "DC — infrastructure (ftp, ntp, syslog)"},
    {"network": "10.1.3.0/24", "comment": "DC — authentication (ldap, radius, ad)"},
    # User subnets
    {"network": "10.1.20.0/24", "comment": "DC — workstations floor 1"},
    {"network": "10.1.21.0/24", "comment": "DC — workstations floor 2"},
    {"network": "10.1.22.0/24", "comment": "DC — workstations floor 3"},
    {"network": "10.1.25.0/24", "comment": "DC — VoIP phones"},
    {"network": "10.1.30.0/24", "comment": "DC — wireless corporate"},
    {"network": "10.1.31.0/24", "comment": "DC — wireless guest"},
    # Security / DMZ
    {"network": "10.1.5.0/24", "comment": "DC — DMZ (proxy, waf, lb)"},
    {"network": "10.1.6.0/24", "comment": "DC — security appliances (ids, fw)"},
    # Management
    {"network": "10.1.10.0/24", "comment": "DC — management (monitoring, logging, backup)"},
    {"network": "10.1.11.0/24", "comment": "DC — out-of-band management (iLO, iDRAC)"},
    # Dev / test
    {"network": "10.1.100.0/24", "comment": "DC — development"},
    {"network": "10.1.101.0/24", "comment": "DC — staging"},
    {"network": "10.1.102.0/24", "comment": "DC — QA testing"},
]

FIXED_ADDRS = [
    # Servers
    {"ipv4addr": "10.1.1.10", "mac": "00:50:56:01:01:10", "name": "web-srv01", "comment": "Web server"},
    {"ipv4addr": "10.1.1.20", "mac": "00:50:56:01:01:20", "name": "app-srv01", "comment": "App server"},
    {"ipv4addr": "10.1.1.30", "mac": "00:50:56:01:01:30", "name": "db-srv01", "comment": "Database server"},
    {"ipv4addr": "10.1.1.40", "mac": "00:50:56:01:01:40", "name": "mail-srv01", "comment": "Mail server"},
    {"ipv4addr": "10.1.1.50", "mac": "00:50:56:01:01:50", "name": "dns-srv01", "comment": "Primary DNS"},
    {"ipv4addr": "10.1.1.51", "mac": "00:50:56:01:01:51", "name": "dns-srv02", "comment": "Secondary DNS"},
    # Infrastructure
    {"ipv4addr": "10.1.2.10", "mac": "00:50:56:01:02:10", "name": "ftp-srv01", "comment": "FTP server"},
    {"ipv4addr": "10.1.2.11", "mac": "00:50:56:01:02:11", "name": "ntp-srv01", "comment": "NTP server"},
    {"ipv4addr": "10.1.2.12", "mac": "00:50:56:01:02:12", "name": "syslog-srv01", "comment": "Syslog server"},
    # Auth
    {"ipv4addr": "10.1.3.10", "mac": "00:50:56:01:03:10", "name": "ldap-srv01", "comment": "LDAP server"},
    {"ipv4addr": "10.1.3.20", "mac": "00:50:56:01:03:20", "name": "radius-srv01", "comment": "RADIUS server"},
    {"ipv4addr": "10.1.3.30", "mac": "00:50:56:01:03:30", "name": "ad-srv01", "comment": "Active Directory"},
    # DMZ
    {"ipv4addr": "10.1.5.10", "mac": "00:50:56:01:05:10", "name": "proxy-srv01", "comment": "Reverse proxy"},
    {"ipv4addr": "10.1.5.20", "mac": "00:50:56:01:05:20", "name": "waf-srv01", "comment": "Web app firewall"},
    {"ipv4addr": "10.1.5.30", "mac": "00:50:56:01:05:30", "name": "lb-srv01", "comment": "Load balancer"},
    # Security
    {"ipv4addr": "10.1.6.10", "mac": "00:50:56:01:06:10", "name": "ids-srv01", "comment": "IDS/IPS"},
    {"ipv4addr": "10.1.6.20", "mac": "00:50:56:01:06:20", "name": "fw-srv01", "comment": "Firewall mgmt"},
    # Management
    {"ipv4addr": "10.1.10.10", "mac": "00:50:56:0A:0A:10", "name": "switch-core", "comment": "Core switch"},
    {"ipv4addr": "10.1.10.50", "mac": "00:50:56:0A:0A:50", "name": "monitoring-srv01", "comment": "Monitoring"},
    {"ipv4addr": "10.1.10.51", "mac": "00:50:56:0A:0A:51", "name": "logging-srv01", "comment": "Logging"},
    {"ipv4addr": "10.1.10.60", "mac": "00:50:56:0A:0A:60", "name": "backup-srv01", "comment": "Backup server"},
    # OOB management
    {"ipv4addr": "10.1.11.1", "mac": "00:50:56:0B:0B:01", "name": "ilo-srv01", "comment": "Server 01 iLO"},
    {"ipv4addr": "10.1.11.2", "mac": "00:50:56:0B:0B:02", "name": "ilo-srv02", "comment": "Server 02 iLO"},
    {"ipv4addr": "10.1.11.3", "mac": "00:50:56:0B:0B:03", "name": "ilo-srv03", "comment": "Server 03 iLO"},
]

DHCP_RANGES = [
    {"start_addr": "10.1.20.100", "end_addr": "10.1.20.250", "comment": "Workstations floor 1"},
    {"start_addr": "10.1.21.100", "end_addr": "10.1.21.250", "comment": "Workstations floor 2"},
    {"start_addr": "10.1.22.100", "end_addr": "10.1.22.250", "comment": "Workstations floor 3"},
    {"start_addr": "10.1.25.100", "end_addr": "10.1.25.250", "comment": "VoIP phones"},
    {"start_addr": "10.1.30.50", "end_addr": "10.1.30.250", "comment": "Wireless corporate"},
    {"start_addr": "10.1.31.50", "end_addr": "10.1.31.250", "comment": "Wireless guest"},
    {"start_addr": "10.1.100.50", "end_addr": "10.1.100.200", "comment": "Development DHCP"},
    {"start_addr": "10.1.101.50", "end_addr": "10.1.101.200", "comment": "Staging DHCP"},
]


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


def create_object(gm_ip, wapi, obj_type, payload, label):
    r = wapi_post(gm_ip, wapi, obj_type, payload)
    if r.status_code == 201:
        log(label)
        return True
    elif r.status_code == 400 and "already exists" in r.text.lower():
        log(f"{label} (exists)")
        return True
    else:
        log(f"{label} — HTTP {r.status_code}: {r.text[:300]}", ok=False)
        return False


# ---------------------------
# Main
# ---------------------------

def main():
    print("=== Deploy IPAM Data — Paul's POC (On-Prem 10.1.0.0/16) ===")
    print(f"\n{'='*50}")
    print(f"  GM: {gm_ip}")
    print(f"{'='*50}")

    wapi = find_wapi_version(gm_ip)
    if not wapi:
        print("  Cannot connect to GM — skipping\n")
        sys.exit(1)

    print(f"\n  --- Network containers ---")
    for c in CONTAINERS:
        create_object(gm_ip, wapi, "networkcontainer", c,
                       f"Container {c['network']:18s} {c['comment']}")

    print(f"\n  --- Networks ---")
    for n in NETWORKS:
        create_object(gm_ip, wapi, "network", n,
                       f"Network   {n['network']:18s} {n['comment']}")

    print(f"\n  --- Fixed addresses ---")
    for fa in FIXED_ADDRS:
        create_object(gm_ip, wapi, "fixedaddress", fa,
                       f"Fixed     {fa['ipv4addr']:18s} {fa['name']}")

    print(f"\n  --- DHCP ranges ---")
    for dr in DHCP_RANGES:
        payload = {
            "start_addr": dr["start_addr"],
            "end_addr": dr["end_addr"],
            "comment": dr["comment"],
        }
        create_object(gm_ip, wapi, "range", payload,
                       f"Range     {dr['start_addr']} — {dr['end_addr']}  {dr['comment']}")

    print("\n=== IPAM deployment complete ===")


if __name__ == "__main__":
    main()
