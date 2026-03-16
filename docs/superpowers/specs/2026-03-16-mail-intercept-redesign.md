# Mail Intercept Redesign — Design Spec
**Date:** 2026-03-16
**Project:** ldap-in-a-box

---

## 1. Problem Statement

The current implementation has two structural issues:

1. **Misuse of `MX_RBL`**: The `MX_RBL` iDempiere table is a Realtime Block List (spam IP/domain blacklist). It was incorrectly repurposed to carry email interception approval records. Its schema (`Host`, `Description`, `Processing`) does not map cleanly to the required fields and has no `Sender` column or email body storage.

2. **Postfix intercepts all mail**: The current `smtpd_sender_restrictions` fires on every message regardless of recipient domain. Because this system is a relay host, only outgoing mail (recipient domain ≠ `mydomain`) should be subject to the `IsMailMonitor` LDAP check.

---

## 2. Goals

- Create a dedicated iDempiere Document Model (`HR_MailIntercept`) for the approval workflow.
- Reconfigure Postfix as a proper relay host that intercepts only externally-bound mail from LDAP-monitored senders.
- Update FastAPI `mail_monitor.py` to push to `HR_MailIntercept` instead of `MX_RBL`, including full email body.

---

## 3. iDempiere Document Model: `HR_MailIntercept`

### 3.1 Table Name
`HR_MailIntercept`

### 3.2 Schema

| Column | DB Type | Java Type | Notes |
|--------|---------|-----------|-------|
| `HR_MailIntercept_ID` | integer | int | Primary Key |
| `HR_MailIntercept_UU` | varchar(36) | String | UUID |
| `AD_Client_ID` | integer | int | Standard |
| `AD_Org_ID` | integer | int | Standard |
| `IsActive` | char(1) | boolean | Standard |
| `Created` | timestamp | Timestamp | Standard |
| `CreatedBy` | integer | int | Standard |
| `Updated` | timestamp | Timestamp | Standard |
| `UpdatedBy` | integer | int | Standard |
| `AD_User_ID` | integer | int | FK → AD_User (sender); nullable |
| `SenderEmail` | varchar(255) | String | Sender email address |
| `Recipients` | text (CLOB) | String | To: header (CLOB — may contain many recipients) |
| `Subject` | varchar(255) | String | Email subject |
| `PostfixQueueID` | varchar(60) | String | Postfix queue ID; **UNIQUE constraint** — prevents duplicate records on repeated 30s poll scans |
| `InterceptedDate` | timestamp | Timestamp | When mail was intercepted |
| `BodyText` | text (CLOB) | String | Plain-text email body |
| `BodyHtml` | text (CLOB) | String | HTML email body |
| `DocStatus` | varchar(2) | String | Document status: DR/IP/CO/VO |
| `DocAction` | varchar(2) | String | Document action |
| `Processed` | char(1) | boolean | Whether document has been processed |

**Deduplication:** The unique constraint on `PostfixQueueID` is the server-side guard against duplicate records. The FastAPI monitor polls the hold queue every 30 seconds; the same `PostfixQueueID` will remain in the hold queue until released or dropped. The Python client must handle a `409 Conflict` (or `400`) response from iDempiere gracefully — log and skip, do not treat as a fatal error.

### 3.3 Java Files (in `tw.ninniku.hrm.model`)

Three files following the existing project convention:

#### `I_HR_MailIntercept.java`
- Interface declaring all column name constants and getter/setter signatures.
- Follows the same pattern as `I_MX_RBL.java`.

#### `X_HR_MailIntercept.java`
- Generated base class extending `PO`, implementing `I_HR_MailIntercept` and `I_Persistent`.
- Contains `get_TableName()`, `initPO()`, and all column accessor implementations.
- Follows the same pattern as `X_MX_RBL.java`.

#### `MMailIntercept.java`
- Model class extending `X_HR_MailIntercept`.
- Implements `DocAction` interface for Document Engine integration.
- **Document workflow lifecycle:**
  - Records are created in `DocStatus=DR`, `DocAction=--` (Draft, no pending action).
  - Human approver reviews in iDempiere UI and sets `DocAction=CO` (approve) or `DocAction=VO` (reject).
  - The Document Engine then invokes the appropriate method.
- Key method implementations:
  - `prepareIt()` — validates required fields (`SenderEmail`, `PostfixQueueID`).
  - `completeIt()` — **approval**: calls `POST {LDAP_BOX_URL}/api/v1/mail/release/{PostfixQueueID}`, sets `Processed = true`. Returns `DocStatus.Completed`.
  - `voidIt()` — **rejection**: calls `POST {LDAP_BOX_URL}/api/v1/mail/drop/{PostfixQueueID}`, sets `Processed = true`. Returns `DocStatus.Voided`.
  - `rejectIt()` — delegates to `voidIt()`.

**FastAPI URL configuration:** `MMailIntercept` reads the FastAPI base URL from an iDempiere System Configuration property named `LDAP_BOX_URL` (configurable in iDempiere → System → Client Info or via `AD_SysConfig`). This avoids hardcoding the container URL.

**Authentication:** The FastAPI `/api/v1/mail/release` and `/api/v1/mail/drop` endpoints require no authentication token. This is acceptable because these endpoints are only reachable within the Docker internal network (not exposed externally). This constraint must be enforced at the Docker network/firewall level.

### 3.4 iDempiere REST API Endpoint
The FastAPI monitor will POST to:
```
POST /api/v1/models/hr_mailintercept
```
With payload:
```json
{
  "AD_User_ID": 123,
  "SenderEmail": "sender@example.com",
  "Recipients": "recipient@external.com",
  "Subject": "Email subject",
  "PostfixQueueID": "ABC123DEF",
  "InterceptedDate": "2026-03-16T10:00:00+00:00",
  "BodyText": "Plain text content...",
  "BodyHtml": "<html>...</html>",
  "DocStatus": "DR",
  "DocAction": "--"
}
```

> **Note:** `DocAction` is set to `"--"` (no pending action) at creation time. Setting it to `"CO"` at creation would immediately trigger `completeIt()`, which would release the mail without human review — defeating the purpose of the workflow. Human review is required before any `CO` or `VO` action.

> **Note:** `AD_User_ID` is omitted if the sender is not found in iDempiere.

---

## 4. Postfix Relay Host Reconfiguration

### 4.1 Design

Postfix acts as a relay host. Only outgoing mail (recipient domain ≠ `$LDAP_DOMAIN`) should trigger the `IsMailMonitor` LDAP sender check.

**Mechanism:** Remove `smtpd_sender_restrictions` (which fires at `MAIL FROM:` phase — before recipient is known). Instead, use `smtpd_recipient_restrictions` (which fires at `RCPT TO:` phase — recipient is known). Place a hash-based `check_recipient_access` first: internal recipients (`@mydomain.com`) get `PERMIT` and short-circuit the remaining checks. External recipients fall through to `check_sender_access ldap:...`.

**Per-recipient evaluation semantics:** `smtpd_recipient_restrictions` is evaluated once per `RCPT TO:` command. For a multi-recipient message (some internal, some external), internal recipients are `PERMIT`ed immediately; external recipients proceed to the sender LDAP check. If the sender is monitored, Postfix issues `HOLD` on the `RCPT TO:` for that recipient, which effectively holds the entire message (Postfix places the message in the hold queue on the first `HOLD` result). This is the intended behavior.

**Interaction with `smtpd_relay_restrictions`:** The existing `smtpd_relay_restrictions = permit_mynetworks permit_sasl_authenticated defer_unauth_destination` is retained unchanged. It governs whether Postfix accepts relay attempts at all (relay authorization phase). The new `smtpd_recipient_restrictions` applies only the business-logic HOLD check. Since relay authorization (`permit_mynetworks`, `permit_sasl_authenticated`) is already fully handled by `smtpd_relay_restrictions`, these rules are **not repeated** in `smtpd_recipient_restrictions` — doing so would cause them to short-circuit the LDAP sender check before it is ever reached, because monitored users are typically SASL-authenticated. Only the domain-routing logic belongs in `smtpd_recipient_restrictions`.

**`mydestination` and relay routing:** This is a pure relay host — Postfix must not claim `@$mydomain` as a local delivery domain. `mydestination` must be limited to `localhost` only (i.e., the existing line `mydestination = $myhostname, localhost.$mydomain, localhost` should be replaced with `mydestination = localhost`). This ensures mail addressed to `@$mydomain` is treated as a relay target and passes through `smtpd_recipient_restrictions`, making the `recipient_permit.cf` effective. Without this, Postfix would route `@$mydomain` mail to local delivery before any restrictions are evaluated.

### 4.2 `backend/postfix/main.cf` Changes

Replace:
```
smtpd_relay_restrictions = permit_mynetworks permit_sasl_authenticated defer_unauth_destination
mydestination = $myhostname, localhost.$mydomain, localhost
```

With:
```
smtpd_relay_restrictions = permit_mynetworks permit_sasl_authenticated defer_unauth_destination
mydestination = localhost
smtpd_recipient_restrictions =
    check_recipient_access hash:/etc/postfix/recipient_permit.cf,
    check_sender_access ldap:/etc/postfix/ldap-sender.cf
```

And remove:
```
smtpd_sender_restrictions = check_sender_access ldap:/etc/postfix/ldap-sender.cf
```

### 4.3 New File: `/etc/postfix/recipient_permit.cf`

Generated dynamically by `entrypoint.sh`. Content:
```
@example.com   PERMIT
```
(where `example.com` is replaced with `$DOMAIN` at runtime)

Maps all recipients at `$DOMAIN` directly to `PERMIT`, short-circuiting the sender LDAP check for internal recipients. All other (external) recipients proceed to `check_sender_access`.

> **Note:** This file is generated at container startup by `entrypoint.sh`. The `main.cf` references `hash:/etc/postfix/recipient_permit.cf` which requires a compiled `.db` file. `postmap` must run before `service postfix start`. Postfix will fail lookups silently if the `.db` file is missing.

### 4.4 `backend/entrypoint.sh` Additions

Insert the following **immediately after** the existing `postconf -e "myhostname=$DOMAIN"` line (keeping both `postconf` calls grouped together), and **before** `service postfix start`:

```bash
postconf -e "mydomain=$DOMAIN"
postconf -e "mydestination=localhost"

# Generate recipient permit map for relay host mode (PERMIT internal recipients)
echo "@${DOMAIN}   PERMIT" > /etc/postfix/recipient_permit.cf
postmap /etc/postfix/recipient_permit.cf
```

> **Why `postconf -e "mydomain=$DOMAIN"` is required:** By default, Postfix derives `mydomain` from `myhostname` by stripping the first component. If `myhostname` equals the bare domain (e.g., `example.com`), Postfix cannot derive a subdomain and `mydomain` may be incorrect. Explicit setting removes this ambiguity.

> **Why `mydestination=localhost`:** This is a relay host. Postfix must not claim `@$DOMAIN` as a local delivery destination — otherwise mail to `@$DOMAIN` is resolved before reaching `smtpd_recipient_restrictions` and the permit logic is never evaluated.

---

## 5. FastAPI Changes

### 5.1 `backend/app/mail_monitor.py`

#### `parse_postcat_output()` — extend to extract body

Use Python's `email` module with `policy=default` to extract both body parts:

```python
# Plain text
plain_part = msg.get_body(preferencelist=('plain',))
body_text = plain_part.get_content() if plain_part else ""

# HTML
html_part = msg.get_body(preferencelist=('html',))
body_html = html_part.get_content() if html_part else ""
```

> **MIME fallback note:** `get_body()` works correctly for standard `multipart/alternative` messages. For non-standard MIME structures where `get_body()` returns `None` for both parts, the body fields will be empty strings — this is a known limitation. A more robust fallback using `msg.walk()` to iterate all parts can be added as a follow-on improvement if needed. The current implementation is acceptable for MVP.

Return dict adds `body_text` and `body_html` keys.

#### `push_to_idempiere()` — call `hr_mailintercept`, handle deduplication

Replace the `MX_RBL` create payload with:

```python
from datetime import datetime, timezone

create_payload = {
    "SenderEmail": sender_email,
    "Recipients": mail_info["recipient"],
    "Subject": mail_info["subject"],
    "PostfixQueueID": mail_info["queue_id"],
    "InterceptedDate": datetime.now(timezone.utc).isoformat(),
    "BodyText": mail_info.get("body_text", ""),
    "BodyHtml": mail_info.get("body_html", ""),
    "DocStatus": "DR",
    "DocAction": "--",
}
if ad_user_id:
    create_payload["AD_User_ID"] = ad_user_id

create_resp = client.post(
    f"{settings.IDEMPIERE_URL}/api/v1/models/hr_mailintercept",
    headers=headers,
    json=create_payload
)

if create_resp.status_code in [200, 201]:
    logger.info(f"Successfully created HR_MailIntercept for Queue ID: {mail_info['queue_id']}")
elif create_resp.status_code in [400, 409]:
    # Duplicate PostfixQueueID — record already submitted in a previous scan cycle. Skip silently.
    logger.debug(f"HR_MailIntercept already exists for Queue ID: {mail_info['queue_id']} — skipping")
else:
    logger.error(f"Failed to create HR_MailIntercept: {create_resp.text}")
```

### 5.2 `backend/app/routers/mail.py`
No changes required. The `release` and `drop` endpoints operate purely on Postfix queue IDs and are model-agnostic. These endpoints have no authentication by design — they are only reachable within the Docker internal network.

---

## 6. Out of Scope

- iDempiere window/tab/field configuration (AD_Table, AD_Column, AD_Window registration) — must be done in iDempiere application dictionary separately.
- Database migration SQL for `HR_MailIntercept` table — must be created as an iDempiere migration script separately.
- Removal of `MX_RBL` Java files — keep existing files to avoid breaking other usages.

---

## 7. Files Changed / Created

### `ldap-in-a-box` repository
| File | Action |
|------|--------|
| `backend/postfix/main.cf` | Modify — replace `smtpd_sender_restrictions` with `smtpd_recipient_restrictions` |
| `backend/entrypoint.sh` | Modify — set `mydomain`, generate and `postmap` `recipient_permit.cf` before Postfix starts |
| `backend/app/mail_monitor.py` | Modify — extract body text/html, call `hr_mailintercept`, handle 400/409 as duplicate |

### `tw.ninniku.hrm` repository
| File | Action |
|------|--------|
| `src/tw/ninniku/hrm/model/I_HR_MailIntercept.java` | Create |
| `src/tw/ninniku/hrm/model/X_HR_MailIntercept.java` | Create |
| `src/tw/ninniku/hrm/model/MMailIntercept.java` | Create |
