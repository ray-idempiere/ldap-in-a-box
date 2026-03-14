# 📜 The Chronicle of LDAP-in-a-Box

> [🇹🇼 中文版](README.md)

> The Grand Historian writes: The chaos of account management has plagued enterprises since time immemorial. New hires require accounts across five systems and eight platforms; departures leave three orphaned accounts and two unsealed backdoors. Administrators suffer greatly, yearning for a unified identity solution. LDAP, the ancestor of directory services, is simple in principle yet vast in application. However, deploying bare OpenLDAP is akin to wrestling a tiger barehanded — courageous indeed, but casualties are inevitable. Thus was **LDAP-in-a-Box** forged: Docker to cage the tiger, a Web UI to tame it, so that mere mortals may command it with ease.

---

## I. Origins

LDAP-in-a-Box is a Docker-based identity management solution designed for small and medium businesses. One-click deployment, online in three minutes. Powered by the resilience of OpenLDAP, wrapped in the beauty of Vue.js, with FastAPI as the connective tissue binding front to back.

Grand in ambition, simple in use:
- 🌳 **Tree Directory Browser** — Centered on the Directory Information Tree (DIT), with all OUs, users, and groups visible at a glance
- 👤 **CRUD on Any Node** — Not limited to users; any OU, Group, or Entry can be created, edited, or deleted
- 🔐 **JWT Authentication** — LDAP bind for identity verification, JWT tokens for session security
- 💾 **One-Click Backup** — LDIF export to ensure data is never lost

![LDAP-in-a-Box Tree Directory Browser](docs/frontend-ui.png)

---

## II. Quick Start

As the ancients said: "A journey of a thousand miles begins with `docker compose`."

```bash
# 1. Clone the repository
git clone https://github.com/ray-idempiere/ldap-in-a-box.git
cd ldap-in-a-box

# 2. Configure environment variables
cp .env.example .env
# Edit passwords and domain in .env — never deploy with defaults

# 3. Start
docker compose up -d

# 4. Wait a few seconds, then open your browser
open https://localhost
```

For first login, use `admin` as the username and the `LDAP_ADMIN_PASSWORD` value from your `.env` file.

---

## III. Architecture

```text
                        ┌──────────────────┐
  Browser / HRM ─HTTPS─►│  nginx (TLS)     │
                        │  Port: 443 / 80  │
                        └────────┬─────────┘
                                 │ HTTP
                                 ▼
┌──────────────────────────┐        ┌──────────────────────────┐
│                          │        │                          │
│   ldap-web (FastAPI)     │◄──────►│  ldap-master (OpenLDAP)  │
│   + Vue.js static files  │  LDAP  │  osixia/openldap:1.5.0   │
│   + JWT authentication   │  389   │  + Custom Schema (isVPN)  │
│                          │        │  + Initial LDIF seed data  │
│   Port: 8000 (internal)  │        │  Port: 389 / 636         │
└──────────────────────────┘        └──────────────────────────┘
```

---

## IV. Environment Variables

| Variable | Description | Default |
|---|---|---|
| `LDAP_DOMAIN` | LDAP base domain | `example.com` |
| `LDAP_ADMIN_PASSWORD` | Admin password (**must change**) | `change_me` |
| `LDAP_ORGANISATION` | Organisation name | `My Company` |
| `JWT_SECRET` | JWT signing key (**must change**) | `change_me_to_random_string` |
| `HTTPS_PORT` | HTTPS external port | `443` |
| `HTTP_PORT` | HTTP external port (auto-redirects to HTTPS) | `80` |
| `TZ` | Timezone | `Asia/Taipei` |

> ⚠️ **The Grand Historian warns**: If `LDAP_ADMIN_PASSWORD` and `JWT_SECRET` remain unchanged, it is as if the city gates are thrown wide open and the imperial seal left unguarded — the consequences are yours to bear.

---

## V. API Endpoints

### v1 — Structured API (Users / Groups)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/login` | Login and obtain JWT |
| GET | `/api/v1/users` | List / search users |
| POST | `/api/v1/users` | Create user |
| GET | `/api/v1/users/{uid}` | Get user details |
| PUT | `/api/v1/users/{uid}` | Update user |
| DELETE | `/api/v1/users/{uid}` | Delete user |
| PUT | `/api/v1/users/{uid}/password` | Reset password |
| GET | `/api/v1/groups` | List groups |
| POST | `/api/v1/groups` | Create group |
| POST | `/api/v1/groups/{cn}/members` | Add member |
| POST | `/api/v1/backup` | Export LDIF backup |

### v2 — Generic DIT API (Any Node Operations)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v2/tree/root` | Get directory tree root node |
| GET | `/api/v2/tree?base_dn=` | Expand children of a given DN |
| GET | `/api/v2/entry?dn=` | Read any entry's attributes |
| POST | `/api/v2/entry` | Create any entry |
| PUT | `/api/v2/entry?dn=` | Modify any entry's attributes |
| DELETE | `/api/v2/entry?dn=` | Delete entry (supports recursive) |
| GET | `/api/v2/schema/templates` | Get objectClass templates |

---

## VI. Integration Guide

- **Synology DSM**: Control Panel → Domain/LDAP → Type: LDAP → Server: Docker host IP → Base DN: `dc=example,dc=com`
- **FreeRADIUS**: Configure `mods-available/ldap` to point to `ldap://your-server:389`
- **OpenVPN**: Use the `auth-ldap` plugin, filtering users by the `isVPN` attribute or VPN group membership

---

## VII. HTTPS Configuration

> As the ancients said: "Easy to dodge a spear thrust in the open, but hard to guard against an arrow from the shadows." Transmitting passwords in plaintext is tantamount to announcing them to the world. LDAP-in-a-Box includes a built-in Nginx HTTPS reverse proxy that auto-generates a self-signed certificate on first start — ready out of the box.

### Default Behavior (Self-Signed Certificate)

A self-signed TLS certificate is automatically generated on startup — no additional configuration needed:

- `https://your-server` → Direct access (browser will warn about untrusted cert; accept to proceed)
- `http://your-server` → Automatic 301 redirect to HTTPS

### Using Your Own Certificate / Let's Encrypt

If you already have a proper certificate, simply mount it into nginx:

```yaml
# docker-compose.override.yml
services:
  nginx:
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - /path/to/fullchain.pem:/etc/nginx/ssl/server.crt:ro
      - /path/to/privkey.pem:/etc/nginx/ssl/server.key:ro
```

For Let's Encrypt + Certbot:

```bash
# Obtain certificate on the host
sudo certbot certonly --standalone -d ldap.yourcompany.com

# Mount in docker-compose.override.yml
# server.crt → /etc/letsencrypt/live/ldap.yourcompany.com/fullchain.pem
# server.key → /etc/letsencrypt/live/ldap.yourcompany.com/privkey.pem
```

---

## VIII. API Integration Tutorial (HRM System Example)

> As the ancients said: "Give a man a fish and you feed him for a day; teach a man to fish and you feed him for a lifetime." This chapter uses an HR Management (HRM) system as an example to demonstrate how to query unified accounts via the LDAP-in-a-Box REST API. The same approach applies to ERP, CRM, attendance, and other systems.

### Scenario Overview

```text
┌──────────────┐    ① POST /auth/login     ┌──────────────────┐
│              │ ─────────────────────────► │                  │
│  HRM System  │    ② Return JWT token      │  LDAP-in-a-Box   │
│              │ ◄───────────────────────── │  (API Server)    │
│              │    ③ GET /users/{uid}      │                  │
│              │ ─────────────────────────► │                  │
│              │    ④ Return user info      │                  │
│              │ ◄───────────────────────── │                  │
└──────────────┘                            └──────────────────┘
```

### Step 1: Login to Obtain JWT Token

```bash
curl -s -X POST http://ldap-server:8443/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "change_me"}'
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Step 2: Query User Info with Token

```bash
# Get a specific user
curl -s http://ldap-server:8443/api/v1/users/ray \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

Response:

```json
{
  "uid": "ray",
  "cn": "Ray Lee",
  "mail": "ray@idempiere.dev",
  "description": "iDempiere Developer",
  "is_vpn": true,
  "groups": ["developers", "vpn-users"]
}
```

### Step 3: Search All Users (Supports Keywords)

```bash
# List all
curl -s http://ldap-server:8443/api/v1/users \
  -H "Authorization: Bearer $TOKEN"

# Keyword search
curl -s "http://ldap-server:8443/api/v1/users?search=ray" \
  -H "Authorization: Bearer $TOKEN"
```

### Step 4: List Groups and Members

```bash
curl -s http://ldap-server:8443/api/v1/groups \
  -H "Authorization: Bearer $TOKEN"
```

---

### 🐍 Python Example (For HRM / ERP Backend Integration)

```python
import requests

LDAP_API = "http://ldap-server:8443/api/v1"

# 1. Login
resp = requests.post(f"{LDAP_API}/auth/login", json={
    "username": "admin",
    "password": "change_me"
})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Get user info
user = requests.get(f"{LDAP_API}/users/ray", headers=headers).json()
print(f"Employee: {user['cn']}, Email: {user['mail']}")

# 3. Get all users (sync to HRM)
all_users = requests.get(f"{LDAP_API}/users", headers=headers).json()
for u in all_users:
    print(f"  - {u['uid']}: {u['cn']}")

# 4. Check VPN permission
if user.get("is_vpn"):
    print("✅ This user has VPN access")
```

### 📦 Node.js Example (For Frontend / Microservices)

```javascript
const axios = require('axios');

const LDAP_API = 'http://ldap-server:8443/api/v1';

async function syncUsersToHRM() {
  // 1. Login
  const { data: auth } = await axios.post(`${LDAP_API}/auth/login`, {
    username: 'admin',
    password: 'change_me'
  });

  const headers = { Authorization: `Bearer ${auth.access_token}` };

  // 2. Get all users
  const { data: users } = await axios.get(`${LDAP_API}/users`, { headers });

  // 3. Sync to HRM database
  for (const user of users) {
    console.log(`Syncing employee: ${user.uid} - ${user.cn} (${user.mail})`);
    // await hrmDB.upsert({ employee_id: user.uid, name: user.cn, email: user.mail });
  }
}

syncUsersToHRM();
```

### 🔄 Common Integration Scenarios

| Scenario | API Call | Description |
|---|---|---|
| HRM new hire | `POST /users` | HR creates account, all systems sync automatically |
| HRM termination | `DELETE /users/{uid}` | One-click delete, access revoked across all systems |
| Attendance verification | `POST /auth/login` | Authenticate with LDAP credentials, no separate accounts needed |
| ERP employee sync | `GET /users` | Periodically pull latest employee list |
| VPN permission check | `GET /users/{uid}` → `is_vpn` | Check `isVPN` attribute to determine access |
| Group-based access control | `GET /groups` | Determine system access based on group membership |

---

## IX. Local Development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install --legacy-peer-deps
npm run dev
```

---

## X. Slave Replication

> As the ancients said: "A cunning rabbit has three burrows." Account data likewise deserves redundancy. As your enterprise grows or multi-site needs arise, deploy Slave nodes to distribute read load and enhance disaster recovery.

### When Is It Needed?

| Scenario | Reason |
|---|---|
| Multi-site / cross-region offices | Each site needs a local LDAP node to reduce latency |
| High availability requirements (99.9%+) | Slave continues read service when Master is down |
| High-volume authentication requests | Thousands of devices doing RADIUS / VPN auth simultaneously |

> 💡 **SMB Tip**: If you have < 500 users and a single site, a single Master + periodic LDIF backup is sufficient. No rush to set up Replication.

### Configuration

Add an `ldap-slave` service to `docker-compose.yml`:

```yaml
  ldap-slave:
    image: osixia/openldap:1.5.0
    environment:
      LDAP_ORGANISATION: "${LDAP_ORGANISATION:-My Company}"
      LDAP_DOMAIN: "${LDAP_DOMAIN:-example.com}"
      LDAP_ADMIN_PASSWORD: "${LDAP_ADMIN_PASSWORD:-change_me}"
      LDAP_TLS: "true"
      LDAP_TLS_VERIFY_CLIENT: "never"
      LDAP_REPLICATION: "true"
      LDAP_REPLICATION_HOSTS: "#DIFFABLE:ldap://ldap-master,ldap://ldap-slave"
    depends_on:
      ldap-master:
        condition: service_healthy
    ports:
      - "${LDAP_SLAVE_PORT:-390}:389"
```

Also add Replication environment variables to `ldap-master`:

```yaml
  ldap-master:
    # ... existing config ...
    environment:
      # ... existing variables ...
      LDAP_REPLICATION: "true"
      LDAP_REPLICATION_HOSTS: "#DIFFABLE:ldap://ldap-master,ldap://ldap-slave"
```

### Start and Verify

```bash
# Restart all containers
docker compose up -d

# Verify Replication status
docker exec ldap-slave ldapsearch -x -H ldap://localhost \
  -b "dc=example,dc=com" -D "cn=admin,dc=example,dc=com" \
  -w change_me "(objectClass=*)" dn
```

If the Slave returns the same entries as the Master, replication is working.

### Architecture Diagram

```text
               ┌─────────────────┐
               │    ldap-web     │
               │  (FastAPI + Vue)│
               └────────┬────────┘
                        │ Write + Read
                        ▼
               ┌─────────────────┐     Replication     ┌─────────────────┐
               │  ldap-master    │ ──────────────────► │  ldap-slave     │
               │  Port: 389      │                      │  Port: 390      │
               └─────────────────┘                      └─────────────────┘
                                                         ▲ Read (load balancing)
                                                         │
                                                   Synology / RADIUS
```

### Cross-Machine Deployment (Slave on a Different Host)

> If the Slave is deployed at a remote data center or branch office, simply change `LDAP_REPLICATION_HOSTS` to actual IPs or domain names.

**Machine A (Master)** — `192.168.1.10`

```yaml
# docker-compose.yml on Machine A
ldap-master:
  image: osixia/openldap:1.5.0
  environment:
    LDAP_DOMAIN: "example.com"
    LDAP_ADMIN_PASSWORD: "change_me"
    LDAP_REPLICATION: "true"
    LDAP_REPLICATION_HOSTS: "#DIFFABLE:ldap://192.168.1.10,ldap://192.168.1.20"
  ports:
    - "389:389"
```

**Machine B (Slave)** — `192.168.1.20`

```yaml
# docker-compose.yml on Machine B
ldap-slave:
  image: osixia/openldap:1.5.0
  environment:
    LDAP_DOMAIN: "example.com"
    LDAP_ADMIN_PASSWORD: "change_me"
    LDAP_REPLICATION: "true"
    LDAP_REPLICATION_HOSTS: "#DIFFABLE:ldap://192.168.1.10,ldap://192.168.1.20"
  ports:
    - "389:389"
```

**⚠️ Cross-Machine Notes:**

| Item | Description |
|---|---|
| Firewall | Port `389` must be open between both machines |
| Domain / Password | `LDAP_DOMAIN` and `LDAP_ADMIN_PASSWORD` must be identical on both sides |
| TLS | For public networks, enable `LDAP_TLS=true` and use port `636` to prevent plaintext transmission |
| Write Direction | All write operations should target the Master; Slave is for read distribution only |

```text
  ┌─ Taipei Office ───────────┐        ┌─ Kaohsiung Office ────────┐
  │                           │        │                           │
  │  ldap-web    ldap-master  │ ─────► │  ldap-slave               │
  │  (Admin UI)  192.168.1.10 │  WAN   │  192.168.1.20             │
  │              Port 389     │        │  Port 389                 │
  └───────────────────────────┘        └───────────────────────────┘
                                          ▲
                                          │ Local reads
                                     Synology / RADIUS
```

---

## XI. License

MIT License. See `LICENSE` for details.

---

> The Grand Historian writes: Observing the design of LDAP-in-a-Box — Docker to encapsulate complexity, a tree browser to transform chaos into clarity — small and medium businesses need not employ a dedicated LDAP administrator to enjoy the benefits of unified identity management. As the ancients said: "A craftsman who wishes to do good work must first sharpen his tools." With this tool now forged, may account chaos plague the world no more.
