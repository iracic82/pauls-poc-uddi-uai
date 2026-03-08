#!/usr/bin/env python3
"""
Set Infoblox CSP Join Token via WAPI
Connects Grid Master to Infoblox Portal
"""

import requests
import urllib3
import sys
import os
import argparse

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def read_join_token(token_file: str) -> str:
    """Read join token from file"""
    with open(token_file, 'r') as f:
        return f.read().strip()


def get_grid_ref(gm_ip: str, username: str, password: str, wapi_version: str = "v2.12") -> str:
    """Get the grid object reference"""
    url = f"https://{gm_ip}/wapi/{wapi_version}/grid"

    response = requests.get(
        url,
        auth=(username, password),
        verify=False
    )
    response.raise_for_status()
    grid_objects = response.json()

    if not grid_objects:
        raise Exception("No grid object found")

    return grid_objects[0]['_ref']


def get_csp_grid_setting(gm_ip: str, username: str, password: str, wapi_version: str = "v2.12") -> dict:
    """Get current CSP grid setting via grid object"""
    url = f"https://{gm_ip}/wapi/{wapi_version}/grid"
    params = {
        "_return_fields": "csp_grid_setting"
    }

    response = requests.get(
        url,
        auth=(username, password),
        params=params,
        verify=False
    )
    response.raise_for_status()
    return response.json()


def set_csp_join_token(gm_ip: str, username: str, password: str, join_token: str, wapi_version: str = "v2.12") -> dict:
    """Set the CSP join token on the Grid Master via grid object"""

    # Get the grid object reference
    grid_ref = get_grid_ref(gm_ip, username, password, wapi_version)
    print(f"Found Grid: {grid_ref}")

    # Update with the join token via csp_grid_setting sub-object
    url = f"https://{gm_ip}/wapi/{wapi_version}/{grid_ref}"

    payload = {
        "csp_grid_setting": {
            "csp_join_token": join_token
        }
    }

    response = requests.put(
        url,
        auth=(username, password),
        json=payload,
        verify=False
    )
    response.raise_for_status()
    return response.json()


def get_csp_status(gm_ip: str, username: str, password: str, wapi_version: str = "v2.12") -> dict:
    """Get current CSP connection status with all fields"""
    url = f"https://{gm_ip}/wapi/{wapi_version}/grid"
    params = {
        "_return_fields": "csp_grid_setting"
    }

    response = requests.get(
        url,
        auth=(username, password),
        params=params,
        verify=False
    )
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description='Set Infoblox CSP Join Token')
    parser.add_argument('--gm', required=True, help='Grid Master IP or hostname')
    parser.add_argument('--user', default='admin', help='WAPI username (default: admin)')
    parser.add_argument('--password', required=True, help='WAPI password')
    parser.add_argument('--token-file', default='join_token.txt', help='Path to join token file')
    parser.add_argument('--wapi-version', default='v2.12', help='WAPI version (default: v2.12)')
    parser.add_argument('--status-only', action='store_true', help='Only check status, do not set token')

    args = parser.parse_args()

    # Check token file exists
    if not args.status_only and not os.path.exists(args.token_file):
        print(f"ERROR: Token file not found: {args.token_file}")
        sys.exit(1)

    try:
        if args.status_only:
            print(f"Checking CSP status on {args.gm}...")
            status = get_csp_status(args.gm, args.user, args.password, args.wapi_version)
            print("Current CSP Settings:")
            for grid in status:
                csp_setting = grid.get('csp_grid_setting', {})
                if csp_setting:
                    for key, value in csp_setting.items():
                        print(f"  {key}: {value}")
                else:
                    print("  No CSP settings configured")
        else:
            # Read token
            join_token = read_join_token(args.token_file)
            print(f"Read join token from {args.token_file} ({len(join_token)} chars)")

            # Set the token
            print(f"Setting CSP join token on {args.gm}...")
            result = set_csp_join_token(args.gm, args.user, args.password, join_token, args.wapi_version)
            print(f"Success! Result: {result}")

            # Check status
            print("\nVerifying CSP status...")
            status = get_csp_status(args.gm, args.user, args.password, args.wapi_version)
            print("Updated CSP Settings:")
            for grid in status:
                csp_setting = grid.get('csp_grid_setting', {})
                if csp_setting:
                    for key, value in csp_setting.items():
                        print(f"  {key}: {value}")
                else:
                    print("  No CSP settings found")

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
