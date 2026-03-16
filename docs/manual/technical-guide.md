# Mail Intercept — Technical Guide

## Architecture

```
Employee mail client
    │
    │ SMTP (authenticated)
    ▼
Postfix (ldap-web container)
    │ smtpd_recipient_restrictions
    │  ├─ @company.com → PERMIT (internal, no check)
    │  └─ external    → LDAP lookup (IsMailMonitor=TRUE → HOLD)
    │
    ▼
Hold queue  ◄──── FastAPI mail_monitor.py polls every 30s
    │                   │
    │                   │ POST /api/v1/models/hr_mailintercept
    │                   ▼
    │             iDempiere ERP
    │             HR_MailIntercept record (DocStatus=DR)
    │                   │
    │         HR Manager reviews and acts
    │                   │
    │         ┌─────────┴─────────┐
    │         │ Complete (approve) │ Void (reject)
    │         │                   │
    │  POST /api/v1/mail/release  POST /api/v1/mail/drop
    │         │                   │
    │   postsuper -H              postsuper -d
    │   postqueue -f              (deleted)
    │         │
    ▼
Delivered to recipient
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LDAP_DOMAIN` | `example.com` | Company domain. Used for `/etc/mailname`, `mydomain`, and `recipient_permit.cf` |
| `LDAP_HOST` | `ldap-master` | LDAP server hostname |
| `LDAP_PORT` | `389` | LDAP server port |
| `LDAP_ADMIN_PASSWORD` | `change_me` | LDAP bind password for Postfix sender lookups |
| `IDEMPIERE_URL` | `http://idempiere:8080` | iDempiere base URL |
| `IDEMPIERE_CLIENT_ID` | `11` | iDempiere Client ID for API authentication |
| `IDEMPIERE_ROLE_ID` | `102` | iDempiere Role ID |
| `IDEMPIERE_ORG_ID` | `11` | iDempiere Organisation ID |
| `IDEMPIERE_WAREHOUSE_ID` | `103` | iDempiere Warehouse ID |
| `IDEMPIERE_USER` | `admin` | iDempiere API username |
| `IDEMPIERE_PASS` | `admin` | iDempiere API password |

All variables can be set via a `.env` file or Docker environment configuration.

---

## Postfix Configuration

### Relay Host Mode

Postfix is configured as a relay host (`mydestination = localhost`). It does not claim local delivery for `@$LDAP_DOMAIN` — all mail is relayed.

**`backend/postfix/main.cf`** (relevant section):

```
smtpd_relay_restrictions = permit_mynetworks permit_sasl_authenticated defer_unauth_destination
mydestination = localhost

smtpd_recipient_restrictions =
    check_recipient_access hash:/etc/postfix/recipient_permit.cf,
    check_sender_access ldap:/etc/postfix/ldap-sender.cf
```

### Restriction Logic

`smtpd_recipient_restrictions` fires at `RCPT TO:` time (recipient is known):

1. **`check_recipient_access hash:/etc/postfix/recipient_permit.cf`**
   Entries: `@company.com PERMIT`
   Internal recipients match immediately → PERMIT (no further checks).

2. **`check_sender_access ldap:/etc/postfix/ldap-sender.cf`**
   For external recipients only. Queries LDAP: if the sender has `IsMailMonitor=TRUE`, returns `HOLD`. Otherwise no match → mail proceeds normally.

`smtpd_relay_restrictions` is evaluated first. Monitored employees are SASL-authenticated, so `permit_sasl_authenticated` matches and Postfix proceeds to `smtpd_recipient_restrictions`. The `defer_unauth_destination` clause only applies to unauthenticated senders.

### Runtime File Generation

`entrypoint.sh` generates two files before starting Postfix:

**`/etc/postfix/ldap-sender.cf`** — LDAP query config:
```
server_host = ldap://${LDAP_HOST}:${LDAP_PORT}
search_base = dc=company,dc=com
bind = yes
bind_dn = cn=admin,dc=company,dc=com
bind_pw = ${LDAP_ADMIN_PASSWORD}
query_filter = (&(objectClass=*)(mail=%s)(IsMailMonitor=TRUE))
result_attribute = mail
result_format = HOLD
```

**`/etc/postfix/recipient_permit.cf`** — domain permit map:
```
@company.com   PERMIT
```
After writing this file, `postmap` compiles it to a `.db` binary that Postfix can read.

### Outbound Delivery

`relayhost` is empty in `main.cf` — Postfix attempts direct MX delivery. For environments where outbound port 25 is blocked, set `relayhost` via `postconf -e` in `entrypoint.sh` or pass it as an environment variable.

---

## FastAPI Mail Monitor

### Location

`backend/app/mail_monitor.py`

### Polling Schedule

APScheduler runs `scan_and_forward_held_mails()` every 30 seconds with `max_instances=1` (no overlapping runs).

### Scan Cycle

1. **`get_held_queue_ids()`** — runs `postqueue -p`, parses output for lines containing `!` (held queue IDs).
2. **`parse_postcat_output(queue_id)`** — runs `postcat -q <id>`, extracts the raw message between `*** MESSAGE CONTENTS ***` and `*** HEADER EXTRACTED ***`, parses it with Python's `email` module (`policy=default`), and extracts `From`, `To`, `Subject`, plain-text body, and HTML body.
3. **`push_to_idempiere(mail_info)`** — authenticates to iDempiere REST API, looks up `AD_User_ID` by sender email, and POSTs to `/api/v1/models/hr_mailintercept`.

### Deduplication

A held message stays in the queue until released or dropped. The monitor will re-encounter the same queue ID on every 30-second cycle. Deduplication relies on a unique constraint on `PostfixQueueID` in the `HR_MailIntercept` database table. iDempiere returns `400` or `409` for duplicate records; the monitor logs a debug message and skips — no duplicate records are created.

**Prerequisite:** The `HR_MailIntercept` database table must have a `UNIQUE` constraint on `PostfixQueueID`. This must be part of the iDempiere migration script (see [iDempiere Setup](#idempiere-setup) below).

### iDempiere API Payload

```json
{
  "AD_User_ID": 123,
  "SenderEmail": "employee@company.com",
  "Recipients": "external@partner.com",
  "Subject": "Quarterly report",
  "PostfixQueueID": "ABC1234DEF",
  "InterceptedDate": "2026-03-16T10:00:00+00:00",
  "BodyText": "Plain text content...",
  "BodyHtml": "<html>...</html>",
  "DocStatus": "DR",
  "DocAction": "--"
}
```

`AD_User_ID` is omitted if the sender's email is not found in iDempiere. `DocAction = "--"` means no pending action — the document is created in Draft with no automatic workflow trigger.

---

## FastAPI Mail Control Endpoints

**`POST /api/v1/mail/release/{queue_id}`**
Runs `postsuper -H {queue_id}` (move to active queue) then `postqueue -f` (flush for immediate delivery).

**`POST /api/v1/mail/drop/{queue_id}`**
Runs `postsuper -d {queue_id}` (permanently delete from queue).

Both endpoints validate `queue_id` with `isalnum()` to prevent shell injection. They require no authentication — they must only be reachable within the Docker internal network. Do not expose port 8000 externally.

---

## iDempiere Setup

The following steps must be completed in iDempiere before the system functions end-to-end.

### 1. Database Migration

Create the `HR_MailIntercept` table with at minimum:

```sql
CREATE TABLE hr_mailintercept (
    hr_mailintercept_id   SERIAL PRIMARY KEY,
    hr_mailintercept_uu   VARCHAR(36) NOT NULL,
    ad_client_id          INTEGER NOT NULL,
    ad_org_id             INTEGER NOT NULL,
    isactive              CHAR(1) NOT NULL DEFAULT 'Y',
    created               TIMESTAMP NOT NULL DEFAULT NOW(),
    createdby             INTEGER NOT NULL,
    updated               TIMESTAMP NOT NULL DEFAULT NOW(),
    updatedby             INTEGER NOT NULL,
    ad_user_id            INTEGER,
    senderemail           VARCHAR(255) NOT NULL,
    recipients            TEXT,
    subject               VARCHAR(255),
    postfixqueueid        VARCHAR(60) NOT NULL,
    intercepteddate       TIMESTAMP,
    bodytext              TEXT,
    bodyhtml              TEXT,
    docstatus             VARCHAR(2) NOT NULL DEFAULT 'DR',
    docaction             VARCHAR(2) NOT NULL DEFAULT '--',
    processed             CHAR(1) NOT NULL DEFAULT 'N',
    UNIQUE (postfixqueueid)
);
```

The `UNIQUE` constraint on `postfixqueueid` is required for deduplication.

### 2. Application Dictionary Registration

Register the table, columns, window, tab, and fields in the iDempiere Application Dictionary so the HR Mail Intercept window appears in the menu. This is done through the iDempiere System Admin UI (AD_Table, AD_Column, AD_Window, AD_Tab, AD_Field entries).

### 3. Java Plugin Deployment

Deploy the `tw.ninniku.hrm` OSGi bundle to iDempiere. The bundle contains:

- `I_HR_MailIntercept` — column name constants and interface
- `X_HR_MailIntercept` — generated PO base class
- `MMailIntercept` — business model with DocAction (Complete = release, Void = drop)

### 4. System Configurator

Set the FastAPI base URL so `MMailIntercept` can call back to the `ldap-web` container:

1. In iDempiere: **System → System Configurator**
2. Add a new entry:
   - **Name:** `LDAP_BOX_URL`
   - **Value:** `http://ldap-web:8000` (or the actual container hostname/port)
   - **Client:** set to your client, or leave as System-level

If this entry is missing, the default `http://ldap-web:8000` is used.

---

## Logs and Monitoring

### Container Logs

```bash
docker logs ldap-web
```

Key log prefixes:

| Prefix | Meaning |
|--------|---------|
| `app.mail_monitor - INFO - Scanning Postfix hold queue` | Poll cycle started |
| `app.mail_monitor - INFO - Detected N held messages` | Messages found |
| `app.mail_monitor - INFO - Intercepted mail from ... to ...` | Mail being processed |
| `app.mail_monitor - INFO - Created HR_MailIntercept for Queue ID` | Successfully pushed to iDempiere |
| `app.mail_monitor - DEBUG - HR_MailIntercept already exists` | Duplicate — skipped |
| `app.mail_monitor - ERROR - iDempiere Login failed` | API authentication problem |

### Postfix Queue

```bash
# List all held messages (marked with !)
docker exec ldap-web postqueue -p

# Inspect a specific held message
docker exec ldap-web postcat -q <queue_id>

# Manually release a message
docker exec ldap-web postsuper -H <queue_id>
docker exec ldap-web postqueue -f

# Manually delete a message
docker exec ldap-web postsuper -d <queue_id>
```

### Postfix Logs

Postfix logs to `/var/log/postfix.log` inside the container:

```bash
docker exec ldap-web tail -f /var/log/postfix.log
```

Look for `status=held` entries to confirm the HOLD restriction is firing.

---

## Troubleshooting

### Mail is not being held

1. Confirm `IsMailMonitor=TRUE` is set on the user's LDAP entry.
2. Check Postfix logs for the `RCPT TO:` exchange:
   ```
   docker exec ldap-web tail -f /var/log/postfix.log
   ```
   Look for `hold: header ...` or `status=held`.
3. Verify `ldap-sender.cf` was generated correctly:
   ```
   docker exec ldap-web cat /etc/postfix/ldap-sender.cf
   ```
4. Test the LDAP query directly:
   ```
   docker exec ldap-web ldapsearch -H ldap://ldap-master:389 \
     -D "cn=admin,dc=company,dc=com" -w <password> \
     -b "dc=company,dc=com" "(&(mail=user@company.com)(IsMailMonitor=TRUE))"
   ```

### HR_MailIntercept record not appearing in iDempiere

1. Check the monitor is running:
   ```
   docker logs ldap-web | grep "Scanning Postfix"
   ```
2. Check for iDempiere API errors:
   ```
   docker logs ldap-web | grep "ERROR"
   ```
3. Verify `IDEMPIERE_URL` and credentials are correct.
4. Confirm the `hr_mailintercept` table exists in the iDempiere database.

### Complete/Void action fails in iDempiere

1. Check iDempiere logs for errors from `MMailIntercept`.
2. Verify `LDAP_BOX_URL` is set correctly in the System Configurator.
3. Test the FastAPI endpoint from within the iDempiere container:
   ```
   curl -X POST http://ldap-web:8000/api/v1/mail/release/<queue_id>
   ```
4. Verify the queue ID still exists in the Postfix hold queue:
   ```
   docker exec ldap-web postqueue -p
   ```
   If the message was already released or expired, `postsuper` will return an error.
