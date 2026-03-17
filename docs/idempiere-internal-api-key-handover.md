# Handover：iDempiere `callFastApi` 修改

## 背景

FastAPI 這邊新增了一個專供 iDempiere 呼叫的 internal release endpoint，並修正了多個與 iDempiere REST API 對接的問題。iDempiere 和 FastAPI server 部署在不同主機，改用 static API key 方案取代無認證呼叫。

---

## 一、iDempiere 需要修改（Java 端）

### 1. `callFastApi` — 加上 `X-Internal-Key` header

```diff
+    String internalKey = System.getenv("INTERNAL_API_KEY");
+    if (internalKey == null) internalKey = "";
+
     HttpRequest request = HttpRequest.newBuilder()
         .uri(URI.create(url))
         .timeout(Duration.ofSeconds(10))
+        .header("X-Internal-Key", internalKey)
         .POST(HttpRequest.BodyPublishers.noBody())
         .build();
```

### 2. Release URL — 路徑改為 internal

呼叫端建構 URL 的地方，把：
```
/api/v1/mail/release/{queue_id}
```
改為：
```
/api/v1/internal/mail/release/{queue_id}
```

---

## 二、FastAPI 已完成的變更（供 iDempiere 端了解 API 行為）

### 2.1 新增 Internal Release Endpoint

`POST /api/v1/internal/mail/release/{queue_id}`

- 需帶 `X-Internal-Key: <INTERNAL_API_KEY>` header
- 不需 JWT token
- 成功回傳 `{"status": "success", "message": "Mail {queue_id} released"}`

相關 diff：

```diff
# backend/app/config.py
+    internal_api_key: str = ""

# backend/app/auth.py
+def require_internal_key(x_internal_key: str = Header(default="")) -> None:
+    if not settings.internal_api_key or x_internal_key != settings.internal_api_key:
+        raise HTTPException(status_code=401, detail="Invalid internal key")

# backend/app/routers/mail.py
+internal_router = APIRouter(prefix="/api/v1/internal/mail", tags=["Mail Internal"])
+
+@internal_router.post("/release/{queue_id}")
+async def release_mail_internal(queue_id: str, _=Depends(require_internal_key)):
+    ...

# backend/app/main.py
+app.include_router(mail.internal_router)

# docker-compose.yml
+      INTERNAL_API_KEY: "${INTERNAL_API_KEY:-}"
```

---

### 2.2 重複建立防護：先查 `PostfixQueueID` 再建立

建立 `HR_MailIntercept` 前，先查詢是否已存在相同 queue ID，存在就直接跳過，避免重複：

```diff
+            check_resp = client.get(
+                f"{IDEMPIERE_URL}/api/v1/models/hr_mailintercept?$filter=PostfixQueueID eq '{queue_id}'",
+                headers=headers
+            )
+            if check_resp.status_code == 200 and check_resp.json().get("row-count", 0) > 0:
+                logger.debug(f"HR_MailIntercept already exists for Queue ID: {queue_id} — skipping")
+                return
```

> iDempiere 端：`HR_MailIntercept` model 需支援 `$filter=PostfixQueueID eq '...'` 查詢。

---

### 2.3 OData filter 語法修正（`$filter` 前綴）

```diff
-f"{IDEMPIERE_URL}/api/v1/models/ad_user?filter=email eq '{sender_email}'"
+f"{IDEMPIERE_URL}/api/v1/models/ad_user?$filter=EMail eq '{sender_email}'"
```

- `filter=` → `$filter=`（標準 OData 語法）
- `email` → `EMail`（對應 iDempiere `AD_User` model 的實際欄位名稱）

---

### 2.4 User ID 欄位名稱修正

```diff
-ad_user_id = users[0].get("AD_User_ID")
+ad_user_id = users[0].get("id")
```

iDempiere REST API 回傳的 record 中，primary key 統一為 `"id"`，不是欄位名稱 `"AD_User_ID"`。

---

### 2.5 日期格式修正

```diff
-"InterceptedDate": datetime.now(timezone.utc).isoformat()
+"InterceptedDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

`isoformat()` 會產生帶微秒的格式（如 `2026-03-17T10:00:00.123456+00:00`），改為 iDempiere 接受的 `2026-03-17T10:00:00Z`。

---

### 2.6 移除 `DocStatus` / `DocAction` 欄位

```diff
-                "DocStatus": "DR",
-                "DocAction": "--",
```

這兩個欄位由 iDempiere workflow 自行管理，手動帶入會造成 400 錯誤。

---

### 2.7 錯誤處理細分 400 vs 409

```diff
-            elif create_resp.status_code in [400, 409]:
-                logger.debug(f"HR_MailIntercept already exists ...")
+            elif create_resp.status_code == 409:
+                logger.debug(f"HR_MailIntercept already exists ...")
+            elif create_resp.status_code == 400:
+                logger.error(f"Failed to create HR_MailIntercept (400): {create_resp.text}")
```

400 是真正的建立失敗，需要 log error 而非靜默略過。

---

## 三、部署設定

兩邊都要設相同的 key：

```bash
# 產生 key（一次即可）
openssl rand -hex 32
```

**FastAPI server（`.env`）：**
```
INTERNAL_API_KEY=<上面產生的字串>
```

**iDempiere server（環境變數）：**
```
INTERNAL_API_KEY=<相同的字串>
```
