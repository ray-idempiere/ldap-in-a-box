# Handover：iDempiere `callFastApi` 修改

## 背景

`callFastApi` 目前沒有帶任何認證，但 FastAPI 的 release endpoint 需要 JWT（`require_admin`）。iDempiere 和 FastAPI server 部署在不同主機，改用 JWT 方案：先 login 取 token，再帶 Bearer header 呼叫 release。

---

## 一、iDempiere 需要修改（Java 端）

### 1.1 Login 取得 JWT

在呼叫 release 前，先 POST 到 `/api/v1/auth/login`：

```
POST {FASTAPI_URL}/api/v1/auth/login
Content-Type: application/json

{"username": "admin", "password": "<LDAP_ADMIN_PASSWORD>"}
```

回傳：
```json
{"access_token": "<jwt>", "token_type": "bearer"}
```

### 1.2 `callFastApi` 改為帶 Bearer token

**修改前（現狀）：**
```java
HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create(url))
    .timeout(Duration.ofSeconds(10))
    .POST(HttpRequest.BodyPublishers.noBody())
    .build();
```

**修改後：**
```java
// Step 1: login
String loginUrl = System.getenv("FASTAPI_URL") + "/api/v1/auth/login";
String loginBody = "{\"username\":\"admin\",\"password\":\""
    + System.getenv("FASTAPI_ADMIN_PASSWORD") + "\"}";

HttpRequest loginRequest = HttpRequest.newBuilder()
    .uri(URI.create(loginUrl))
    .timeout(Duration.ofSeconds(10))
    .header("Content-Type", "application/json")
    .POST(HttpRequest.BodyPublishers.ofString(loginBody))
    .build();

HttpResponse<String> loginResponse =
    HTTP_CLIENT.send(loginRequest, HttpResponse.BodyHandlers.ofString());

if (loginResponse.statusCode() != 200) {
    log.warning("FastAPI login failed: " + loginResponse.body());
    return false;
}

// Parse token (simple string extraction, or use a JSON library)
String token = new org.json.JSONObject(loginResponse.body()).getString("access_token");

// Step 2: call release with Bearer token
HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create(url))
    .timeout(Duration.ofSeconds(10))
    .header("Authorization", "Bearer " + token)
    .POST(HttpRequest.BodyPublishers.noBody())
    .build();
```

### 1.3 Release URL（不變）

```
POST {FASTAPI_URL}/api/v1/mail/release/{queue_id}
Authorization: Bearer <token>
```

### 1.4 環境變數

iDempiere server 需要設：

```
FASTAPI_URL=https://<fastapi-host>
FASTAPI_ADMIN_PASSWORD=<LDAP admin password>
```

> `FASTAPI_ADMIN_PASSWORD` 與 FastAPI `.env` 裡的 `LDAP_ADMIN_PASSWORD` 相同。

---

## 二、FastAPI 這邊已完成的變更（`mail_monitor.py`）

### 2.1 重複建立防護：先查 `PostfixQueueID` 再建立

建立 `HR_MailIntercept` 前，先查詢是否已存在相同 queue ID：

```diff
+            check_resp = client.get(
+                f"{IDEMPIERE_URL}/api/v1/models/hr_mailintercept?$filter=PostfixQueueID eq '{queue_id}'",
+                headers=headers
+            )
+            if check_resp.status_code == 200 and check_resp.json().get("row-count", 0) > 0:
+                logger.debug(f"HR_MailIntercept already exists for Queue ID: {queue_id} — skipping")
+                return
```

### 2.2 OData filter 語法修正

```diff
-f"{IDEMPIERE_URL}/api/v1/models/ad_user?filter=email eq '{sender_email}'"
+f"{IDEMPIERE_URL}/api/v1/models/ad_user?$filter=EMail eq '{sender_email}'"
```

- `filter=` → `$filter=`（標準 OData 語法）
- `email` → `EMail`（`AD_User` model 實際欄位名稱）

### 2.3 User ID 欄位名稱修正

```diff
-ad_user_id = users[0].get("AD_User_ID")
+ad_user_id = users[0].get("id")
```

iDempiere REST API 回傳的 record 中，primary key 統一為 `"id"`。

### 2.4 日期格式修正

```diff
-"InterceptedDate": datetime.now(timezone.utc).isoformat()
+"InterceptedDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

`isoformat()` 帶微秒（`2026-03-17T10:00:00.123456+00:00`），改為 iDempiere 接受的格式。

### 2.5 移除 `DocStatus` / `DocAction`

```diff
-                "DocStatus": "DR",
-                "DocAction": "--",
```

這兩個欄位由 iDempiere workflow 自行管理，手動帶入會造成 400 錯誤。

### 2.6 錯誤處理細分 400 vs 409

```diff
-            elif create_resp.status_code in [400, 409]:
-                logger.debug(...)
+            elif create_resp.status_code == 409:
+                logger.debug(f"HR_MailIntercept already exists — skipping duplicate")
+            elif create_resp.status_code == 400:
+                logger.error(f"Failed to create HR_MailIntercept (400): {create_resp.text}")
```
