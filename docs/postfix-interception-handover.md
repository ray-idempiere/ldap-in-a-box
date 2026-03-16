# Handover: Postfix Email Interception & iDempiere Integration

## 1. Overview
This system implements a compliant email interception workflow. Outgoing emails from users marked with `IsMailMonitor='Y'` in LDAP are automatically held by Postfix and forwarded to iDempiere ERP for workflow approval.

## 2. Architecture
- **Postfix Engine**: Hosted inside the `ldap-web` (FastAPI) container to allow direct queue management via system commands.
- **Relay Host Mode**: Postfix is configured as a relay host. Only outgoing mail (recipient domain ≠ `$LDAP_DOMAIN`) is subject to the `IsMailMonitor` LDAP check. Internal recipients are short-circuited via `recipient_permit.cf`.
- **LDAP Interceptor**: Uses `postfix-ldap` to perform real-time lookups on the `IsMailMonitor` attribute at `RCPT TO:` phase via `smtpd_recipient_restrictions`.
- **Background Monitor**: A Python service (`app/mail_monitor.py`) running via `APScheduler` inside FastAPI that polls the Postfix hold queue every 30 seconds.
- **REST Integration**: Communicates with iDempiere via standard REST API to create approval records (`HR_MailIntercept`).

## 3. Configuration Files
- **`backend/entrypoint.sh`**: Handles startup logic, generates `/etc/mailname`, configures Postfix LDAP lookups, sets `mydestination=localhost` for relay mode, and generates `recipient_permit.cf` before Postfix starts.
- **`backend/postfix/main.cf`**: Main Postfix config; defines `smtpd_recipient_restrictions` to permit internal recipients and trigger the LDAP check for external recipients.
- **`backend/postfix/ldap-sender.cf`**: Defines the LDAP query logic for identifying monitored users. Generated at runtime by `entrypoint.sh` — not copied from a static file.

## 4. Postfix Relay Host Configuration

`smtpd_recipient_restrictions` (evaluated at `RCPT TO:` phase):
1. `check_recipient_access hash:/etc/postfix/recipient_permit.cf` — `@$DOMAIN` recipients get `PERMIT` immediately (internal mail, no monitoring needed).
2. `check_sender_access ldap:/etc/postfix/ldap-sender.cf` — external recipients fall through; if the sender has `IsMailMonitor=TRUE` in LDAP, Postfix issues `HOLD`.

`smtpd_relay_restrictions = permit_mynetworks permit_sasl_authenticated defer_unauth_destination` governs relay authorization separately. Monitored senders are SASL-authenticated and pass through this phase before recipient restrictions apply.

## 5. iDempiere Integration Points
When a mail is intercepted, the system:
1. Finds the `AD_User_ID` via `GET /api/v1/models/AD_User?filter=EMail eq '...'`.
2. Creates a record in `HR_MailIntercept` via `POST /api/v1/models/hr_mailintercept`.
3. The payload includes: `SenderEmail`, `Recipients`, `Subject`, `PostfixQueueID` (unique — prevents duplicate records), `InterceptedDate`, `BodyText`, `BodyHtml`, `DocStatus=DR`, `DocAction=--`.

The human approver reviews the record in iDempiere and takes one of two actions:
- **Complete (CO)**: Approves — `MMailIntercept.completeIt()` calls FastAPI to release the held email.
- **Void (VO)**: Rejects — `MMailIntercept.voidIt()` calls FastAPI to drop the held email.

## 6. Control APIs
FastAPI provides two endpoints for iDempiere to call once a decision is made:
- **Release (Approve)**: `POST /api/v1/mail/release/{queue_id}`
  - Executes `postsuper -H {queue_id}` to move mail to active queue, then `postqueue -f` to flush for immediate delivery.
- **Drop (Reject)**: `POST /api/v1/mail/drop/{queue_id}`
  - Executes `postsuper -d {queue_id}` to delete the email from the queue.

These endpoints are unauthenticated by design — they must only be reachable within the Docker internal network (not exposed externally).

## 7. Monitoring & Troubleshooting
- **Logs**: View logs with `docker logs ldap-web`. Look for `app.mail_monitor` for background task status.
- **Postfix Queue**: Run `docker exec ldap-web postqueue -p` to see held messages (indicated by a `!` suffix).
- **Manual Debug**: Use `docker exec ldap-web postcat -q {queue_id}` to inspect the full content of a held email.

## 8. Environment Variables
Ensure the following are set in the environment:
- `LDAP_DOMAIN`: Used for `/etc/mailname` and `recipient_permit.cf`.
- `LDAP_HOST`, `LDAP_PORT`, `LDAP_ADMIN_PASSWORD`: Used to generate `ldap-sender.cf` at startup.
- `IDEMPIERE_URL`: Base URL for REST API.
- `IDEMPIERE_USER` / `IDEMPIERE_PASS`: API Credentials.
- `IDEMPIERE_CLIENT_ID`, `IDEMPIERE_ROLE_ID`, `IDEMPIERE_ORG_ID`, `IDEMPIERE_WAREHOUSE_ID`: iDempiere context for API authentication.

## 9. Post-Integration Requirements (Out of Scope for This PR)
- **iDempiere Application Dictionary** registration (Table, Columns, Window, Tab, Fields for `HR_MailIntercept`) must be done in iDempiere.
- **Database migration SQL** (`CREATE TABLE HR_MailIntercept ...`) must be created as an iDempiere migration script.
- **`LDAP_BOX_URL`** must be configured in iDempiere System Configurator so `MMailIntercept` can call back to FastAPI.
- **Docker network** must ensure port 8000 is not exposed externally (release/drop endpoints are unauthenticated).
