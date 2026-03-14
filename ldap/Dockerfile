FROM osixia/openldap:1.5.0

# Copy custom schema
COPY schema/myorg.schema /container/service/slapd/assets/config/bootstrap/schema/custom/

# Copy seed data
COPY seed/init.ldif /container/service/slapd/assets/config/bootstrap/ldif/custom/

# Load additional schemas (samba, misc)
# These are loaded via environment variable LDAP_SEED_INTERNAL_SCHEMA_PATH
