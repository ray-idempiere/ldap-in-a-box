#!/bin/sh
# Generate self-signed certificate if none exists
SSL_DIR="/etc/nginx/ssl"
if [ ! -f "$SSL_DIR/server.crt" ]; then
  echo "Installing openssl..."
  apk add --no-cache openssl >/dev/null 2>&1
  echo "Generating self-signed SSL certificate..."
  mkdir -p "$SSL_DIR"
  openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout "$SSL_DIR/server.key" \
    -out "$SSL_DIR/server.crt" \
    -subj "/CN=ldap-in-a-box/O=LDAP-in-a-Box/C=TW"
  echo "Self-signed certificate generated."
fi

exec nginx -g "daemon off;"
