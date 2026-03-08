#!/usr/bin/env python3
"""
Deletes DNS A records for the 2 NIOS-X servers from Route 53.
Parses the dns_log_niosx.txt log file to find records to delete.
"""

import os
import boto3
import sys
import re
from datetime import datetime, timezone

# ---------------------------
# Logging setup
# ---------------------------
timestamp = datetime.now(timezone.utc).isoformat()
log_file = "dns_log_niosx_cleanup.txt"
source_log_file = "dns_log_niosx.txt"
log_lines = [f"\n--- NIOS-X DNS Record Deletion Log [{timestamp}] ---\n"]

def log(msg):
    print(msg)
    log_lines.append(msg + "\n")

# ---------------------------
# Env Vars
# ---------------------------
aws_access_key_id = os.getenv("DEMO_AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("DEMO_AWS_SECRET_ACCESS_KEY")
region = os.getenv("DEMO_AWS_REGION", "us-east-1")
hosted_zone_id = os.getenv("DEMO_HOSTED_ZONE_ID")

missing = []
if not aws_access_key_id: missing.append("DEMO_AWS_ACCESS_KEY_ID")
if not aws_secret_access_key: missing.append("DEMO_AWS_SECRET_ACCESS_KEY")
if not hosted_zone_id: missing.append("DEMO_HOSTED_ZONE_ID")

if missing:
    log(f"ERROR: Missing required environment variable(s): {', '.join(missing)}")
    sys.exit(1)

# ---------------------------
# Parse DNS Log to extract FQDN and IP pairs
# ---------------------------
if not os.path.exists(source_log_file):
    log(f"ERROR: Log file '{source_log_file}' not found.")
    sys.exit(1)

records_to_delete = []
with open(source_log_file, "r") as f:
    for line in f:
        match = re.search(r"A record created: (.+niosx-\d+\.iracictechguru\.com\.) -> ([\d.]+)", line)
        if match:
            records_to_delete.append({
                "fqdn": match.group(1).strip(),
                "ip": match.group(2).strip()
            })

if not records_to_delete:
    log("WARNING: No NIOS-X A records found in the log to delete.")
    # Write log and exit gracefully
    with open(log_file, "a") as f:
        f.writelines(log_lines)
    sys.exit(0)

# ---------------------------
# Route 53 Deletion
# ---------------------------
session = boto3.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region
)
route53 = session.client("route53")

for record in records_to_delete:
    fqdn = record["fqdn"]
    ip = record["ip"]
    log(f"Deleting A record: {fqdn} -> {ip}")
    try:
        route53.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                "Comment": f"Delete A record {fqdn}",
                "Changes": [{
                    "Action": "DELETE",
                    "ResourceRecordSet": {
                        "Name": fqdn,
                        "Type": "A",
                        "TTL": 300,
                        "ResourceRecords": [{"Value": ip}]
                    }
                }]
            }
        )
        log(f"Successfully deleted: {fqdn}")
    except route53.exceptions.InvalidChangeBatch as e:
        log(f"WARNING: Record may not exist or already deleted: {e}")
    except Exception as e:
        log(f"ERROR during deletion: {e}")
        sys.exit(1)

# ---------------------------
# Write cleanup log
# ---------------------------
with open(log_file, "a") as f:
    f.writelines(log_lines)

log(f"Cleanup log written to {log_file}")
