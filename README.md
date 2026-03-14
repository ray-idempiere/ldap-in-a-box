# LDAP-in-a-Box

Docker-based identity management for SMBs. Unified account management with a Web UI.

## Quick Start

```bash
cp .env.example .env   # edit domain and passwords
docker compose up -d
open https://localhost:8443
```

## Architecture

- **ldap-master**: OpenLDAP 2.6 directory service
- **ldap-web**: FastAPI REST API + Vue.js admin UI
