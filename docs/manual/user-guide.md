# Mail Intercept — User Guide

## Overview

The Mail Intercept system automatically holds outgoing emails sent by employees who are marked for monitoring. When a monitored employee sends an email to an external address, the email is put on hold and a review record appears in iDempiere for an HR manager to approve or reject.

The email is not delivered until a manager takes action. If no action is taken, the email remains held indefinitely.

---

## Enabling Monitoring for an Employee

To place an employee's outgoing email under interception, set the **Mail Monitor** flag on their LDAP user record.

### Option A — iDempiere LDAP Manager (recommended)

1. In iDempiere, open **LDAP Manager**.
2. Go to the **Users** tab and locate the employee (use the search bar or VPN/Mail Monitor filter checkboxes).
3. Double-click the employee row to open **User Detail**.
4. Check **Mail Monitor**.
5. Click **Save**.

The flag is written to LDAP (`IsMailMonitor=Y`) and synced back to `AD_User` in the same operation.

### Option B — LDAP-in-a-Box Admin UI

1. Navigate to the employee's user entry in the LDAP tree.
2. Add or set the attribute `IsMailMonitor` to `TRUE`.
3. Save the entry.

---

The change takes effect immediately — the next email the employee sends to an external address will be held.

To stop monitoring, uncheck **Mail Monitor** in LDAP Manager (or set `IsMailMonitor` to `FALSE` in the LDAP tree) and save.

---

## Dashboard — Held Mail Queue Panel

The Dashboard provides a live view of the Postfix hold queue without opening iDempiere. It refreshes automatically every 30 seconds.

### Reading the Panel

| State | Display |
|-------|---------|
| Messages held | Red panel — "⚠ Held Mail Queue" with a count badge and a table of messages |
| Queue empty | Green panel — "✓ Queue Clear" |

Each row in the table shows: **Sender**, **Recipient**, **Subject**, and action buttons.

### Quick Actions from the Dashboard

Two action buttons appear on each held message row:

| Button | Symbol | Effect |
|--------|--------|--------|
| Release | ✓ (green) | Releases the email for immediate delivery |
| Drop | ✕ (red) | Permanently deletes the email from the queue |

Both buttons are disabled while another action is in progress. A **Refresh** button in the panel header triggers an immediate poll (the spinner appears while loading).

> **Note:** The Dashboard actions bypass the iDempiere review workflow — use them for quick corrections (e.g., a false positive). For formal audit-trail approvals and rejections, use the HR Mail Intercept window in iDempiere.

---

## Reviewing Intercepted Emails

When a monitored employee sends an external email, iDempiere creates an **HR Mail Intercept** record in Draft (`DR`) status. The record contains:

| Field | Description |
|-------|-------------|
| Sender Email | The email address of the monitored employee |
| Recipients | The To: address(es) of the held email |
| Subject | The email subject line |
| Intercepted Date | When the email was held by the system |
| Body Text | Plain-text content of the email |
| Body HTML | HTML content of the email (if the email was formatted) |
| Postfix Queue ID | Internal system identifier (for reference) |

To find pending records in iDempiere:

1. Open the **HR Mail Intercept** window.
2. Filter by **Doc Status = DR** (Draft) to see emails awaiting review.
3. Click a record to open it and read the full email content.

---

## Approving an Email (Release)

To approve an intercepted email and allow it to be delivered:

1. Open the HR Mail Intercept record.
2. In the document action toolbar, select **Complete**.
3. Confirm the action.

The system will immediately release the email from the hold queue and attempt delivery. The record status changes to **Completed**.

---

## Rejecting an Email (Drop)

To reject an intercepted email and permanently discard it:

1. Open the HR Mail Intercept record.
2. In the document action toolbar, select **Void**.
3. Confirm the action.

The email is permanently deleted from the queue and will never be delivered. The record status changes to **Voided**. This action cannot be undone.

---

## What Happens After Action

| Action | Email outcome | Record status |
|--------|--------------|---------------|
| Complete (Approve) | Delivered to recipient(s) | Completed |
| Void (Reject) | Permanently deleted | Voided |

---

## Scope of Interception

Only **outgoing** emails are intercepted — emails sent to addresses outside the company domain. Internal emails (sent to colleagues at the same domain) are **not** held.

---

## Troubleshooting

**The email is not showing up in iDempiere.**

The background monitor checks for held emails every 30 seconds. Wait up to one minute after the email was sent. If it still does not appear, check the container logs:

```
docker logs ldap-web | grep mail_monitor
```

Look for lines like `Intercepted mail from ... to ...` or errors from `app.mail_monitor`.

**The Complete or Void button is not visible.**

The action buttons only appear when the record is in Draft (`DR`) or In Progress (`IP`) status. If the record is already Completed or Voided, no further actions are available.

**An email was approved but the recipient says they never received it.**

Check that the Postfix `relayhost` environment variable is configured correctly for your network. If `relayhost` is empty, Postfix attempts direct MX delivery, which may fail in environments with outbound port-25 restrictions.
