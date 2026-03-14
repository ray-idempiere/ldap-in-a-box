# LDAP-in-a-Box v2 — LDAP Tree Browser UI

> 目標：將目前的平面式 Users / Groups 管理介面升級為**以 LDAP DIT (Directory Information Tree) 為核心的樹狀瀏覽器**，支援在任意 Tree Node 上執行 CRUD 操作（不限於 `ou=users`，可操作任何 OU、Entry）。

---

## 1. 現況分析

| 層級 | 目前狀態 | 不足 |
|---|---|---|
| **Backend** | `LDAPService` 已有泛用 `search / add / modify / delete`，但 Router 只暴露 `/users` 和 `/groups` 兩組 typed endpoint | 無法操作任意 DN / objectClass |
| **Frontend** | 扁平的 `Users.vue`、`Groups.vue` 表格 | 無法看到完整目錄樹；無法管理自建 OU |
| **UX** | Tailwind 基本樣式，無 sidebar | 不夠專業、無導航層級感 |

---

## 2. 設計目標

1. **左側 LDAP Tree Panel** — 從 Base DN 開始遞迴呈現目錄結構，可展開/收合
2. **右側 Entry Detail Panel** — 點選任一 node 後顯示其所有屬性 (Attribute)，並提供 inline 編輯
3. **任意節點 CRUD**：
   - **Create** — 在任一 OU 下新增子 Entry（可選擇 objectClass template：OU / User / Group / 自訂）
   - **Read** — 顯示 Entry 的所有 attributes
   - **Update** — 修改 attributes（新增 / 刪除 / 修改值）
   - **Delete** — 刪除任一 Leaf Entry（或遞迴刪除含子節點的 OU）
4. **Premium UI** — 深色側邊欄 + 白色主內容區，Modern SaaS 風格

---

## 3. 架構變更

```text
┌─────────────────────────────────────────────────────────┐
│  Vue.js SPA (frontend)                                  │
│  ┌─────────────┐  ┌──────────────────────────────────┐  │
│  │  TreePanel   │  │  EntryDetail / CreateEntry       │  │
│  │  (recursive) │  │  (attribute editor)              │  │
│  └─────────────┘  └──────────────────────────────────┘  │
│         ↕ Axios                                         │
├─────────────────────────────────────────────────────────┤
│  FastAPI Backend                                        │
│  ┌──────────────────────────────────────────┐           │
│  │  /api/v2/tree   — Generic DIT browser    │           │
│  │  /api/v2/entry  — Generic CRUD on any DN │           │
│  │  /api/v2/schema — objectClass templates  │           │
│  │  /api/v1/*      — (保留既有 endpoints)    │           │
│  └──────────────────────────────────────────┘           │
│         ↕ python-ldap                                   │
├─────────────────────────────────────────────────────────┤
│  OpenLDAP (ldap-master)                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 4. 實作計畫

### Chunk A：Backend — Generic DIT API (`/api/v2`)

> 新增一組泛用 API，讓前端可以瀏覽及操作任意 DN。

#### [NEW] `backend/app/routers/tree.py`

| Endpoint | Method | 說明 |
|---|---|---|
| `/api/v2/tree?base_dn=&scope=one` | GET | 取得指定 DN 下一層子節點（預設 `SCOPE_ONELEVEL`），回傳 `[{dn, rdn, objectClass[], hasChildren}]` |
| `/api/v2/tree/root` | GET | 回傳 Base DN 本身資訊及一層子節點 |

#### [NEW] `backend/app/routers/entry.py`

| Endpoint | Method | 說明 |
|---|---|---|
| `/api/v2/entry?dn=` | GET | 讀取指定 DN 的所有 attributes |
| `/api/v2/entry` | POST | body: `{parent_dn, rdn, objectClasses[], attributes{}}` → 新增 Entry |
| `/api/v2/entry?dn=` | PUT | body: `{modifications[{op, attr, values}]}` → 修改 attributes |
| `/api/v2/entry?dn=` | DELETE | 刪除 Entry（query param `recursive=true` 時遞迴刪除子節點） |

#### [NEW] `backend/app/routers/schema.py`

| Endpoint | Method | 說明 |
|---|---|---|
| `/api/v2/schema/templates` | GET | 回傳常用 objectClass templates（OU / User / Group / Custom），包含 required & optional attributes |

#### [MODIFY] `backend/app/services/ldap_service.py`

- 新增 `search_onelevel(base_dn)` — 用 `SCOPE_ONELEVEL` 取得子節點
- 新增 `search_entry(dn)` — 用 `SCOPE_BASE` 取得單一 entry 的所有 attrs
- 新增 `delete_tree(dn)` — 遞迴刪除 subtree（先查子節點再由葉往根逐一刪除）
- 新增 `get_subschema()` — 讀取 LDAP schema 資訊

#### [MODIFY] `backend/app/main.py`

- 掛入新的 `tree`, `entry`, `schema` routers

---

### Chunk B：Frontend — LDAP Tree Browser

#### [NEW] `frontend/src/views/TreeBrowser.vue`

主頁面。採用兩欄式 Layout：
- 左欄 (280px)：`<TreePanel>` 元件
- 右欄：根據選取的 node 動態顯示 `<EntryDetail>` 或 `<CreateEntry>`

#### [NEW] `frontend/src/components/TreePanel.vue`

遞迴樹元件：
- 接收 `baseDn` prop
- 展開節點時呼叫 `GET /api/v2/tree?base_dn=xxx&scope=one`
- 每個 node 顯示：icon（依 objectClass 不同：📁 OU / 👤 User / 👥 Group / 📄 Entry）、RDN 名稱、展開箭頭
- 點擊 node 時 emit `select(dn)` 事件
- 右鍵 context menu：New Entry / Delete

#### [NEW] `frontend/src/components/EntryDetail.vue`

Entry 詳情 + 編輯器：
- 顯示 DN、objectClass 清單
- 所有 attributes 以 key-value 表格呈現
- 每個 attribute 支援 inline 修改、新增值、刪除值
- 底部 Save / Discard 按鈕
- 頂部 Delete Entry 按鈕

#### [NEW] `frontend/src/components/CreateEntry.vue`

新增 Entry 表單：
- 選擇 objectClass template（OU / User / Group / Custom）
- 依據 template 自動帶出 required / optional attributes 欄位
- 輸入 RDN 值
- 建立後自動 refresh tree

#### [MODIFY] `frontend/src/App.vue`

- 導覽列新增 **「Tree Browser」** 連結
- (保留既有 Dashboard / Users / Groups 連結作為 shortcut)

#### [MODIFY] `frontend/src/router.js`

- 新增 `/tree` route → `TreeBrowser.vue`

#### [MODIFY] `frontend/src/style.css`

- 加入 tree panel styles、context menu styles、split-pane layout

---

### Chunk C：Premium UI 升級

#### [MODIFY] `frontend/src/App.vue`

- 升級 Navbar 為 **深色 sidebar navigation**（左側窄條 + icon + label）
- 頁面改為 sidebar + main content layout
- 加入微動畫（expand/collapse tree node transition、hover effects）

#### [MODIFY] 所有 views

- 統一卡片/表格樣式
- 加入 loading skeleton
- 加入 toast 通知（成功/失敗操作）

---

### Chunk D：整合 & 測試

#### Docker 重建

```bash
docker compose up --build -d
```

#### 測試計畫

| # | 測試項目 | 方式 | 預期結果 |
|---|---|---|---|
| 1 | Tree 瀏覽 Base DN | 瀏覽器打開 `/tree` | 看到 `dc=example,dc=com` 根節點及 `ou=users`, `ou=groups`, `ou=alias`, `ou=system` |
| 2 | 展開 `ou=users` | 點擊展開箭頭 | 看到 `testuser` entry |
| 3 | 點選 `testuser` | 點擊 node | 右側顯示 DN、cn、sn、mail、isVPN 等 attributes |
| 4 | 修改 attribute | 修改 mail 值 → Save | API 回應 200，重新讀取顯示新值 |
| 5 | 在 `ou=users` 下新增 OU | 右鍵 → New Entry → OU | 成功建立 `ou=it,ou=users,dc=example,dc=com`，tree 自動 refresh |
| 6 | 在新 OU 下新增 User | 切換到新 OU → New User Entry | 成功建立使用者 |
| 7 | 刪除 Leaf Entry | 選取 entry → Delete | entry 從 tree 中消失 |
| 8 | 遞迴刪除 OU | 對含有子節點的 OU 執行 Delete（confirm recursive） | OU 及其子節點全部被刪除 |
| 9 | 既有 Users/Groups 頁面 | 開啟 `/users` 和 `/groups` | 功能不受影響 |
| 10 | Backend API 測試 | `curl -X GET /api/v2/tree/root` | 回傳 JSON tree 結構 |

#### 自動化 API 測試腳本

```bash
# 取得 Token
TOKEN=$(curl -s -X POST http://localhost:8443/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"change_me"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 測試 Tree Root
curl -s http://localhost:8443/api/v2/tree/root \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 測試 Entry 讀取
curl -s "http://localhost:8443/api/v2/entry?dn=ou=users,dc=example,dc=com" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 測試建立新 OU
curl -s -X POST http://localhost:8443/api/v2/entry \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"parent_dn":"dc=example,dc=com","rdn":"ou=test-ou","objectClasses":["organizationalUnit"],"attributes":{"ou":"test-ou"}}' | python3 -m json.tool

# 測試刪除
curl -s -X DELETE "http://localhost:8443/api/v2/entry?dn=ou=test-ou,dc=example,dc=com" \
  -H "Authorization: Bearer $TOKEN"
```

#### 瀏覽器 UI 驗收

手動在瀏覽器中操作驗證 Tree 展開、Node 選取、Attribute 編輯、新增/刪除 Entry 等所有功能。

---

## 5. 時程估算

| Chunk | 工作量 |
|---|---|
| A: Backend Generic DIT API | ~4 files, ~300 lines |
| B: Frontend Tree Browser | ~4 files, ~500 lines |
| C: Premium UI 升級 | ~3 files, ~200 lines |
| D: 整合 & 測試 | Docker rebuild + API/UI testing |
