#!/bin/bash
set -e

DNS_IP="10.100.0.130"
SUBNET="10.100.0.0/24"

echo "Updating packages..."
sudo apt update -y
sudo apt install -y bind9 bind9-utils ufw

echo "Allowing DNS through UFW..."
sudo ufw allow 53/udp
sudo ufw allow 53/tcp

echo "Configuring named.conf.options..."

sudo tee /etc/bind/named.conf.options > /dev/null <<EOF
options {
        directory "/var/cache/bind";

        listen-on { 127.0.0.1; $DNS_IP; };
        allow-query { $SUBNET; 127.0.0.1; };

        recursion yes;
        dnssec-validation auto;

        listen-on-v6 { any; };
};
EOF

echo "Configuring named.conf.local..."

sudo tee /etc/bind/named.conf.local > /dev/null <<EOF
zone "corp1.internal" {
    type master;
    file "/etc/bind/db.corp1.internal";
};

zone "corp2.internal" {
    type master;
    file "/etc/bind/db.corp2.internal";
};
EOF

echo "Creating zone files..."

sudo cp /etc/bind/db.local /etc/bind/db.corp1.internal
sudo cp /etc/bind/db.local /etc/bind/db.corp2.internal

echo "Writing corp1.internal zone..."

sudo tee /etc/bind/db.corp1.internal > /dev/null <<EOF
\$TTL 86400
@   IN  SOA ns1.corp1.internal. admin.corp1.internal. (
        1       ; Serial
        3600    ; Refresh
        1800    ; Retry
        604800  ; Expire
        86400 ) ; Minimum
 
    IN  NS  ns1.corp1.internal.
 
ns1 IN  A   $DNS_IP
app IN  A   10.100.0.130
EOF

echo "Checking configuration..."

sudo named-checkconf
sudo named-checkzone corp1.internal /etc/bind/db.corp1.internal
sudo named-checkzone corp2.internal /etc/bind/db.corp2.internal

echo "Restarting bind9..."

sudo systemctl restart bind9

echo "Setup complete."