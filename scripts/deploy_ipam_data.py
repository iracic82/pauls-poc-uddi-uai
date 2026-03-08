#!/usr/bin/env python3
"""
Deploy IPAM data (network containers, networks, fixed addresses, DHCP ranges) on NIOS via WAPI.

GM1 ($GM_IP)  -> 10.10.0.0/16 corporate space (correlated with test.com DNS)
GM2 ($GM2_IP) -> 172.16.0.0/16 branch space   (correlated with jag.com DNS)

All config from environment variables — no CLI args, no interactive input.
Required env vars: GM_IP, GM2_IP, TF_VAR_windows_admin_password
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
gm1_ip = os.getenv("GM_IP")
gm2_ip = os.getenv("GM2_IP")
password = os.getenv("TF_VAR_windows_admin_password")

if not gm1_ip or not gm2_ip:
    print("ERROR: GM_IP and GM2_IP must be set")
    sys.exit(1)

if not password:
    print("ERROR: TF_VAR_windows_admin_password must be set")
    sys.exit(1)

# ---------------------------
# IPAM definitions — GM1 (test.com / 10.10.x.x)
# ---------------------------

GM1_CONTAINERS = [
    {"network": "10.0.0.0/8", "comment": "Corporate address space"},
    {"network": "10.10.0.0/16", "comment": "test.com — all subnets"},
]

GM1_NETWORKS = [
    # Server subnets
    {"network": "10.10.1.0/24", "comment": "test.com — servers (web, app, db, mail, dns)"},
    {"network": "10.10.2.0/24", "comment": "test.com — infrastructure (ftp, ntp)"},
    {"network": "10.10.3.0/24", "comment": "test.com — authentication (ldap, radius)"},
    # User subnets
    {"network": "10.10.20.0/24", "comment": "test.com — workstations floor 1"},
    {"network": "10.10.21.0/24", "comment": "test.com — workstations floor 2"},
    {"network": "10.10.22.0/24", "comment": "test.com — workstations floor 3"},
    {"network": "10.10.25.0/24", "comment": "test.com — VoIP phones"},
    {"network": "10.10.30.0/24", "comment": "test.com — wireless corporate"},
    {"network": "10.10.31.0/24", "comment": "test.com — wireless guest"},
    # Security / DMZ
    {"network": "10.10.5.0/24", "comment": "test.com — DMZ (proxy, waf)"},
    {"network": "10.10.6.0/24", "comment": "test.com — security appliances"},
    # Management
    {"network": "10.10.10.0/24", "comment": "test.com — management (monitoring, logging, backup)"},
    {"network": "10.10.11.0/24", "comment": "test.com — out-of-band management (iLO, iDRAC)"},
    # Dev / test
    {"network": "10.10.100.0/24", "comment": "test.com — development"},
    {"network": "10.10.101.0/24", "comment": "test.com — staging"},
    {"network": "10.10.102.0/24", "comment": "test.com — QA testing"},
]

GM1_FIXED = [
    # Servers — correlated with DNS A records
    {"ipv4addr": "10.10.1.10", "mac": "00:50:56:01:01:10", "name": "www.test.com", "comment": "Web server"},
    {"ipv4addr": "10.10.1.20", "mac": "00:50:56:01:01:20", "name": "app.test.com", "comment": "App server"},
    {"ipv4addr": "10.10.1.30", "mac": "00:50:56:01:01:30", "name": "db.test.com", "comment": "Database server"},
    {"ipv4addr": "10.10.1.40", "mac": "00:50:56:01:01:40", "name": "mail.test.com", "comment": "Mail server"},
    {"ipv4addr": "10.10.1.50", "mac": "00:50:56:01:01:50", "name": "dns1.test.com", "comment": "Primary DNS"},
    {"ipv4addr": "10.10.1.51", "mac": "00:50:56:01:01:51", "name": "dns2.test.com", "comment": "Secondary DNS"},
    # Infrastructure
    {"ipv4addr": "10.10.2.10", "mac": "00:50:56:01:02:10", "name": "ftp.test.com", "comment": "FTP server"},
    {"ipv4addr": "10.10.2.11", "mac": "00:50:56:01:02:11", "name": "ntp.test.com", "comment": "NTP server"},
    # Auth
    {"ipv4addr": "10.10.3.10", "mac": "00:50:56:01:03:10", "name": "ldap.test.com", "comment": "LDAP server"},
    {"ipv4addr": "10.10.3.20", "mac": "00:50:56:01:03:20", "name": "radius.test.com", "comment": "RADIUS server"},
    # DMZ
    {"ipv4addr": "10.10.5.10", "mac": "00:50:56:01:05:10", "name": "proxy.test.com", "comment": "Reverse proxy"},
    {"ipv4addr": "10.10.5.20", "mac": "00:50:56:01:05:20", "name": "waf.test.com", "comment": "Web app firewall"},
    # Management
    {"ipv4addr": "10.10.10.1", "mac": "00:50:56:0A:0A:01", "name": "gw-mgmt.test.com", "comment": "Mgmt gateway"},
    {"ipv4addr": "10.10.10.10", "mac": "00:50:56:0A:0A:10", "name": "switch-core.test.com", "comment": "Core switch"},
    {"ipv4addr": "10.10.10.50", "mac": "00:50:56:0A:0A:50", "name": "monitoring.test.com", "comment": "Monitoring"},
    {"ipv4addr": "10.10.10.51", "mac": "00:50:56:0A:0A:51", "name": "logging.test.com", "comment": "Logging"},
    {"ipv4addr": "10.10.10.60", "mac": "00:50:56:0A:0A:60", "name": "backup.test.com", "comment": "Backup server"},
    # Network gear
    {"ipv4addr": "10.10.11.1", "mac": "00:50:56:0B:0B:01", "name": "ilo-srv01.test.com", "comment": "Server 01 iLO"},
    {"ipv4addr": "10.10.11.2", "mac": "00:50:56:0B:0B:02", "name": "ilo-srv02.test.com", "comment": "Server 02 iLO"},
    {"ipv4addr": "10.10.11.3", "mac": "00:50:56:0B:0B:03", "name": "ilo-srv03.test.com", "comment": "Server 03 iLO"},
]

GM1_RANGES = [
    {"start_addr": "10.10.20.100", "end_addr": "10.10.20.250", "comment": "Workstations floor 1"},
    {"start_addr": "10.10.21.100", "end_addr": "10.10.21.250", "comment": "Workstations floor 2"},
    {"start_addr": "10.10.22.100", "end_addr": "10.10.22.250", "comment": "Workstations floor 3"},
    {"start_addr": "10.10.25.100", "end_addr": "10.10.25.250", "comment": "VoIP phones"},
    {"start_addr": "10.10.30.50", "end_addr": "10.10.30.250", "comment": "Wireless corporate"},
    {"start_addr": "10.10.31.50", "end_addr": "10.10.31.250", "comment": "Wireless guest"},
    {"start_addr": "10.10.100.50", "end_addr": "10.10.100.200", "comment": "Development DHCP"},
    {"start_addr": "10.10.101.50", "end_addr": "10.10.101.200", "comment": "Staging DHCP"},
]

# ---------------------------
# IPAM definitions — GM2 (jag.com / 172.16.x.x)
# ---------------------------

GM2_CONTAINERS = [
    {"network": "172.16.0.0/12", "comment": "Branch office address space"},
    {"network": "172.16.0.0/16", "comment": "jag.com — all subnets"},
]

GM2_NETWORKS = [
    # Server subnets
    {"network": "172.16.1.0/24", "comment": "jag.com — servers (web, portal, mail, vpn, dns)"},
    {"network": "172.16.2.0/24", "comment": "jag.com — business apps (erp, crm, hr)"},
    {"network": "172.16.3.0/24", "comment": "jag.com — devops (wiki, git, ci)"},
    # User subnets
    {"network": "172.16.20.0/24", "comment": "jag.com — office A workstations"},
    {"network": "172.16.21.0/24", "comment": "jag.com — office B workstations"},
    {"network": "172.16.22.0/24", "comment": "jag.com — office C workstations"},
    {"network": "172.16.23.0/24", "comment": "jag.com — remote VPN clients"},
    {"network": "172.16.25.0/24", "comment": "jag.com — VoIP phones"},
    {"network": "172.16.30.0/24", "comment": "jag.com — wireless corporate"},
    {"network": "172.16.31.0/24", "comment": "jag.com — wireless guest"},
    {"network": "172.16.32.0/24", "comment": "jag.com — wireless IoT"},
    # Security / DMZ
    {"network": "172.16.5.0/24", "comment": "jag.com — DMZ (proxy, firewall)"},
    {"network": "172.16.6.0/24", "comment": "jag.com — IDS/IPS segment"},
    # Management
    {"network": "172.16.10.0/24", "comment": "jag.com — management (monitoring, logging, ntp)"},
    {"network": "172.16.11.0/24", "comment": "jag.com — out-of-band management"},
    # Dev / staging
    {"network": "172.16.100.0/24", "comment": "jag.com — development"},
    {"network": "172.16.101.0/24", "comment": "jag.com — staging"},
    {"network": "172.16.102.0/24", "comment": "jag.com — QA testing"},
    {"network": "172.16.103.0/24", "comment": "jag.com — sandbox"},
]

GM2_FIXED = [
    # Servers — correlated with DNS A records
    {"ipv4addr": "172.16.1.10", "mac": "00:50:56:AC:01:10", "name": "www.jag.com", "comment": "Web server"},
    {"ipv4addr": "172.16.1.20", "mac": "00:50:56:AC:01:20", "name": "portal.jag.com", "comment": "Portal"},
    {"ipv4addr": "172.16.1.30", "mac": "00:50:56:AC:01:30", "name": "mail.jag.com", "comment": "Mail server"},
    {"ipv4addr": "172.16.1.40", "mac": "00:50:56:AC:01:40", "name": "vpn.jag.com", "comment": "VPN gateway"},
    {"ipv4addr": "172.16.1.50", "mac": "00:50:56:AC:01:50", "name": "dns1.jag.com", "comment": "Primary DNS"},
    {"ipv4addr": "172.16.1.51", "mac": "00:50:56:AC:01:51", "name": "dns2.jag.com", "comment": "Secondary DNS"},
    # Business apps
    {"ipv4addr": "172.16.2.10", "mac": "00:50:56:AC:02:10", "name": "erp.jag.com", "comment": "ERP system"},
    {"ipv4addr": "172.16.2.20", "mac": "00:50:56:AC:02:20", "name": "crm.jag.com", "comment": "CRM system"},
    {"ipv4addr": "172.16.2.30", "mac": "00:50:56:AC:02:30", "name": "hr.jag.com", "comment": "HR portal"},
    # DevOps
    {"ipv4addr": "172.16.3.10", "mac": "00:50:56:AC:03:10", "name": "wiki.jag.com", "comment": "Wiki"},
    {"ipv4addr": "172.16.3.20", "mac": "00:50:56:AC:03:20", "name": "git.jag.com", "comment": "Git server"},
    {"ipv4addr": "172.16.3.30", "mac": "00:50:56:AC:03:30", "name": "ci.jag.com", "comment": "CI/CD server"},
    # DMZ
    {"ipv4addr": "172.16.5.10", "mac": "00:50:56:AC:05:10", "name": "proxy.jag.com", "comment": "Reverse proxy"},
    {"ipv4addr": "172.16.5.20", "mac": "00:50:56:AC:05:20", "name": "firewall.jag.com", "comment": "Firewall"},
    # Management
    {"ipv4addr": "172.16.10.1", "mac": "00:50:56:AC:0A:01", "name": "gw-mgmt.jag.com", "comment": "Mgmt gateway"},
    {"ipv4addr": "172.16.10.10", "mac": "00:50:56:AC:0A:10", "name": "switch-core.jag.com", "comment": "Core switch"},
    {"ipv4addr": "172.16.10.50", "mac": "00:50:56:AC:0A:50", "name": "monitoring.jag.com", "comment": "Monitoring"},
    {"ipv4addr": "172.16.10.51", "mac": "00:50:56:AC:0A:51", "name": "logging.jag.com", "comment": "Logging"},
    {"ipv4addr": "172.16.10.52", "mac": "00:50:56:AC:0A:52", "name": "ntp.jag.com", "comment": "NTP server"},
    # OOB management
    {"ipv4addr": "172.16.11.1", "mac": "00:50:56:AC:0B:01", "name": "ilo-srv01.jag.com", "comment": "Server 01 iLO"},
    {"ipv4addr": "172.16.11.2", "mac": "00:50:56:AC:0B:02", "name": "ilo-srv02.jag.com", "comment": "Server 02 iLO"},
    {"ipv4addr": "172.16.11.3", "mac": "00:50:56:AC:0B:03", "name": "ilo-srv03.jag.com", "comment": "Server 03 iLO"},
    {"ipv4addr": "172.16.11.4", "mac": "00:50:56:AC:0B:04", "name": "ilo-srv04.jag.com", "comment": "Server 04 iLO"},
]

GM2_RANGES = [
    {"start_addr": "172.16.20.100", "end_addr": "172.16.20.250", "comment": "Office A workstations"},
    {"start_addr": "172.16.21.100", "end_addr": "172.16.21.250", "comment": "Office B workstations"},
    {"start_addr": "172.16.22.100", "end_addr": "172.16.22.250", "comment": "Office C workstations"},
    {"start_addr": "172.16.23.50", "end_addr": "172.16.23.250", "comment": "Remote VPN clients"},
    {"start_addr": "172.16.25.100", "end_addr": "172.16.25.250", "comment": "VoIP phones"},
    {"start_addr": "172.16.30.50", "end_addr": "172.16.30.250", "comment": "Wireless corporate"},
    {"start_addr": "172.16.31.50", "end_addr": "172.16.31.250", "comment": "Wireless guest"},
    {"start_addr": "172.16.32.50", "end_addr": "172.16.32.200", "comment": "Wireless IoT"},
    {"start_addr": "172.16.100.50", "end_addr": "172.16.100.200", "comment": "Development DHCP"},
    {"start_addr": "172.16.101.50", "end_addr": "172.16.101.200", "comment": "Staging DHCP"},
    {"start_addr": "172.16.103.10", "end_addr": "172.16.103.200", "comment": "Sandbox DHCP"},
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
# Deploy logic
# ---------------------------

def deploy_gm(label, gm_ip, containers, networks, fixed_addrs, dhcp_ranges):
    print(f"\n{'='*50}")
    print(f"  {label}: {gm_ip}")
    print(f"{'='*50}")

    wapi = find_wapi_version(gm_ip)
    if not wapi:
        print(f"  Skipping {label} — cannot connect\n")
        return

    print(f"\n  --- Network containers ---")
    for c in containers:
        create_object(gm_ip, wapi, "networkcontainer", c,
                       f"Container {c['network']:18s} {c['comment']}")

    print(f"\n  --- Networks ---")
    for n in networks:
        create_object(gm_ip, wapi, "network", n,
                       f"Network   {n['network']:18s} {n['comment']}")

    print(f"\n  --- Fixed addresses ---")
    for fa in fixed_addrs:
        create_object(gm_ip, wapi, "fixedaddress", fa,
                       f"Fixed     {fa['ipv4addr']:18s} {fa['name']}")

    print(f"\n  --- DHCP ranges ---")
    for dr in dhcp_ranges:
        payload = {
            "start_addr": dr["start_addr"],
            "end_addr": dr["end_addr"],
            "comment": dr["comment"],
        }
        create_object(gm_ip, wapi, "range", payload,
                       f"Range     {dr['start_addr']} — {dr['end_addr']}  {dr['comment']}")

    print()


# ---------------------------
# Main
# ---------------------------

def main():
    print("=== Deploy IPAM Data on NIOS Grid Masters ===")

    deploy_gm("GM1 (test.com)", gm1_ip,
              GM1_CONTAINERS, GM1_NETWORKS, GM1_FIXED, GM1_RANGES)

    deploy_gm("GM2 (jag.com)", gm2_ip,
              GM2_CONTAINERS, GM2_NETWORKS, GM2_FIXED, GM2_RANGES)

    print("=== IPAM deployment complete ===")


if __name__ == "__main__":
    main()
