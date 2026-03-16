#!/bin/bash
set -e

# Create /etc/mailname (required by Postfix)
DOMAIN="${LDAP_DOMAIN:-example.com}"
echo "$DOMAIN" > /etc/mailname

# Update Postfix LDAP config with actual env values
LDAP_HOST="${LDAP_HOST:-ldap-master}"
LDAP_PORT="${LDAP_PORT:-389}"
LDAP_BASE_DN=$(echo "$DOMAIN" | sed 's/\./,dc=/g' | sed 's/^/dc=/')
ADMIN_DN="cn=admin,$LDAP_BASE_DN"
ADMIN_PW="${LDAP_ADMIN_PASSWORD:-change_me}"

cat > /etc/postfix/ldap-sender.cf <<EOF
server_host = ldap://${LDAP_HOST}:${LDAP_PORT}
search_base = ${LDAP_BASE_DN}
bind = yes
bind_dn = ${ADMIN_DN}
bind_pw = ${ADMIN_PW}
query_filter = (&(objectClass=*)(mail=%s)(IsMailMonitor=TRUE))
result_attribute = mail
result_format = HOLD
EOF

# Configure Postfix hostname and relay host settings
postconf -e "myhostname=$DOMAIN"
postconf -e "mydomain=$DOMAIN"
postconf -e "mydestination=localhost"
postconf -e "maillog_file=/var/log/postfix.log"

# Generate recipient permit map — PERMIT internal recipients, external ones proceed to LDAP check
echo "@${DOMAIN}   PERMIT" > /etc/postfix/recipient_permit.cf
postmap /etc/postfix/recipient_permit.cf

# Start Postfix
service postfix start

# Start the FastAPI app
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
