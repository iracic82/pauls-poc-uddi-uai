#!/usr/bin/env python3
"""
Create a Forward Looking Delegation (FLD) from an Infoblox federated block.

Looks up the parent federated block by address / CIDR / tag, then calls the
Infoblox Federation "create next available FLD" API to carve a smaller CIDR
out of it. The allocated CIDR is written to a file so that downstream tooling
(e.g. Terraform) can consume it as the address space for a new VNet.

Auth: set BLOXONE_API_KEY, or TF_VAR_ddi_api_key (the Instruqt lab default).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import requests

CSP_URL = os.getenv("BLOXONE_CSP_URL", "https://csp.infoblox.com").rstrip("/")
# The Instruqt lab exports the sandbox-scoped key as TF_VAR_ddi_api_key.
# Accept BLOXONE_API_KEY too so the script runs outside the lab as well.
API_KEY = os.getenv("BLOXONE_API_KEY") or os.getenv("TF_VAR_ddi_api_key")

DEFAULT_OUT_FILE = os.getenv("FLD_CIDR_FILE", "/root/infoblox-lab/pauls-poc/fld_cidr.txt")


class FederationError(RuntimeError):
    """Raised for expected, user-facing failures (clean message, no traceback)."""


def build_session(api_key: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    return session


def ddi_request(session: requests.Session, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    """Call the DDI API and return parsed JSON, surfacing API errors cleanly."""
    url = f"{CSP_URL}/api/ddi/v1/{path.lstrip('/')}"
    try:
        resp = session.request(method, url, timeout=30, **kwargs)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        body = exc.response.text.strip()
        raise FederationError(
            f"{method} {path} -> HTTP {exc.response.status_code}\n{body}"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise FederationError(f"{method} {path} -> request failed: {exc}") from exc

    try:
        return resp.json()
    except ValueError as exc:
        raise FederationError(f"{method} {path} -> response was not valid JSON") from exc


def find_matching_block(
    session: requests.Session,
    address: str,
    cidr: int,
    tag_key: str,
    tag_value: str,
) -> dict[str, Any]:
    """Return the single federated block matching address/cidr/tag, or raise."""
    results = ddi_request(session, "GET", "federation/federated_block").get("results") or []

    matches = [
        block
        for block in results
        if block.get("address") == address
        and int(block.get("cidr", -1)) == cidr
        and (block.get("tags") or {}).get(tag_key) == tag_value
    ]

    if not matches:
        raise FederationError(
            f"No federated block found for {address}/{cidr} with tag "
            f"{tag_key}={tag_value}. Run create_federated_block.py first."
        )
    if len(matches) > 1:
        raise FederationError(
            f"Multiple federated blocks matched {address}/{cidr} with tag "
            f"{tag_key}={tag_value}; refine the lookup."
        )
    return matches[0]


def create_next_available_fld(
    session: requests.Session,
    fld_cidr: int,
    count: int,
    name: str,
    tag_key: str,
    tag_value: str,
) -> dict[str, Any]:
    """Allocate the next available FLD and return the first allocated object."""
    body = {
        "count": count,
        "cidr": fld_cidr,
        "name": name,
        "tags": {tag_key: tag_value},
    }
    result = ddi_request(
        session, "POST", "federation/create_next_available_fld", json=body
    )

    fld_objects = result.get("results") or (result if isinstance(result, list) else [])
    if not fld_objects:
        raise FederationError(
            f"FLD create returned no objects:\n{json.dumps(result, indent=2)}"
        )
    return fld_objects[0]


def write_cidr(path: str, cidr: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(cidr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--address", default="10.0.0.0", help="Parent federated block address")
    parser.add_argument("--cidr", type=int, default=8, help="Parent federated block CIDR")
    parser.add_argument("--tag-key", default="owner", help="Tag key used to match the block")
    parser.add_argument("--tag-value", default="pdh", help="Tag value used to match the block")
    parser.add_argument("--fld-cidr", type=int, default=16, help="CIDR size of the FLD to allocate")
    parser.add_argument("--count", type=int, default=1, help="Number of FLDs to allocate")
    parser.add_argument("--out-file", default=DEFAULT_OUT_FILE, help="Where to write the allocated CIDR")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not API_KEY:
        print("ERROR: set BLOXONE_API_KEY (or TF_VAR_ddi_api_key)", file=sys.stderr)
        return 2

    session = build_session(API_KEY)

    try:
        block = find_matching_block(
            session, args.address, args.cidr, args.tag_key, args.tag_value
        )
        name = f"fld-{args.address.replace('.', '-')}-{args.fld_cidr}-{int(time.time())}"
        fld = create_next_available_fld(
            session, args.fld_cidr, args.count, name, args.tag_key, args.tag_value
        )
    except FederationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    allocated_cidr = f"{fld['address']}/{fld['cidr']}"

    print("Matched federated block:")
    print(json.dumps({k: block.get(k) for k in ("id", "address", "cidr", "tags")}, indent=2))
    print("\nAllocated Forward Looking Delegation:")
    print(json.dumps({k: fld.get(k) for k in ("id", "name", "address", "cidr", "tags")}, indent=2))

    try:
        write_cidr(args.out_file, allocated_cidr)
    except OSError as exc:
        print(f"WARNING: could not write {args.out_file}: {exc}", file=sys.stderr)
    else:
        print(f"\nFLD allocated CIDR: {allocated_cidr}")
        print(f"Written to: {args.out_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
