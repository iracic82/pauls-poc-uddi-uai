#!/usr/bin/env python3
"""
Creates DNS A records for the 2 NIOS-X servers in Route 53.
Reads NIOSX_1_IP and NIOSX_2_IP from environment variables.
"""

import os
import boto3
import sys
from datetime import datetime

# ---------------------------
# Setup logging
# ---------------------------
log_file = "dns_log_niosx.txt"
timestamp = datetime.utcnow().isoformat()
log_lines = [f"\n--- NIOS-X DNS Record Log [{timestamp}] ---\n"]

def log(message):
    print(message)
    log_lines.append(message + "\n")

# ---------------------------
# AWS credentials and config
# ---------------------------
aws_access_key_id = os.getenv("DEMO_AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("DEMO_AWS_SECRET_ACCESS_KEY")
region = os.getenv("DEMO_AWS_REGION", "us-east-1")
hosted_zone_id = os.getenv("DEMO_HOSTED_ZONE_ID")

if not aws_access_key_id or not aws_secret_access_key or not hosted_zone_id:
    log("ERROR: Missing AWS credentials or Hosted Zone ID in environment")
    sys.exit(1)

niosx_1_ip = os.getenv("NIOSX_1_IP")
niosx_2_ip = os.getenv("NIOSX_2_IP")

if not niosx_1_ip or not niosx_2_ip:
    log("ERROR: NIOSX_1_IP and NIOSX_2_IP must be set in the environment")
    sys.exit(1)

# ---------------------------
# Build FQDN mappings
# ---------------------------
prefix = os.getenv("INSTRUQT_PARTICIPANT_ID", "").strip()
prefix_str = f"{prefix}-" if prefix else ""

records = [
    {
        "fqdn": f"{prefix_str}niosx-1.iracictechguru.com.",
        "ip": niosx_1_ip,
        "comment": "A record for NIOS-X server #1"
    },
    {
        "fqdn": f"{prefix_str}niosx-2.iracictechguru.com.",
        "ip": niosx_2_ip,
        "comment": "A record for NIOS-X server #2"
    }
]

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
# Create A records
# ---------------------------
for record in records:
    fqdn = record["fqdn"]
    ip = record["ip"]
    log(f"Creating A record: {fqdn} -> {ip}")
    try:
        response = route53.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                "Comment": record["comment"],
                "Changes": [
                    {
                        "Action": "UPSERT",
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
        log(f"A record created: {fqdn} -> {ip}")
        log(f"Change status: {status}")
    except Exception as e:
        log(f"ERROR: Failed to create A record for {fqdn}: {e}")
        sys.exit(1)

# ---------------------------
# Write log to file
# ---------------------------
with open(log_file, "a") as f:
    f.writelines(log_lines)

log(f"Log written to {log_file}")
