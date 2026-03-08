#!/usr/bin/env python3
"""
Enable/Disable Cloud Grid Management (NIOS Management) via WAPI enable_federation field.
Usage:
  python3 enable_nios_management.py --gm <IP> --password <pass> --on
  python3 enable_nios_management.py --gm <IP> --password <pass> --off
  python3 enable_nios_management.py --gm <IP> --password <pass> --status
"""

import requests
import urllib3
import argparse
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WAPI_VERSIONS = ["v2.14", "v2.13.1", "v2.13", "v2.12"]


def find_wapi_version(gm_ip, username, password):
    """Try WAPI versions and return the highest supported one"""
    for v in WAPI_VERSIONS:
        try:
            r = requests.get(
                f"https://{gm_ip}/wapi/{v}/grid",
                auth=(username, password),
                verify=False,
                timeout=10
            )
            if r.status_code == 200:
                print(f"WAPI version: {v}")
                return v
        except Exception:
            continue
    print("ERROR: Could not connect to WAPI")
    sys.exit(1)


def get_grid_ref(gm_ip, username, password, wapi_version):
    r = requests.get(
        f"https://{gm_ip}/wapi/{wapi_version}/grid",
        auth=(username, password),
        verify=False,
        timeout=10
    )
    r.raise_for_status()
    return r.json()[0]['_ref']


def get_status(gm_ip, username, password, wapi_version):
    r = requests.get(
        f"https://{gm_ip}/wapi/{wapi_version}/grid",
        params={"_return_fields": "enable_federation"},
        auth=(username, password),
        verify=False,
        timeout=10
    )
    if r.status_code == 200:
        data = r.json()[0]
        val = data.get('enable_federation', 'field not available')
        print(f"enable_federation: {val}")
        return val
    else:
        print(f"Could not read enable_federation: HTTP {r.status_code}")
        print(r.text)
        return None


def set_federation(gm_ip, username, password, wapi_version, enable):
    grid_ref = get_grid_ref(gm_ip, username, password, wapi_version)
    print(f"Grid: {grid_ref}")

    r = requests.put(
        f"https://{gm_ip}/wapi/{wapi_version}/{grid_ref}",
        auth=(username, password),
        json={"enable_federation": enable},
        verify=False,
        timeout=10
    )
    if r.status_code == 200:
        state = "ENABLED" if enable else "DISABLED"
        print(f"Cloud Grid Management: {state}")
    else:
        print(f"ERROR: HTTP {r.status_code}")
        print(r.text)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Enable/Disable NIOS Cloud Grid Management')
    parser.add_argument('--gm', required=True, help='Grid Master IP')
    parser.add_argument('--user', default='admin', help='WAPI username (default: admin)')
    parser.add_argument('--password', required=True, help='WAPI password')
    parser.add_argument('--wapi', default=None, help='WAPI version (auto-detect if not set)')

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--on', action='store_true', help='Enable Cloud Grid Management')
    action.add_argument('--off', action='store_true', help='Disable Cloud Grid Management')
    action.add_argument('--status', action='store_true', help='Check current status')

    args = parser.parse_args()

    wapi = args.wapi or find_wapi_version(args.gm, args.user, args.password)

    if args.status:
        get_status(args.gm, args.user, args.password, wapi)
    elif args.on:
        set_federation(args.gm, args.user, args.password, wapi, True)
    elif args.off:
        set_federation(args.gm, args.user, args.password, wapi, False)


if __name__ == "__main__":
    main()
