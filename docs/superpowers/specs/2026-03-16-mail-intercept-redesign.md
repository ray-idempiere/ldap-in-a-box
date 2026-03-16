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
| `AD_User_ID` | integer | int | FK → AD_User (sender) |
| `SenderEmail` | varchar(255) | String | Sender email address |
| `Recipients` | varchar(255) | String | To: header |
| `Subject` | varchar(255) | String | Email subject |
| `PostfixQueueID` | varchar(60) | String | Postfix queue ID (used for release/drop callback) |
| `InterceptedDate` | timestamp | Timestamp | When mail was intercepted |
| `BodyText` | text (CLOB) | String | Plain-text email body |
| `BodyHtml` | text (CLOB) | String | HTML email body |
| `DocStatus` | varchar(2) | String | Document status: DR/IP/CO/VO |
| `DocAction` | varchar(2) | String | Document action |
| `Processed` | char(1) | boolean | Whether document has been processed |

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
- Key method implementations:
  - `prepareIt()` — validates required fields (SenderEmail, PostfixQueueID).
  - `completeIt()` — approval action: calls FastAPI `POST /api/v1/mail/release/{PostfixQueueID}`, sets `Processed = true`.
  - `voidIt()` — rejection action: calls FastAPI `POST /api/v1/mail/drop/{PostfixQueueID}`, sets `Processed = true`.
  - `rejectIt()` — delegates to `voidIt()`.

### 3.4 iDempiere REST API Endpoint
The FastAPI monitor will POST to:
```
POST /api/v1/models/hr_mailintercept
```
With payload:
```json
{
  "AD_User_ID": <int or omitted if not found>,
  "SenderEmail": "sender@example.com",
  "Recipients": "recipient@external.com",
  "Subject": "Email subject",
  "PostfixQueueID": "ABC123DEF",
  "InterceptedDate": "2026-03-16T10:00:00Z",
  "BodyText": "Plain text content...",
  "BodyHtml": "<html>...</html>",
  "DocStatus": "DR",
  "DocAction": "CO"
}
```

---

## 4. Postfix Relay Host Reconfiguration

### 4.1 Design

Postfix acts as a relay host. Only outgoing mail (recipient domain ≠ `$LDAP_DOMAIN`) should trigger the `IsMailMonitor` LDAP check.

**Mechanism:** `smtpd_recipient_restrictions` with a hash-based recipient permit file. Internal recipients are permitted immediately (skipping the sender LDAP check). External recipients proceed to the sender LDAP check.

### 4.2 `backend/postfix/main.cf` Changes

Replace:
```
smtpd_sender_restrictions = check_sender_access ldap:/etc/postfix/ldap-sender.cf
```

With:
```
smtpd_recipient_restrictions =
    permit_mynetworks,
    permit_sasl_authenticated,
    check_recipient_access hash:/etc/postfix/recipient_permit.cf,
    check_sender_access ldap:/etc/postfix/ldap-sender.cf,
    defer_unauth_destination
```

### 4.3 New File: `/etc/postfix/recipient_permit.cf`

Generated dynamically by `entrypoint.sh`:
```
@mydomain.com   PERMIT
```
Maps all recipients at the local domain directly to `PERMIT`, short-circuiting the sender LDAP check for internal mail.

### 4.4 `backend/entrypoint.sh` Additions

After generating `ldap-sender.cf`, add:
```bash
# Generate recipient permit map for relay host mode
echo "@${DOMAIN}   PERMIT" > /etc/postfix/recipient_permit.cf
postmap /etc/postfix/recipient_permit.cf
```

---

## 5. FastAPI Changes

### 5.1 `backend/app/mail_monitor.py`

#### `parse_postcat_output()` — extend to extract body
Use Python's `email` module with `policy=default` to extract both body parts:
```python
plain_part = msg.get_body(preferencelist=('plain',))
body_text = plain_part.get_content() if plain_part else ""

html_part = msg.get_body(preferencelist=('html',))
body_html = html_part.get_content() if html_part else ""
```
Return dict adds `body_text` and `body_html` keys.

#### `push_to_idempiere()` — call `hr_mailintercept`
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
    "DocAction": "CO",
}
if ad_user_id:
    create_payload["AD_User_ID"] = ad_user_id

client.post(
    f"{settings.IDEMPIERE_URL}/api/v1/models/hr_mailintercept",
    headers=headers,
    json=create_payload
)
```

### 5.2 `backend/app/routers/mail.py`
No changes required. The `release` and `drop` endpoints operate purely on Postfix queue IDs and are model-agnostic.

---

## 6. Out of Scope

- iDempiere window/tab/field configuration (AD_Table, AD_Column, AD_Window registration) — this must be done in iDempiere application dictionary separately.
- Database migration SQL for `HR_MailIntercept` table — must be created as an iDempiere migration script separately.
- Removal of `MX_RBL` Java files — keep existing files to avoid breaking other usages.

---

## 7. Files Changed / Created

### `ldap-in-a-box` repository
| File | Action |
|------|--------|
| `backend/postfix/main.cf` | Modify — replace `smtpd_sender_restrictions` |
| `backend/entrypoint.sh` | Modify — generate `recipient_permit.cf` |
| `backend/app/mail_monitor.py` | Modify — extract body, call `hr_mailintercept` |

### `tw.ninniku.hrm` repository
| File | Action |
|------|--------|
| `src/tw/ninniku/hrm/model/I_HR_MailIntercept.java` | Create |
| `src/tw/ninniku/hrm/model/X_HR_MailIntercept.java` | Create |
| `src/tw/ninniku/hrm/model/MMailIntercept.java` | Create |
