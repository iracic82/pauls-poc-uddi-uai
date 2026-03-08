#!/usr/bin/env python3
"""
Deploy DNS zones and records on both NIOS Grid Masters via WAPI.

GM1 ($GM_IP)  -> test.com  (zone + A, CNAME, MX, TXT records)
GM2 ($GM2_IP) -> jag.com   (zone + A, CNAME, MX, TXT records)

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
# Zone and record definitions
# ---------------------------

GM1_ZONE = "test.com"
GM1_RECORDS = {
    "record:a": [
        {"name": "www.test.com", "ipv4addr": "10.10.1.10"},
        {"name": "app.test.com", "ipv4addr": "10.10.1.20"},
        {"name": "db.test.com", "ipv4addr": "10.10.1.30"},
        {"name": "mail.test.com", "ipv4addr": "10.10.1.40"},
        {"name": "dns1.test.com", "ipv4addr": "10.10.1.50"},
        {"name": "dns2.test.com", "ipv4addr": "10.10.1.51"},
        {"name": "ftp.test.com", "ipv4addr": "10.10.2.10"},
        {"name": "ntp.test.com", "ipv4addr": "10.10.2.11"},
        {"name": "ldap.test.com", "ipv4addr": "10.10.3.10"},
        {"name": "radius.test.com", "ipv4addr": "10.10.3.20"},
        {"name": "monitoring.test.com", "ipv4addr": "10.10.10.50"},
        {"name": "logging.test.com", "ipv4addr": "10.10.10.51"},
        {"name": "backup.test.com", "ipv4addr": "10.10.10.60"},
        {"name": "proxy.test.com", "ipv4addr": "10.10.5.10"},
        {"name": "waf.test.com", "ipv4addr": "10.10.5.20"},
    ],
    "record:cname": [
        {"name": "web.test.com", "canonical": "www.test.com"},
        {"name": "api.test.com", "canonical": "app.test.com"},
        {"name": "smtp.test.com", "canonical": "mail.test.com"},
        {"name": "imap.test.com", "canonical": "mail.test.com"},
        {"name": "grafana.test.com", "canonical": "monitoring.test.com"},
        {"name": "syslog.test.com", "canonical": "logging.test.com"},
    ],
    "record:mx": [
        {"name": "test.com", "mail_exchanger": "mail.test.com", "preference": 10},
    ],
    "record:txt": [
        {"name": "test.com", "text": "v=spf1 mx ip4:10.10.1.0/24 -all"},
        {"name": "_dmarc.test.com", "text": "v=DMARC1; p=reject; rua=mailto:admin@test.com"},
    ],
}

GM2_ZONE = "jag.com"
GM2_RECORDS = {
    "record:a": [
        {"name": "www.jag.com", "ipv4addr": "172.16.1.10"},
        {"name": "portal.jag.com", "ipv4addr": "172.16.1.20"},
        {"name": "mail.jag.com", "ipv4addr": "172.16.1.30"},
        {"name": "vpn.jag.com", "ipv4addr": "172.16.1.40"},
        {"name": "dns1.jag.com", "ipv4addr": "172.16.1.50"},
        {"name": "dns2.jag.com", "ipv4addr": "172.16.1.51"},
        {"name": "erp.jag.com", "ipv4addr": "172.16.2.10"},
        {"name": "crm.jag.com", "ipv4addr": "172.16.2.20"},
        {"name": "hr.jag.com", "ipv4addr": "172.16.2.30"},
        {"name": "wiki.jag.com", "ipv4addr": "172.16.3.10"},
        {"name": "git.jag.com", "ipv4addr": "172.16.3.20"},
        {"name": "ci.jag.com", "ipv4addr": "172.16.3.30"},
        {"name": "monitoring.jag.com", "ipv4addr": "172.16.10.50"},
        {"name": "logging.jag.com", "ipv4addr": "172.16.10.51"},
        {"name": "ntp.jag.com", "ipv4addr": "172.16.10.52"},
        {"name": "proxy.jag.com", "ipv4addr": "172.16.5.10"},
        {"name": "firewall.jag.com", "ipv4addr": "172.16.5.20"},
    ],
    "record:cname": [
        {"name": "www2.jag.com", "canonical": "www.jag.com"},
        {"name": "webmail.jag.com", "canonical": "mail.jag.com"},
        {"name": "smtp.jag.com", "canonical": "mail.jag.com"},
        {"name": "imap.jag.com", "canonical": "mail.jag.com"},
        {"name": "grafana.jag.com", "canonical": "monitoring.jag.com"},
        {"name": "syslog.jag.com", "canonical": "logging.jag.com"},
        {"name": "jenkins.jag.com", "canonical": "ci.jag.com"},
    ],
    "record:mx": [
        {"name": "jag.com", "mail_exchanger": "mail.jag.com", "preference": 10},
    ],
    "record:txt": [
        {"name": "jag.com", "text": "v=spf1 mx ip4:172.16.1.0/24 -all"},
        {"name": "_dmarc.jag.com", "text": "v=DMARC1; p=quarantine; rua=mailto:admin@jag.com"},
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
# Deploy logic
# ---------------------------

def create_zone(gm_ip, wapi, fqdn):
    r = wapi_post(gm_ip, wapi, "zone_auth", {"fqdn": fqdn})
    if r.status_code == 201:
        log(f"Zone created: {fqdn}")
        return True
    elif r.status_code == 400 and "already exists" in r.text.lower():
        log(f"Zone already exists: {fqdn}")
        return True
    else:
        log(f"Zone {fqdn} — HTTP {r.status_code}: {r.text[:300]}", ok=False)
        return False


def create_records(gm_ip, wapi, records):
    for record_type, entries in records.items():
        for payload in entries:
            name = payload.get("name", "?")
            r = wapi_post(gm_ip, wapi, record_type, payload)
            if r.status_code == 201:
                log(f"{record_type:15s} {name}")
            elif r.status_code == 400 and "already exists" in r.text.lower():
                log(f"{record_type:15s} {name} (exists)")
            else:
                log(f"{record_type:15s} {name} — HTTP {r.status_code}: {r.text[:200]}", ok=False)


def deploy_gm(label, gm_ip, zone, records):
    print(f"\n{'='*50}")
    print(f"  {label}: {gm_ip} -> {zone}")
    print(f"{'='*50}\n")

    wapi = find_wapi_version(gm_ip)
    if not wapi:
        print(f"  Skipping {label} — cannot connect\n")
        return

    print(f"\n  --- Zone ---")
    if not create_zone(gm_ip, wapi, zone):
        print(f"  Skipping records — zone creation failed\n")
        return

    print(f"\n  --- Records ---")
    create_records(gm_ip, wapi, records)
    print()


# ---------------------------
# Main
# ---------------------------

def main():
    print("=== Deploy DNS Zones on NIOS Grid Masters ===")

    deploy_gm("GM1", gm1_ip, GM1_ZONE, GM1_RECORDS)
    deploy_gm("GM2", gm2_ip, GM2_ZONE, GM2_RECORDS)

    print("=== DNS deployment complete ===")


if __name__ == "__main__":
    main()
