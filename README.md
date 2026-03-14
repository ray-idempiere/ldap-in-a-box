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
open http://localhost:8443
```

首次登入，以 `admin` 為帳號，`.env` 中所設之 `LDAP_ADMIN_PASSWORD` 為密碼。

---

## 參・架構圖

```text
┌──────────────────────────┐        ┌──────────────────────────┐
│                          │        │                          │
│   ldap-web (FastAPI)     │◄──────►│  ldap-master (OpenLDAP)  │
│   + Vue.js 前端靜態檔案    │  LDAP  │  osixia/openldap:1.5.0   │
│   + JWT 認證              │  389   │  + 自訂 Schema (isVPN)    │
│                          │        │  + 初始 LDIF 種子資料      │
│   Port: 8443             │        │  Port: 389 / 636         │
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
| `WEB_PORT` | Web UI 對外埠號 | `8443` |
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

## 柒・本機開發

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

## 捌・授權

MIT License。詳見 `LICENSE`。

---

> 太史公曰：觀 LDAP-in-a-Box 之設計，以 Docker 封裝複雜，以樹狀瀏覽器化繁為簡，使中小企業不必豢養專職 LDAP 管理員，亦能享統一帳號之便。古有云：「工欲善其事，必先利其器。」此器既成，願天下再無帳號之亂。
