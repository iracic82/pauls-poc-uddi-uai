#!/usr/bin/env python3

import os
import boto3
import sys
from datetime import datetime, timezone

# ---------------------------
# Setup logging
# ---------------------------
log_file = "dns_record_log.txt"
timestamp = datetime.now(timezone.utc).isoformat()
log_lines = [f"\n--- DNS Record Creation Log [{timestamp}] ---\n"]

def log(message):
    print(message)
    log_lines.append(message + "\n")

# ---------------------------
# AWS credentials from env vars
# ---------------------------
aws_access_key_id = os.getenv("DEMO_AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("DEMO_AWS_SECRET_ACCESS_KEY")
region = os.getenv("DEMO_AWS_REGION", "us-east-1")
hosted_zone_id = os.getenv("DEMO_HOSTED_ZONE_ID")

if not aws_access_key_id or not aws_secret_access_key or not hosted_zone_id:
    log("❌ ERROR: DEMO_AWS_ACCESS_KEY_ID, DEMO_AWS_SECRET_ACCESS_KEY, and DEMO_HOSTED_ZONE_ID must be set")
    sys.exit(1)

# ---------------------------
# Participant + IPs from env
# ---------------------------
participant_id = os.getenv("INSTRUQT_PARTICIPANT_ID")
gm_ip = os.getenv("GM_IP")
gm2_ip = os.getenv("GM2_IP")

if not participant_id:
    log("❌ ERROR: INSTRUQT_PARTICIPANT_ID is not set")
    sys.exit(1)

if not gm_ip:
    log("❌ ERROR: GM_IP must be set")
    sys.exit(1)

if not gm2_ip:
    log("⚠️  WARNING: GM2_IP is not set, skipping infoblox GM2 DNS record")

# ---------------------------
# Build FQDN mapping
# ---------------------------
fqdn_gm = f"{participant_id}-infoblox.iracictechguru.com."
fqdn_gm2 = f"{participant_id}-infoblox2.iracictechguru.com."

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
# Create A record for NIOS GM
# ---------------------------
log(f"➡️  Creating A record: {fqdn_gm} -> {gm_ip}")
try:
    response = route53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            "Comment": f"Upsert A record for {fqdn_gm}",
            "Changes": [
                {
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": fqdn_gm,
                        "Type": "A",
                        "TTL": 300,
                        "ResourceRecords": [{"Value": gm_ip}]
                    }
                }
            ]
        }
    )
    status = response['ChangeInfo']['Status']
    log(f"✅  A record created: {fqdn_gm} -> {gm_ip}")
    log(f"📡  Change status: {status}")

except Exception as e:
    log(f"❌ Failed to create A record {fqdn_gm}: {e}")
    sys.exit(1)

# ---------------------------
# Create A record for NIOS GM2
# ---------------------------
if gm2_ip:
    log(f"➡️  Creating A record: {fqdn_gm2} -> {gm2_ip}")
    try:
        response = route53.change_resource_record_sets(
            HostedZoneId=hosted_zone_id,
            ChangeBatch={
                "Comment": f"Upsert A record for {fqdn_gm2}",
                "Changes": [
                    {
                        "Action": "UPSERT",
                        "ResourceRecordSet": {
                            "Name": fqdn_gm2,
                            "Type": "A",
                            "TTL": 300,
                            "ResourceRecords": [{"Value": gm2_ip}]
                        }
                    }
                ]
            }
        )
        status = response['ChangeInfo']['Status']
        log(f"✅  A record created: {fqdn_gm2} -> {gm2_ip}")
        log(f"📡  Change status: {status}")

    except Exception as e:
        log(f"❌ Failed to create A record {fqdn_gm2}: {e}")
        sys.exit(1)

# ---------------------------
# Save FQDNs and IPs to file
# ---------------------------
fqdn_file = "created_fqdn.txt"
with open(fqdn_file, "w") as f:
    f.write(f"{fqdn_gm} {gm_ip}\n")
    if gm2_ip:
        f.write(f"{fqdn_gm2} {gm2_ip}\n")
log(f"💾 FQDNs and IPs written to {fqdn_file}")

# ---------------------------
# Write log to file
# ---------------------------
with open(log_file, "a") as f:
    f.writelines(log_lines)

log(f"📄 Log written to {log_file}")
