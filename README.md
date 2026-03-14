# LDAP-in-a-Box

Docker-based identity management for SMBs. Unified account management with a Web UI.

## Quick Start

1. Clone the repository and copy the environment variables example:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` to match your domain and set secure passwords.
3. Start the containers using Docker Compose:
   ```bash
   docker compose up -d
   ```
4. Wait a few seconds for OpenLDAP to initialize.
5. Open your browser and navigate to `http://localhost:8443` (or the port you configured). Login with username `admin`.

## Architecture

```text
+-----------------------+        +--------------------------+
|                       |        |                          |
|  ldap-web (FastAPI)   | <----> |  ldap-master (OpenLDAP)  |
|  + Vue.js Frontend    |        |                          |
|                       |        |                          |
+-----------------------+        +--------------------------+
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `LDAP_DOMAIN` | The base domain for your LDAP directory (e.g. `example.com`) | `example.com` |
| `LDAP_ADMIN_PASSWORD` | The admin password for LDAP | `change_me` |
| `LDAP_ORGANISATION` | Organisation name | `My Company` |
| `WEB_PORT` | Port for the web UI and API | `8443` |
| `LDAP_PORT` | Unencrypted LDAP port | `389` |
| `LDAPS_PORT` | LDAP over TLS port | `636` |
| `TZ` | Timezone | `Asia/Taipei` |
| `JWT_SECRET` | Secret key for JWT auth tokens | *change this* |

## API Endpoints

- `POST /api/v1/auth/login` - Authenticate users
- `GET /api/v1/users` - List / search users
- `POST /api/v1/users` - Create user
- `GET /api/v1/users/{uid}` - Get user details
- `PUT /api/v1/users/{uid}` - Update user profile
- `DELETE /api/v1/users/{uid}` - Delete user
- `PUT /api/v1/users/{uid}/password` - Reset password
- `POST /api/v1/users/{uid}/disable` - Disable user account
- `GET /api/v1/groups` - List groups
- `POST /api/v1/groups` - Create group
- `POST /api/v1/groups/{cn}/members` - Add member to group
- `DELETE /api/v1/groups/{cn}/members` - Remove member
- `POST /api/v1/backup` - Export LDIF backup

## Integration Guides

- **Synology DSM**: Go to Control Panel > Domain/LDAP. Set type to LDAP, server address to your Docker host, and Base DN to your domain (e.g. `dc=example,dc=com`).
- **FreeRADIUS**: Configure `mods-available/ldap` to point to `ldap://your-server:389`. Use the service account for binding.
- **OpenVPN**: Use the `auth-ldap` plugin. You can filter users by checking the `isVPN` attribute or by ensuring they are members of a specific VPN group.

## Development Setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## License

MIT License. See `LICENSE` for details.
