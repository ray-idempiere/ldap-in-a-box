# 📜 LDAP-in-a-Box 列傳

> 太史公曰：天下帳號之亂，久矣。員工入職須建帳號於五系統、八平台，離職則忘刪三處、漏封兩端。管理者苦之，遂求一統帳號之術。LDAP 者，目錄服務之祖也，其道簡而其用廣。然裸裝 OpenLDAP，猶如徒手搏虎——勇則勇矣，傷亡難免。故有 **LDAP-in-a-Box** 之作，以 Docker 封印猛虎，以 Web UI 馴之，使凡人亦可駕馭。

---

## 壹・起源

LDAP-in-a-Box 者，Docker 化之身份管理方案也。專為中小企業所設，一鍵部署，三分鐘上線。內蘊 OpenLDAP 之堅，外覆 Vue.js 之美，以 FastAPI 為經絡貫通前後。

其志也大，其用也簡：
- 🌳 **樹狀目錄瀏覽器** — 以目錄資訊樹 (DIT) 為核心，所有 OU、使用者、群組一目了然
- 👤 **任意節點 CRUD** — 不限於使用者，任何 OU、Group、Entry 皆可新增、編輯、刪除
- 🔐 **JWT 認證** — 以 LDAP bind 驗身，以 JWT 護航
- 💾 **一鍵備份** — LDIF 匯出，資料不失

![LDAP-in-a-Box 樹狀目錄瀏覽器](docs/frontend-ui.png)

---

## 貳・快速部署

古人云：「千里之行，始於 `docker compose`。」

```bash
# 一、取得原始碼
git clone https://github.com/ray-idempiere/ldap-in-a-box.git
cd ldap-in-a-box

# 二、設定環境變數
cp .env.example .env
# 修改 .env 中的密碼與域名，切勿以預設值上陣

# 三、啟動
docker compose up -d

# 四、靜候數秒，乃開瀏覽器
open https://localhost
```

首次登入，以 `admin` 為帳號，`.env` 中所設之 `LDAP_ADMIN_PASSWORD` 為密碼。

---

## 參・架構圖

```text
                        ┌──────────────────┐
  瀏覽器 / HRM ──HTTPS──►│  nginx (TLS)     │
                        │  Port: 443 / 80  │
                        └────────┬─────────┘
                                 │ HTTP
                                 ▼
┌──────────────────────────┐        ┌──────────────────────────┐
│                          │        │                          │
│   ldap-web (FastAPI)     │◄──────►│  ldap-master (OpenLDAP)  │
│   + Vue.js 前端靜態檔案    │  LDAP  │  osixia/openldap:1.5.0   │
│   + JWT 認證              │  389   │  + 自訂 Schema (isVPN)    │
│                          │        │  + 初始 LDIF 種子資料      │
│   Port: 8000 (internal)  │        │  Port: 389 / 636         │
└──────────────────────────┘        └──────────────────────────┘
```

---

## 肆・環境變數

| 變數 | 說明 | 預設值 |
|---|---|---|
| `LDAP_DOMAIN` | LDAP 基底域名 | `example.com` |
| `LDAP_ADMIN_PASSWORD` | 管理員密碼（**務必修改**） | `change_me` |
| `LDAP_ORGANISATION` | 組織名稱 | `My Company` |
| `JWT_SECRET` | JWT 簽章金鑰（**務必修改**） | `change_me_to_random_string` |
| `HTTPS_PORT` | HTTPS 對外埠號 | `443` |
| `HTTP_PORT` | HTTP 對外埠號（自動跳轉 HTTPS） | `80` |
| `TZ` | 時區 | `Asia/Taipei` |

> ⚠️ **太史公特別提醒**：`LDAP_ADMIN_PASSWORD` 與 `JWT_SECRET` 若不改，猶如城門大開、印璽外露——後果自負。

---

## 伍・API 端點一覽

### v1 — 結構化 API（Users / Groups）

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/api/v1/auth/login` | 登入取得 JWT |
| GET | `/api/v1/users` | 列出 / 搜尋使用者 |
| POST | `/api/v1/users` | 新增使用者 |
| GET | `/api/v1/users/{uid}` | 取得使用者詳情 |
| PUT | `/api/v1/users/{uid}` | 更新使用者 |
| DELETE | `/api/v1/users/{uid}` | 刪除使用者 |
| PUT | `/api/v1/users/{uid}/password` | 重設密碼 |
| GET | `/api/v1/groups` | 列出群組 |
| POST | `/api/v1/groups` | 新增群組 |
| POST | `/api/v1/groups/{cn}/members` | 加入成員 |
| POST | `/api/v1/backup` | 匯出 LDIF 備份 |

### v2 — 泛用 DIT API（任意節點操作）

| 方法 | 路徑 | 說明 |
|---|---|---|
| GET | `/api/v2/tree/root` | 取得目錄樹根節點 |
| GET | `/api/v2/tree?base_dn=` | 展開指定 DN 子節點 |
| GET | `/api/v2/entry?dn=` | 讀取任意 Entry 屬性 |
| POST | `/api/v2/entry` | 新增任意 Entry |
| PUT | `/api/v2/entry?dn=` | 修改任意 Entry 屬性 |
| DELETE | `/api/v2/entry?dn=` | 刪除 Entry（支援遞迴） |
| GET | `/api/v2/schema/templates` | 取得 objectClass 範本 |

---

## 陸・整合指南

- **Synology DSM**：控制台 → 域/LDAP → 類型選 LDAP → 伺服器填 Docker 主機 IP → Base DN 填 `dc=example,dc=com`
- **FreeRADIUS**：設定 `mods-available/ldap`，指向 `ldap://your-server:389`
- **OpenVPN**：使用 `auth-ldap` 插件，搭配 `isVPN` 屬性或 VPN 群組進行過濾

---

## 柒・HTTPS 設定

> 古人云：「明槍易躲，暗箭難防。」帳號密碼若以明文傳輸，豈非自曝於天下？故 LDAP-in-a-Box 內建 Nginx HTTPS 反向代理，首次啟動自動產生自簽憑證，開箱即用。

### 預設行為（自簽憑證）

啟動後即自動生成自簽 TLS 憑證，無需額外設定：

- `https://your-server` → 直接存取（瀏覽器會提示不安全，接受即可）
- `http://your-server` → 自動 301 跳轉至 HTTPS

### 使用自有憑證 / Let's Encrypt

若已有正式憑證，掛載進 nginx 即可：

```yaml
# docker-compose.override.yml
services:
  nginx:
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - /path/to/fullchain.pem:/etc/nginx/ssl/server.crt:ro
      - /path/to/privkey.pem:/etc/nginx/ssl/server.key:ro
```

若使用 Let's Encrypt + Certbot：

```bash
# 在主機上用 certbot 取得憑證
sudo certbot certonly --standalone -d ldap.yourcompany.com

# 掛載進 docker-compose.override.yml
# server.crt → /etc/letsencrypt/live/ldap.yourcompany.com/fullchain.pem
# server.key → /etc/letsencrypt/live/ldap.yourcompany.com/privkey.pem
```

---

## 捌・API 整合教學（以 HRM 系統為例）

> 古人云：「授人以魚，不如授人以漁。」此章以一人資系統 (HRM) 為例，示範如何透過 LDAP-in-a-Box 的 REST API 實現統一帳號查詢。凡 ERP、CRM、打卡系統，皆可依此法炮製。

### 情境說明

```text
┌──────────────┐    ① POST /auth/login     ┌──────────────────┐
│              │ ─────────────────────────► │                  │
│   HRM 系統   │    ② 回傳 JWT token        │  LDAP-in-a-Box   │
│              │ ◄───────────────────────── │  (API Server)    │
│              │    ③ GET /users/{uid}      │                  │
│              │ ─────────────────────────► │                  │
│              │    ④ 回傳使用者資訊         │                  │
│              │ ◄───────────────────────── │                  │
└──────────────┘                            └──────────────────┘
```

### Step 1：登入取得 JWT Token

```bash
curl -s -X POST http://ldap-server:8443/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "change_me"}'
```

回應：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Step 2：用 Token 查詢使用者資訊

```bash
# 取得特定使用者
curl -s http://ldap-server:8443/api/v1/users/ray \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

回應：

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

### Step 3：搜尋全部使用者（支援關鍵字）

```bash
# 列出全部
curl -s http://ldap-server:8443/api/v1/users \
  -H "Authorization: Bearer $TOKEN"

# 關鍵字搜尋
curl -s "http://ldap-server:8443/api/v1/users?search=ray" \
  -H "Authorization: Bearer $TOKEN"
```

### Step 4：列出群組及其成員

```bash
curl -s http://ldap-server:8443/api/v1/groups \
  -H "Authorization: Bearer $TOKEN"
```

---

### 🐍 Python 範例（適用 HRM / ERP 後端整合）

```python
import requests

LDAP_API = "http://ldap-server:8443/api/v1"

# 1. 登入
resp = requests.post(f"{LDAP_API}/auth/login", json={
    "username": "admin",
    "password": "change_me"
})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. 取得使用者資訊
user = requests.get(f"{LDAP_API}/users/ray", headers=headers).json()
print(f"員工：{user['cn']}，信箱：{user['mail']}")

# 3. 取得全部使用者（同步至 HRM）
all_users = requests.get(f"{LDAP_API}/users", headers=headers).json()
for u in all_users:
    print(f"  - {u['uid']}: {u['cn']}")

# 4. 檢查是否有 VPN 權限
if user.get("is_vpn"):
    print("✅ 此使用者已開通 VPN")
```

### 📦 Node.js 範例（適用前端 / 微服務）

```javascript
const axios = require('axios');

const LDAP_API = 'http://ldap-server:8443/api/v1';

async function syncUsersToHRM() {
  // 1. 登入
  const { data: auth } = await axios.post(`${LDAP_API}/auth/login`, {
    username: 'admin',
    password: 'change_me'
  });

  const headers = { Authorization: `Bearer ${auth.access_token}` };

  // 2. 取得全部使用者
  const { data: users } = await axios.get(`${LDAP_API}/users`, { headers });

  // 3. 同步到 HRM 資料庫
  for (const user of users) {
    console.log(`同步員工：${user.uid} - ${user.cn} (${user.mail})`);
    // await hrmDB.upsert({ employee_id: user.uid, name: user.cn, email: user.mail });
  }
}

syncUsersToHRM();
```

### 🔄 常見整合情境

| 情境 | API 呼叫 | 說明 |
|---|---|---|
| HRM 新進員工 | `POST /users` | HR 建帳號後，所有系統自動同步 |
| HRM 離職員工 | `DELETE /users/{uid}` | 一鍵刪除，全系統同時失去存取權 |
| 打卡系統驗證身份 | `POST /auth/login` | 用 LDAP 帳密驗證，不用另建帳號 |
| ERP 同步員工清單 | `GET /users` | 定期拉取最新員工清單 |
| VPN 權限檢查 | `GET /users/{uid}` → `is_vpn` | 檢查 `isVPN` 屬性決定是否放行 |
| 群組權限控管 | `GET /groups` | 依群組決定系統存取權限 |

---

## 玖・本機開發

```bash
# 後端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 前端
cd frontend
npm install --legacy-peer-deps
npm run dev
```

---

## 拾・主從複寫（Slave Replication）

> 古人云：「狡兔三窟。」帳號資料亦當有備無患。若企業規模漸長，或有多站點之需，可設 Slave 節點以分擔讀取、增強容災。

### 何時需要？

| 場景 | 理由 |
|---|---|
| 多站點 / 跨地區辦公室 | 各站點需本地 LDAP 節點，降低延遲 |
| 高可用性要求（99.9%+） | Master 故障時 Slave 可繼續提供讀取服務 |
| 大量認證請求 | 數千台設備同時做 RADIUS / VPN 認證，需做讀取負載分散 |

> 💡 **中小企業提示**：若使用者 < 500 人且僅單一站點，單台 Master + 定期 LDIF 備份已足夠，無需急於設置 Replication。

### 設定方法

在 `docker-compose.yml` 中新增一個 `ldap-slave` service：

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

同時，為 `ldap-master` 也加上 Replication 環境變數：

```yaml
  ldap-master:
    # ... 原有設定 ...
    environment:
      # ... 原有變數 ...
      LDAP_REPLICATION: "true"
      LDAP_REPLICATION_HOSTS: "#DIFFABLE:ldap://ldap-master,ldap://ldap-slave"
```

### 啟動與驗證

```bash
# 重新啟動所有容器
docker compose up -d

# 驗證 Replication 狀態
docker exec ldap-slave ldapsearch -x -H ldap://localhost \
  -b "dc=example,dc=com" -D "cn=admin,dc=example,dc=com" \
  -w change_me "(objectClass=*)" dn
```

若 Slave 能查到與 Master 相同的 Entry，即表示複寫成功。

### 架構圖

```text
               ┌─────────────────┐
               │    ldap-web     │
               │  (FastAPI + Vue)│
               └────────┬────────┘
                        │ 寫入 + 讀取
                        ▼
               ┌─────────────────┐     Replication     ┌─────────────────┐
               │  ldap-master    │ ──────────────────► │  ldap-slave     │
               │  Port: 389      │                      │  Port: 390      │
               └─────────────────┘                      └─────────────────┘
                                                         ▲ 讀取（分流用）
                                                         │
                                                   Synology / RADIUS
```

### 跨機器部署（Slave 在不同主機）

> 若 Slave 部署於異地機房或分公司，只需將 `LDAP_REPLICATION_HOSTS` 改為實際 IP 或域名。

**機器 A（Master）** — `192.168.1.10`

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

**機器 B（Slave）** — `192.168.1.20`

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

**⚠️ 跨機器注意事項：**

| 項目 | 說明 |
|---|---|
| 防火牆 | 兩台機器的 port `389` 必須互通 |
| 域名 / 密碼 | `LDAP_DOMAIN` 和 `LDAP_ADMIN_PASSWORD` 兩邊必須完全一致 |
| TLS | 跨公網務必開啟 `LDAP_TLS=true` 並使用 port `636`，避免明文傳輸 |
| 寫入方向 | 所有寫入操作仍應指向 Master，Slave 僅供讀取分流 |

```text
  ┌─ 台北辦公室 ──────────────┐        ┌─ 高雄辦公室 ──────────────┐
  │                           │        │                           │
  │  ldap-web    ldap-master  │ ─────► │  ldap-slave               │
  │  (管理 UI)   192.168.1.10 │  WAN   │  192.168.1.20             │
  │              Port 389     │        │  Port 389                 │
  └───────────────────────────┘        └───────────────────────────┘
                                          ▲
                                          │ 本地讀取
                                     Synology / RADIUS
```

---

## 拾壹・授權

MIT License。詳見 `LICENSE`。

---

> 太史公曰：觀 LDAP-in-a-Box 之設計，以 Docker 封裝複雜，以樹狀瀏覽器化繁為簡，使中小企業不必豢養專職 LDAP 管理員，亦能享統一帳號之便。古有云：「工欲善其事，必先利其器。」此器既成，願天下再無帳號之亂。
