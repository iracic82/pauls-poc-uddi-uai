#!/bin/bash
set -e

# ---- CONFIG (edit if needed) ----
CN="app.corp1.internal"   # hostname you will use (should resolve to this server)
PAGE_HEADING="Internal DNS Validation Page"
PAGE_BODY="Successful access confirms that enterprise DNS policies are being enforced and DNS over HTTPS (DoH) is not in use for this domain."

DAYS="100"
KEY_PATH="/etc/ssl/private/internal.key"
CRT_PATH="/etc/ssl/certs/internal.crt"
# --------------------------------

echo "[1/7] Update packages and install Apache + SSL tools..."
sudo apt update -y
sudo apt install -y apache2 openssl ufw

echo "[2/7] Allow HTTP/HTTPS through UFW..."
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

echo "[3/7] Create the web page..."
sudo tee /var/www/html/index.html > /dev/null <<EOF
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Internal DNS Validation</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 50px; background-color: #f4f6f8; }
      .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
      h1 { color: #2c3e50; }
      p { font-size: 16px; color: #333; }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>${PAGE_HEADING}</h1>
      <p>${PAGE_BODY}</p>
    </div>
  </body>
</html>
EOF

echo "[4/7] Enable SSL module and default SSL site..."
sudo a2enmod ssl
sudo a2ensite default-ssl

echo "[5/7] Create self-signed certificate..."
sudo openssl req -x509 -nodes -days "$DAYS" -newkey rsa:2048 \
  -keyout "$KEY_PATH" \
  -out "$CRT_PATH" \
  -subj "/C=IN/ST=KA/L=Bangalore/O=Internal/OU=IT/CN=$CN"

echo "[6/7] Configure Apache SSL site to use the certificate..."
sudo sed -i "s#^\\s*SSLCertificateFile.*#SSLCertificateFile $CRT_PATH#" /etc/apache2/sites-available/default-ssl.conf
sudo sed -i "s#^\\s*SSLCertificateKeyFile.*#SSLCertificateKeyFile $KEY_PATH#" /etc/apache2/sites-available/default-ssl.conf

echo "[7/7] Restart and enable Apache..."
sudo apachectl configtest
sudo systemctl restart apache2
sudo systemctl enable apache2

echo "Done."
echo "Test:"
echo "  curl -k https://localhost"
echo "  curl -k https://$CN"