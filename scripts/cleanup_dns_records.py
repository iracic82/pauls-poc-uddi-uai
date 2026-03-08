#!/usr/bin/env python3

import os
import boto3
import sys
from datetime import datetime, timezone

# ---------------------------
# Setup logging
# ---------------------------
log_file = "dns_record_cleanup_log.txt"
timestamp = datetime.now(timezone.utc).isoformat()
log_lines = [f"\n--- DNS Record Deletion Log [{timestamp}] ---\n"]

def log(message):
    print(message)
    log_lines.append(message + "\n")

# ---------------------------
# Read all FQDN + IP pairs from file
# ---------------------------
fqdn_file = "created_fqdn.txt"
records = []
try:
    with open(fqdn_file, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                fqdn, ip = line.split()
                records.append((fqdn, ip))
except Exception as e:
    log(f"❌ ERROR: Failed to read FQDNs and IPs from {fqdn_file}: {e}")
    sys.exit(1)

if not records:
    log("⚠️  No DNS records found in file, nothing to clean up")
    sys.exit(0)

# ---------------------------
# AWS credentials from env vars
# ---------------------------
aws_access_key_id = os.getenv("DEMO_AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("DEMO_AWS_SECRET_ACCESS_KEY")
region = os.getenv("DEMO_AWS_REGION", "us-east-1")
hosted_zone_id = os.getenv("DEMO_HOSTED_ZONE_ID")

if not aws_access_key_id or not aws_secret_access_key or not hosted_zone_id:
    log("❌ ERROR: Missing AWS credentials or Hosted Zone ID")
    sys.exit(1)

# ---------------------------
# Create boto3 session
# ---------------------------
session = boto3.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region
)
route53 = session.client("route53")

# ---------------------------
# Delete all A records
# ---------------------------
for fqdn, ip in records:
    log(f"🗑️  Deleting A record: {fqdn} -> {ip}")
    try:
        response = route53.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                "Comment": f"Delete A record for {fqdn}",
                "Changes": [
                    {
                        "Action": "DELETE",
                        "ResourceRecordSet": {
                            "Name": fqdn,
                            "Type": "A",
                            "TTL": 300,
                            "ResourceRecords": [{"Value": ip}]
                        }
                    }
                ]
            }
        )
        status = response['ChangeInfo']['Status']
        log(f"✅  Deleted: {fqdn} -> {ip}")
        log(f"📡  Change status: {status}")
    except route53.exceptions.InvalidChangeBatch as e:
        log(f"⚠️  Record {fqdn} may not exist or already deleted: {e}")
    except Exception as e:
        log(f"❌ Failed to delete A record {fqdn}: {e}")

# ---------------------------
# Write cleanup log
# ---------------------------
with open(log_file, "a") as f:
    f.writelines(log_lines)

log(f"📄 Cleanup log written to {log_file}")
