# Mail Intercept Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace misused `MX_RBL` with a dedicated `HR_MailIntercept` Document Model and reconfigure Postfix as a relay host that only intercepts outgoing mail from LDAP-monitored senders.

**Architecture:** Postfix uses `smtpd_recipient_restrictions` with a domain-based permit map to only HOLD mail destined for external recipients; relay authorization stays in `smtpd_relay_restrictions`. FastAPI `mail_monitor.py` polls the hold queue and POSTs to iDempiere's `HR_MailIntercept` model (new) instead of `MX_RBL`. The Java model `MMailIntercept` implements DocAction — `completeIt()` calls FastAPI release, `voidIt()` calls FastAPI drop.

**Tech Stack:** Python 3.12, FastAPI, httpx, pytest, Postfix (Debian package), Java 17, iDempiere OSGi, `java.net.http.HttpClient`

**Spec:** `docs/superpowers/specs/2026-03-16-mail-intercept-redesign.md`

---

## Chunk 1: ldap-in-a-box — Postfix + FastAPI

### Task 1: Update Postfix `main.cf` for relay host mode

**Files:**
- Modify: `backend/postfix/main.cf`

- [ ] **Step 1: Read current `main.cf`**

  Open `backend/postfix/main.cf`. Identify the lines to change:
  - Line containing `smtpd_relay_restrictions = ...`
  - Line containing `mydestination = ...`
  - Line containing `smtpd_sender_restrictions = ...`

- [ ] **Step 2: Apply changes**

  Replace the relevant lines so the file contains:

  ```
  smtpd_relay_restrictions = permit_mynetworks permit_sasl_authenticated defer_unauth_destination
  mydestination = localhost
  smtpd_recipient_restrictions =
      check_recipient_access hash:/etc/postfix/recipient_permit.cf,
      check_sender_access ldap:/etc/postfix/ldap-sender.cf
  ```

  Remove the old line:
  ```
  smtpd_sender_restrictions = check_sender_access ldap:/etc/postfix/ldap-sender.cf
  ```

  > **Why `mydestination = localhost`:** Pure relay host. Must not claim `@$DOMAIN` as local — otherwise Postfix resolves internal mail before reaching `smtpd_recipient_restrictions`, making the permit map ineffective.
  >
  > **Why no `permit_mynetworks/permit_sasl_authenticated` in `smtpd_recipient_restrictions`:** These already live in `smtpd_relay_restrictions` (relay authorization phase). Repeating them here would short-circuit the LDAP HOLD check for authenticated senders — exactly the users we want to monitor.

- [ ] **Step 3: Commit**

  ```bash
  cd /Users/ray/sources/docker/ldap-in-a-box
  git add backend/postfix/main.cf
  git commit -m "feat: reconfigure Postfix for relay host mode with recipient-based HOLD"
  ```

---

### Task 2: Update `entrypoint.sh` — mydomain, mydestination, recipient_permit.cf

**Files:**
- Modify: `backend/entrypoint.sh`

- [ ] **Step 1: Read current `entrypoint.sh`**

  Open `backend/entrypoint.sh`. Find the `# Configure Postfix hostname` block (around line 27):
  ```bash
  postconf -e "myhostname=$DOMAIN"
  postconf -e "maillog_file=/var/log/postfix.log"
  ```

- [ ] **Step 2: Insert new lines immediately after `postconf -e "myhostname=$DOMAIN"`**

  The block should become:

  ```bash
  # Configure Postfix hostname and relay host settings
  postconf -e "myhostname=$DOMAIN"
  postconf -e "mydomain=$DOMAIN"
  postconf -e "mydestination=localhost"
  postconf -e "maillog_file=/var/log/postfix.log"

  # Generate recipient permit map — PERMIT internal recipients, external ones proceed to LDAP check
  echo "@${DOMAIN}   PERMIT" > /etc/postfix/recipient_permit.cf
  postmap /etc/postfix/recipient_permit.cf
  ```

  > **Order matters:** `postmap` compiles `recipient_permit.cf` into a `.db` file that Postfix reads. This block must remain before `service postfix start` (which it already is, since `service postfix start` comes after this section).

- [ ] **Step 3: Commit**

  ```bash
  git add backend/entrypoint.sh
  git commit -m "feat: set mydomain/mydestination and generate recipient_permit.cf in entrypoint"
  ```

---

### Task 3: TDD — extend `parse_postcat_output()` to extract email body

**Files:**
- Modify: `backend/app/mail_monitor.py`
- Create: `backend/tests/test_mail_monitor.py`

- [ ] **Step 1: Write failing tests**

  Create `backend/tests/test_mail_monitor.py`:

  ```python
  import email
  from email.policy import default
  from unittest.mock import patch, MagicMock
  from app.mail_monitor import parse_postcat_output


  POSTCAT_PLAIN_ONLY = """
  *** MESSAGE CONTENTS ABC123 ***
  Content-Type: text/plain; charset="utf-8"
  From: sender@example.com
  To: recipient@external.com
  Subject: Test Subject

  This is plain text body.

  *** HEADER EXTRACTED ***
  """

  POSTCAT_MULTIPART = """
  *** MESSAGE CONTENTS ABC456 ***
  MIME-Version: 1.0
  From: sender@example.com
  To: recipient@external.com
  Subject: HTML Test
  Content-Type: multipart/alternative; boundary="boundary123"

  --boundary123
  Content-Type: text/plain; charset="utf-8"

  Plain text part.

  --boundary123
  Content-Type: text/html; charset="utf-8"

  <html><body>HTML part.</body></html>

  --boundary123--

  *** HEADER EXTRACTED ***
  """

  POSTCAT_NO_CONTENTS = "Some other postfix output without MESSAGE CONTENTS marker"


  def _mock_run(output, returncode=0):
      mock = MagicMock()
      mock.returncode = returncode
      mock.stdout = output
      mock.stderr = ""
      return mock


  def test_parse_returns_body_text_for_plain_email():
      with patch("app.mail_monitor.subprocess.run", return_value=_mock_run(POSTCAT_PLAIN_ONLY)):
          result = parse_postcat_output("ABC123")
      assert result is not None
      assert "body_text" in result
      assert "This is plain text body." in result["body_text"]


  def test_parse_returns_empty_body_html_for_plain_email():
      with patch("app.mail_monitor.subprocess.run", return_value=_mock_run(POSTCAT_PLAIN_ONLY)):
          result = parse_postcat_output("ABC123")
      assert result is not None
      assert "body_html" in result
      assert result["body_html"] == ""


  def test_parse_returns_both_body_parts_for_multipart():
      with patch("app.mail_monitor.subprocess.run", return_value=_mock_run(POSTCAT_MULTIPART)):
          result = parse_postcat_output("ABC456")
      assert result is not None
      assert "Plain text part." in result["body_text"]
      assert "<html>" in result["body_html"]


  def test_parse_returns_none_on_subprocess_failure():
      with patch("app.mail_monitor.subprocess.run", return_value=_mock_run("", returncode=1)):
          result = parse_postcat_output("BADID")
      assert result is None


  def test_parse_returns_none_when_no_message_contents_marker():
      with patch("app.mail_monitor.subprocess.run", return_value=_mock_run(POSTCAT_NO_CONTENTS)):
          result = parse_postcat_output("ABC789")
      assert result is None
  ```

- [ ] **Step 2: Run tests to verify they fail**

  ```bash
  cd /Users/ray/sources/docker/ldap-in-a-box/backend
  python -m pytest tests/test_mail_monitor.py -v
  ```

  Expected: `test_parse_returns_body_text_for_plain_email`, `test_parse_returns_empty_body_html_for_plain_email`, and `test_parse_returns_both_body_parts_for_multipart` will **FAIL** (key not present yet). The remaining 2 tests (`test_parse_returns_none_on_subprocess_failure` and `test_parse_returns_none_when_no_message_contents_marker`) will **PASS** — this is expected and correct, as they test existing error-path behavior.

- [ ] **Step 3: Implement body extraction in `parse_postcat_output()`**

  In `backend/app/mail_monitor.py`, update `parse_postcat_output()`. Find the line:
  ```python
  msg = email.message_from_string(raw_msg, policy=default)
  ```

  Replace the `return` dict below it with:

  ```python
  msg = email.message_from_string(raw_msg, policy=default)

  # Extract plain text body
  plain_part = msg.get_body(preferencelist=('plain',))
  body_text = plain_part.get_content() if plain_part else ""

  # Extract HTML body
  html_part = msg.get_body(preferencelist=('html',))
  body_html = html_part.get_content() if html_part else ""

  return {
      "queue_id": queue_id,
      "sender": msg.get("From", ""),
      "subject": msg.get("Subject", ""),
      "recipient": msg.get("To", ""),
      "body_text": body_text,
      "body_html": body_html,
  }
  ```

- [ ] **Step 4: Run tests to verify they pass**

  ```bash
  cd /Users/ray/sources/docker/ldap-in-a-box/backend
  python -m pytest tests/test_mail_monitor.py -v
  ```

  Expected: all 5 tests `PASSED`.

- [ ] **Step 5: Commit**

  ```bash
  cd /Users/ray/sources/docker/ldap-in-a-box
  git add backend/app/mail_monitor.py backend/tests/test_mail_monitor.py
  git commit -m "feat: extract body_text and body_html in parse_postcat_output"
  ```

---

### Task 4: TDD — update `push_to_idempiere()` for `HR_MailIntercept`

**Files:**
- Modify: `backend/app/mail_monitor.py`
- Modify: `backend/tests/test_mail_monitor.py`

- [ ] **Step 1: Write failing tests**

  Append to `backend/tests/test_mail_monitor.py` (add only the new import and test functions — do not repeat imports already at the top of the file):

  ```python
  from app.mail_monitor import push_to_idempiere


  def _make_mail_info(queue_id="QUEUE001"):
      return {
          "queue_id": queue_id,
          "sender": "Sender Name <sender@example.com>",
          "subject": "Test Subject",
          "recipient": "recipient@external.com",
          "body_text": "Plain body",
          "body_html": "<html>HTML body</html>",
      }


  def _mock_client(create_status=201):
      client = MagicMock()
      # Login response
      login_resp = MagicMock()
      login_resp.status_code = 200
      login_resp.json.return_value = {"token": "test-token"}
      # User lookup response
      user_resp = MagicMock()
      user_resp.status_code = 200
      user_resp.json.return_value = {"records": [{"AD_User_ID": 42}]}
      # Create record response
      create_resp = MagicMock()
      create_resp.status_code = create_status
      create_resp.text = ""
      client.__enter__ = MagicMock(return_value=client)
      client.__exit__ = MagicMock(return_value=False)
      client.post.side_effect = [login_resp, create_resp]
      client.get.return_value = user_resp
      return client


  def test_push_calls_hr_mailintercept_endpoint():
      client = _mock_client()
      with patch("app.mail_monitor.httpx.Client", return_value=client):
          push_to_idempiere(_make_mail_info())
      # The second POST call should be to hr_mailintercept
      create_call = client.post.call_args_list[1]
      assert "hr_mailintercept" in create_call[0][0]


  def test_push_payload_contains_required_fields():
      client = _mock_client()
      with patch("app.mail_monitor.httpx.Client", return_value=client):
          push_to_idempiere(_make_mail_info())
      payload = client.post.call_args_list[1][1]["json"]
      assert payload["SenderEmail"] == "sender@example.com"
      assert payload["Subject"] == "Test Subject"
      assert payload["Recipients"] == "recipient@external.com"
      assert payload["PostfixQueueID"] == "QUEUE001"
      assert payload["BodyText"] == "Plain body"
      assert payload["BodyHtml"] == "<html>HTML body</html>"
      assert payload["DocStatus"] == "DR"
      assert payload["DocAction"] == "--"
      assert "InterceptedDate" in payload
      assert payload["AD_User_ID"] == 42


  def test_push_handles_duplicate_gracefully():
      """409 or 400 from iDempiere (duplicate PostfixQueueID) should log and not raise."""
      client = _mock_client(create_status=409)
      with patch("app.mail_monitor.httpx.Client", return_value=client):
          # Should not raise
          push_to_idempiere(_make_mail_info())


  def test_push_handles_400_as_duplicate():
      client = _mock_client(create_status=400)
      with patch("app.mail_monitor.httpx.Client", return_value=client):
          push_to_idempiere(_make_mail_info())


  def test_push_strips_display_name_from_sender():
      """'Display Name <email@example.com>' -> 'email@example.com' for LDAP lookup and SenderEmail."""
      client = _mock_client()
      with patch("app.mail_monitor.httpx.Client", return_value=client):
          push_to_idempiere(_make_mail_info())
      payload = client.post.call_args_list[1][1]["json"]
      assert payload["SenderEmail"] == "sender@example.com"
  ```

- [ ] **Step 2: Run to verify they fail**

  ```bash
  cd /Users/ray/sources/docker/ldap-in-a-box/backend
  python -m pytest tests/test_mail_monitor.py::test_push_calls_hr_mailintercept_endpoint -v
  ```

  Expected: `FAILED` — current code calls `mx_rbl`, not `hr_mailintercept`.

- [ ] **Step 3: Rewrite `push_to_idempiere()` in `mail_monitor.py`**

  Replace the entire `push_to_idempiere` function with:

  ```python
  def push_to_idempiere(mail_info: dict):
      from datetime import datetime, timezone

      auth_payload = {
          "clientId": settings.IDEMPIERE_CLIENT_ID,
          "roleId": settings.IDEMPIERE_ROLE_ID,
          "organizationId": settings.IDEMPIERE_ORG_ID,
          "warehouseId": settings.IDEMPIERE_WAREHOUSE_ID,
          "userName": settings.IDEMPIERE_USER,
          "password": settings.IDEMPIERE_PASS
      }

      try:
          with httpx.Client(timeout=10.0) as client:
              login_resp = client.post(f"{settings.IDEMPIERE_URL}/api/v1/auth/tokens", json=auth_payload)
              if login_resp.status_code not in [200, 201]:
                  logger.error(f"iDempiere Login failed: {login_resp.text}")
                  return
              token = login_resp.json().get("token")

              headers = {
                  "Authorization": f"Bearer {token}",
                  "Content-Type": "application/json",
                  "Accept": "application/json"
              }

              # Extract bare email address from "Display Name <email>" format
              sender_email = mail_info["sender"]
              if "<" in sender_email and ">" in sender_email:
                  sender_email = sender_email.split("<")[1].split(">")[0]

              # Look up AD_User_ID by sender email
              user_resp = client.get(
                  f"{settings.IDEMPIERE_URL}/api/v1/models/ad_user?filter=email eq '{sender_email}'",
                  headers=headers
              )
              ad_user_id = None
              if user_resp.status_code == 200:
                  users = user_resp.json().get("records", [])
                  if users:
                      ad_user_id = users[0].get("AD_User_ID")

              # Create HR_MailIntercept document (Draft, no pending action)
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
                  logger.info(f"Created HR_MailIntercept for Queue ID: {mail_info['queue_id']}")
              elif create_resp.status_code in [400, 409]:
                  logger.debug(f"HR_MailIntercept already exists for Queue ID: {mail_info['queue_id']} — skipping duplicate")
              else:
                  logger.error(f"Failed to create HR_MailIntercept: {create_resp.text}")

      except Exception as e:
          logger.error(f"Error communicating with iDempiere: {e}")
  ```

- [ ] **Step 4: Run all mail_monitor tests**

  ```bash
  cd /Users/ray/sources/docker/ldap-in-a-box/backend
  python -m pytest tests/test_mail_monitor.py -v
  ```

  Expected: all tests `PASSED`.

- [ ] **Step 5: Run full test suite to check for regressions**

  ```bash
  cd /Users/ray/sources/docker/ldap-in-a-box/backend
  python -m pytest tests/ -v
  ```

  Expected: all tests pass.

- [ ] **Step 6: Commit**

  ```bash
  cd /Users/ray/sources/docker/ldap-in-a-box
  git add backend/app/mail_monitor.py backend/tests/test_mail_monitor.py
  git commit -m "feat: push to HR_MailIntercept instead of MX_RBL, handle duplicate 400/409"
  ```

---

### Chunk 1 Verification

After completing Tasks 1–4, manually verify in the running container:

```bash
# 1. Check recipient_permit.cf is generated correctly
docker exec ldap-web cat /etc/postfix/recipient_permit.cf
# Expected: @yourdomain.com   PERMIT

# 2. Check Postfix config was applied
docker exec ldap-web postconf smtpd_recipient_restrictions
docker exec ldap-web postconf mydestination
# Expected: mydestination = localhost

# 3. Send test email from monitored user to external domain (should be held)
docker exec ldap-web python test_postfix.py
docker exec ldap-web postqueue -p
# Expected: held message (!) for external recipient from monitored sender

# 4. Verify internal recipient is NOT held
#    Edit test_postfix.py to send from monitored user to an @yourdomain.com recipient,
#    then check postqueue -p shows no held (!) messages for that send.
docker exec ldap-web postqueue -p
# Expected: empty queue (internal recipient was permitted, not held)
```

---

## Chunk 2: tw.ninniku.hrm — Java Model

> **Working directory:** `/Users/ray/sources/tw.ninniku.hrm`
>
> **Note:** The tw.ninniku.hrm project is an iDempiere OSGi plugin. There is no standalone test framework — unit tests require a full iDempiere runtime. This chunk provides manual verification steps instead of automated tests.

### Task 5: Create `I_HR_MailIntercept.java`

**Files:**
- Create: `src/tw/ninniku/hrm/model/I_HR_MailIntercept.java`

- [ ] **Step 1: Create the interface file**

  Create `src/tw/ninniku/hrm/model/I_HR_MailIntercept.java`:

  ```java
  /******************************************************************************
   * Product: iDempiere ERP & CRM Smart Business Solution                       *
   * Copyright (C) 1999-2012 ComPiere, Inc. All Rights Reserved.                *
   * This program is free software, you can redistribute it and/or modify it    *
   * under the terms version 2 of the GNU General Public License as published   *
   * by the Free Software Foundation. This program is distributed in the hope   *
   * that it will be useful, but WITHOUT ANY WARRANTY, without even the implied *
   * warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.           *
   * See the GNU General Public License for more details.                       *
   * You should have received a copy of the GNU General Public License along    *
   * with this program, if not, write to the Free Software Foundation, Inc.,    *
   * 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA.                     *
   *****************************************************************************/
  package tw.ninniku.hrm.model;

  import java.sql.Timestamp;
  import org.compiere.model.*;
  import org.compiere.util.KeyNamePair;

  /** Generated Interface for HR_MailIntercept
   *  @author iDempiere (generated)
   *  @version Release 6.2
   */
  @SuppressWarnings("all")
  public interface I_HR_MailIntercept
  {
      /** TableName=HR_MailIntercept */
      public static final String Table_Name = "HR_MailIntercept";

      /** AD_Table_ID (set after iDempiere dictionary registration) */
      public static final int Table_ID = MTable.getTable_ID(Table_Name);

      KeyNamePair Model = new KeyNamePair(Table_ID, Table_Name);

      /** AccessLevel = 3 - Client - Org */
      java.math.BigDecimal accessLevel = java.math.BigDecimal.valueOf(3);

      // -------------------------------------------------------------------------
      // Standard columns
      // -------------------------------------------------------------------------

      /** Column name AD_Client_ID */
      public static final String COLUMNNAME_AD_Client_ID = "AD_Client_ID";
      public int getAD_Client_ID();

      /** Column name AD_Org_ID */
      public static final String COLUMNNAME_AD_Org_ID = "AD_Org_ID";
      public void setAD_Org_ID(int AD_Org_ID);
      public int getAD_Org_ID();

      /** Column name Created */
      public static final String COLUMNNAME_Created = "Created";
      public Timestamp getCreated();

      /** Column name CreatedBy */
      public static final String COLUMNNAME_CreatedBy = "CreatedBy";
      public int getCreatedBy();

      /** Column name IsActive */
      public static final String COLUMNNAME_IsActive = "IsActive";
      public void setIsActive(boolean IsActive);
      public boolean isActive();

      /** Column name Updated */
      public static final String COLUMNNAME_Updated = "Updated";
      public Timestamp getUpdated();

      /** Column name UpdatedBy */
      public static final String COLUMNNAME_UpdatedBy = "UpdatedBy";
      public int getUpdatedBy();

      // -------------------------------------------------------------------------
      // Primary key
      // -------------------------------------------------------------------------

      /** Column name HR_MailIntercept_ID */
      public static final String COLUMNNAME_HR_MailIntercept_ID = "HR_MailIntercept_ID";
      public void setHR_MailIntercept_ID(int HR_MailIntercept_ID);
      public int getHR_MailIntercept_ID();

      /** Column name HR_MailIntercept_UU */
      public static final String COLUMNNAME_HR_MailIntercept_UU = "HR_MailIntercept_UU";
      public void setHR_MailIntercept_UU(String HR_MailIntercept_UU);
      public String getHR_MailIntercept_UU();

      // -------------------------------------------------------------------------
      // Business columns
      // -------------------------------------------------------------------------

      /** Column name AD_User_ID */
      public static final String COLUMNNAME_AD_User_ID = "AD_User_ID";
      public void setAD_User_ID(int AD_User_ID);
      public int getAD_User_ID();

      /** Column name SenderEmail */
      public static final String COLUMNNAME_SenderEmail = "SenderEmail";
      public void setSenderEmail(String SenderEmail);
      public String getSenderEmail();

      /** Column name Recipients */
      public static final String COLUMNNAME_Recipients = "Recipients";
      public void setRecipients(String Recipients);
      public String getRecipients();

      /** Column name Subject */
      public static final String COLUMNNAME_Subject = "Subject";
      public void setSubject(String Subject);
      public String getSubject();

      /** Column name PostfixQueueID */
      public static final String COLUMNNAME_PostfixQueueID = "PostfixQueueID";
      public void setPostfixQueueID(String PostfixQueueID);
      public String getPostfixQueueID();

      /** Column name InterceptedDate */
      public static final String COLUMNNAME_InterceptedDate = "InterceptedDate";
      public void setInterceptedDate(Timestamp InterceptedDate);
      public Timestamp getInterceptedDate();

      /** Column name BodyText */
      public static final String COLUMNNAME_BodyText = "BodyText";
      public void setBodyText(String BodyText);
      public String getBodyText();

      /** Column name BodyHtml */
      public static final String COLUMNNAME_BodyHtml = "BodyHtml";
      public void setBodyHtml(String BodyHtml);
      public String getBodyHtml();

      // -------------------------------------------------------------------------
      // Document columns
      // -------------------------------------------------------------------------

      /** Column name DocStatus */
      public static final String COLUMNNAME_DocStatus = "DocStatus";
      public void setDocStatus(String DocStatus);
      public String getDocStatus();

      /** Column name DocAction */
      public static final String COLUMNNAME_DocAction = "DocAction";
      public void setDocAction(String DocAction);
      public String getDocAction();

      /** Column name Processed */
      public static final String COLUMNNAME_Processed = "Processed";
      public void setProcessed(boolean Processed);
      public boolean isProcessed();
  }
  ```

- [ ] **Step 2: Commit**

  ```bash
  cd /Users/ray/sources/tw.ninniku.hrm
  git add src/tw/ninniku/hrm/model/I_HR_MailIntercept.java
  git commit -m "feat: add I_HR_MailIntercept interface"
  ```

---

### Task 6: Create `X_HR_MailIntercept.java`

**Files:**
- Create: `src/tw/ninniku/hrm/model/X_HR_MailIntercept.java`

- [ ] **Step 1: Create the generated base class**

  Create `src/tw/ninniku/hrm/model/X_HR_MailIntercept.java`:

  ```java
  /******************************************************************************
   * Product: iDempiere ERP & CRM Smart Business Solution                       *
   * Copyright (C) 1999-2012 ComPiere, Inc. All Rights Reserved.                *
   * This program is free software, you can redistribute it and/or modify it    *
   * under the terms version 2 of the GNU General Public License as published   *
   * by the Free Software Foundation. This program is distributed in the hope   *
   * that it will be useful, but WITHOUT ANY WARRANTY, without even the implied *
   * warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.           *
   * See the GNU General Public License for more details.                       *
   * You should have received a copy of the GNU General Public License along    *
   * with this program, if not, write to the Free Software Foundation, Inc.,    *
   * 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA.                     *
   *****************************************************************************/
  /** Generated Model - DO NOT CHANGE */
  package tw.ninniku.hrm.model;

  import java.sql.ResultSet;
  import java.sql.Timestamp;
  import java.util.Properties;
  import org.compiere.model.*;

  /** Generated Model for HR_MailIntercept
   *  @author iDempiere (generated)
   *  @version Release 6.2 - $Id$ */
  public class X_HR_MailIntercept extends PO implements I_HR_MailIntercept, I_Persistent
  {
      private static final long serialVersionUID = 20260316L;

      /** Standard Constructor */
      public X_HR_MailIntercept(Properties ctx, int HR_MailIntercept_ID, String trxName)
      {
          super(ctx, HR_MailIntercept_ID, trxName);
      }

      /** Load Constructor */
      public X_HR_MailIntercept(Properties ctx, ResultSet rs, String trxName)
      {
          super(ctx, rs, trxName);
      }

      /** AccessLevel */
      protected int get_AccessLevel()
      {
          return accessLevel.intValue();
      }

      /** Load Meta Data */
      protected POInfo initPO(Properties ctx)
      {
          POInfo poi = POInfo.getPOInfo(ctx, Table_ID, get_TrxName());
          return poi;
      }

      public String toString()
      {
          return new StringBuffer("X_HR_MailIntercept[")
              .append(get_ID()).append("]").toString();
      }

      // -------------------------------------------------------------------------
      // Primary key
      // -------------------------------------------------------------------------

      public void setHR_MailIntercept_ID(int HR_MailIntercept_ID)
      {
          if (HR_MailIntercept_ID < 1)
              set_ValueNoCheck(COLUMNNAME_HR_MailIntercept_ID, null);
          else
              set_ValueNoCheck(COLUMNNAME_HR_MailIntercept_ID, Integer.valueOf(HR_MailIntercept_ID));
      }

      public int getHR_MailIntercept_ID()
      {
          Integer ii = (Integer) get_Value(COLUMNNAME_HR_MailIntercept_ID);
          return ii == null ? 0 : ii.intValue();
      }

      public void setHR_MailIntercept_UU(String HR_MailIntercept_UU)
      {
          set_Value(COLUMNNAME_HR_MailIntercept_UU, HR_MailIntercept_UU);
      }

      public String getHR_MailIntercept_UU()
      {
          return (String) get_Value(COLUMNNAME_HR_MailIntercept_UU);
      }

      // -------------------------------------------------------------------------
      // Business columns
      // -------------------------------------------------------------------------

      public void setAD_User_ID(int AD_User_ID)
      {
          if (AD_User_ID < 1)
              set_Value(COLUMNNAME_AD_User_ID, null);
          else
              set_Value(COLUMNNAME_AD_User_ID, Integer.valueOf(AD_User_ID));
      }

      public int getAD_User_ID()
      {
          Integer ii = (Integer) get_Value(COLUMNNAME_AD_User_ID);
          return ii == null ? 0 : ii.intValue();
      }

      public void setSenderEmail(String SenderEmail)
      {
          set_Value(COLUMNNAME_SenderEmail, SenderEmail);
      }

      public String getSenderEmail()
      {
          return (String) get_Value(COLUMNNAME_SenderEmail);
      }

      public void setRecipients(String Recipients)
      {
          set_Value(COLUMNNAME_Recipients, Recipients);
      }

      public String getRecipients()
      {
          return (String) get_Value(COLUMNNAME_Recipients);
      }

      public void setSubject(String Subject)
      {
          set_Value(COLUMNNAME_Subject, Subject);
      }

      public String getSubject()
      {
          return (String) get_Value(COLUMNNAME_Subject);
      }

      public void setPostfixQueueID(String PostfixQueueID)
      {
          set_Value(COLUMNNAME_PostfixQueueID, PostfixQueueID);
      }

      public String getPostfixQueueID()
      {
          return (String) get_Value(COLUMNNAME_PostfixQueueID);
      }

      public void setInterceptedDate(Timestamp InterceptedDate)
      {
          set_Value(COLUMNNAME_InterceptedDate, InterceptedDate);
      }

      public Timestamp getInterceptedDate()
      {
          return (Timestamp) get_Value(COLUMNNAME_InterceptedDate);
      }

      public void setBodyText(String BodyText)
      {
          set_Value(COLUMNNAME_BodyText, BodyText);
      }

      public String getBodyText()
      {
          return (String) get_Value(COLUMNNAME_BodyText);
      }

      public void setBodyHtml(String BodyHtml)
      {
          set_Value(COLUMNNAME_BodyHtml, BodyHtml);
      }

      public String getBodyHtml()
      {
          return (String) get_Value(COLUMNNAME_BodyHtml);
      }

      // -------------------------------------------------------------------------
      // Document columns
      // -------------------------------------------------------------------------

      public void setDocStatus(String DocStatus)
      {
          set_Value(COLUMNNAME_DocStatus, DocStatus);
      }

      public String getDocStatus()
      {
          return (String) get_Value(COLUMNNAME_DocStatus);
      }

      public void setDocAction(String DocAction)
      {
          set_Value(COLUMNNAME_DocAction, DocAction);
      }

      public String getDocAction()
      {
          return (String) get_Value(COLUMNNAME_DocAction);
      }

      public void setProcessed(boolean Processed)
      {
          set_Value(COLUMNNAME_Processed, Boolean.valueOf(Processed));
      }

      public boolean isProcessed()
      {
          Object oo = get_Value(COLUMNNAME_Processed);
          if (oo instanceof Boolean)
              return (Boolean) oo;
          return "Y".equals(oo);
      }
  }
  ```

- [ ] **Step 2: Commit**

  ```bash
  cd /Users/ray/sources/tw.ninniku.hrm
  git add src/tw/ninniku/hrm/model/X_HR_MailIntercept.java
  git commit -m "feat: add X_HR_MailIntercept generated base class"
  ```

---

### Task 7: Create `MMailIntercept.java`

**Files:**
- Create: `src/tw/ninniku/hrm/model/MMailIntercept.java`

- [ ] **Step 1: Create the model class**

  Create `src/tw/ninniku/hrm/model/MMailIntercept.java`:

  ```java
  package tw.ninniku.hrm.model;

  import java.io.File;
  import java.math.BigDecimal;
  import java.net.URI;
  import java.net.http.HttpClient;
  import java.net.http.HttpRequest;
  import java.net.http.HttpResponse;
  import java.sql.ResultSet;
  import java.util.Properties;
  import java.util.logging.Level;

  import org.compiere.model.MSysConfig;
  import org.compiere.process.DocAction;
  import org.compiere.process.DocOptions;
  import org.compiere.process.DocumentEngine;
  import org.compiere.util.CLogger;
  import org.compiere.util.Env;

  /**
   * HR_MailIntercept — iDempiere Document Model for email interception approval workflow.
   *
   * Lifecycle:
   *   - Created in DR (Draft) status by FastAPI mail_monitor when a monitored sender's
   *     outgoing email is held by Postfix.
   *   - Human approver sets DocAction=CO (approve) → completeIt() releases the held email.
   *   - Human approver sets DocAction=VO (reject/void) → voidIt() drops the held email.
   *
   * FastAPI URL is read from iDempiere System Configurator property "LDAP_BOX_URL".
   * Configure at: iDempiere → System → System Configurator → LDAP_BOX_URL
   */
  public class MMailIntercept extends X_HR_MailIntercept implements DocAction, DocOptions
  {
      private static final long serialVersionUID = 20260316L;
      private static final CLogger log = CLogger.getCLogger(MMailIntercept.class);

      /** <None> = -- */
      public static final String DOCACTION_None = "--";

      /** Default FastAPI base URL if AD_SysConfig not configured */
      private static final String DEFAULT_LDAP_BOX_URL = "http://ldap-web:8000";

      public MMailIntercept(Properties ctx, int HR_MailIntercept_ID, String trxName)
      {
          super(ctx, HR_MailIntercept_ID, trxName);
      }

      public MMailIntercept(Properties ctx, ResultSet rs, String trxName)
      {
          super(ctx, rs, trxName);
      }

      // -------------------------------------------------------------------------
      // DocAction — processIt delegates to DocumentEngine (standard iDempiere pattern)
      // -------------------------------------------------------------------------

      @Override
      public boolean processIt(String action) throws Exception
      {
          DocumentEngine engine = new DocumentEngine(this, getDocStatus());
          return engine.processIt(action, getDocAction());
      }

      @Override
      public boolean unlockIt()        { return true; }

      @Override
      public boolean invalidateIt()    { return false; }

      /**
       * Prepare — validate required fields.
       * @return DocAction.STATUS_InProgress on success, DocAction.STATUS_Invalid on failure.
       */
      @Override
      public String prepareIt()
      {
          if (getSenderEmail() == null || getSenderEmail().isEmpty())
              return DocAction.STATUS_Invalid;
          if (getPostfixQueueID() == null || getPostfixQueueID().isEmpty())
              return DocAction.STATUS_Invalid;
          return DocAction.STATUS_InProgress;
      }

      @Override
      public boolean approveIt()       { return false; }

      @Override
      public boolean rejectIt()        { return voidIt(); }

      /**
       * Complete — APPROVE: release the held email via FastAPI, then mark document Completed.
       */
      @Override
      public String completeIt()
      {
          String status = prepareIt();
          if (!DocAction.STATUS_InProgress.equals(status))
              return status;

          if (!callFastApi(getLdapBoxUrl() + "/api/v1/mail/release/" + getPostfixQueueID(), "release"))
              return DocAction.STATUS_Invalid;

          setProcessed(true);
          setDocAction(DOCACTION_None);
          return DocAction.STATUS_Completed;
      }

      /**
       * Void — REJECT: drop the held email via FastAPI, then mark document Voided.
       */
      @Override
      public boolean voidIt()
      {
          if (!callFastApi(getLdapBoxUrl() + "/api/v1/mail/drop/" + getPostfixQueueID(), "drop"))
              return false;
          setProcessed(true);
          setDocAction(DOCACTION_None);
          setDocStatus(DocAction.STATUS_Voided);
          return true;
      }

      @Override
      public boolean closeIt()         { return false; }

      @Override
      public boolean reverseCorrectIt(){ return false; }

      @Override
      public boolean reverseAccrualIt(){ return false; }

      @Override
      public boolean reActivateIt()    { return false; }

      // -------------------------------------------------------------------------
      // DocAction info methods
      // -------------------------------------------------------------------------

      @Override
      public String getSummary()       { return getSenderEmail() + " → " + getSubject(); }

      @Override
      public String getDocumentNo()    { return getPostfixQueueID(); }

      @Override
      public String getDocumentInfo()  { return "MailIntercept[" + getPostfixQueueID() + "]"; }

      @Override
      public File createPDF()          { return null; }

      @Override
      public String getProcessMsg()    { return null; }

      @Override
      public int getDoc_User_ID()      { return getAD_User_ID(); }

      @Override
      public int getC_Currency_ID()    { return 0; }

      @Override
      public BigDecimal getApprovalAmt() { return null; }

      // -------------------------------------------------------------------------
      // DocOptions — controls which action buttons appear in the iDempiere UI
      // -------------------------------------------------------------------------

      @Override
      public int customizeValidActions(String docStatus, Object processing,
              String orderType, String isSOTrx, int AD_Table_ID,
              String[] docAction, String[] options, int index)
      {
          if (options == null)  throw new IllegalArgumentException("options array is null");
          if (docAction == null) throw new IllegalArgumentException("docAction array is null");

          // DR or Invalid: show Approve (Complete) and Reject (Void)
          if (docStatus.equals(DocumentEngine.STATUS_Drafted)
                  || docStatus.equals(DocumentEngine.STATUS_Invalid))
          {
              options[index++] = DocumentEngine.ACTION_Complete;
              options[index++] = DocumentEngine.ACTION_Void;
          }
          // InProgress: show same options
          else if (docStatus.equals(DocumentEngine.STATUS_InProgress))
          {
              options[index++] = DocumentEngine.ACTION_Complete;
              options[index++] = DocumentEngine.ACTION_Void;
          }
          // Completed or Voided: no further actions
          return index;
      }

      // -------------------------------------------------------------------------
      // Internal helpers
      // -------------------------------------------------------------------------

      /**
       * Reads LDAP_BOX_URL from iDempiere System Configurator.
       * To configure: iDempiere → System → System Configurator → add key "LDAP_BOX_URL"
       */
      private String getLdapBoxUrl()
      {
          return MSysConfig.getValue("LDAP_BOX_URL", DEFAULT_LDAP_BOX_URL,
                  Env.getAD_Client_ID(getCtx()));
      }

      /**
       * POSTs to a FastAPI endpoint (no body, no auth — internal Docker network only).
       * @return true if HTTP 2xx received
       */
      private boolean callFastApi(String url, String action)
      {
          try {
              HttpClient httpClient = HttpClient.newHttpClient();
              HttpRequest request = HttpRequest.newBuilder()
                  .uri(URI.create(url))
                  .POST(HttpRequest.BodyPublishers.noBody())
                  .build();
              HttpResponse<String> response =
                  httpClient.send(request, HttpResponse.BodyHandlers.ofString());

              if (response.statusCode() >= 200 && response.statusCode() < 300) {
                  log.info("FastAPI " + action + " succeeded for queue ID: " + getPostfixQueueID());
                  return true;
              } else {
                  log.warning("FastAPI " + action + " failed (HTTP "
                          + response.statusCode() + "): " + response.body());
                  return false;
              }
          } catch (Exception e) {
              log.log(Level.SEVERE, "FastAPI " + action + " error: " + e.getMessage(), e);
              return false;
          }
      }
  }
  ```

- [ ] **Step 2: Verify the file compiles**

  In your IDE (Eclipse/IntelliJ with iDempiere SDK), build the `tw.ninniku.hrm` plugin:
  - Right-click project → Build Project
  - Expected: no compilation errors

  If `DocAction` import path differs in your iDempiere version, check other M_ classes in the project for the correct import (e.g., `org.compiere.process.DocAction` vs `org.compiere.model.DocAction`).

- [ ] **Step 3: Commit**

  ```bash
  cd /Users/ray/sources/tw.ninniku.hrm
  git add src/tw/ninniku/hrm/model/MMailIntercept.java
  git commit -m "feat: add MMailIntercept DocAction model with release/drop via FastAPI"
  ```

---

### Chunk 2 Manual Verification

After completing Tasks 5–7 and registering `HR_MailIntercept` in the iDempiere Application Dictionary (out of scope — must be done separately):

1. Create a test `HR_MailIntercept` record in iDempiere with a known `PostfixQueueID`.
2. Set `DocAction = CO` → verify `postqueue -p` shows the message is no longer held.
3. Create another record, set `DocAction = VO` → verify message is gone from queue.
4. Check iDempiere logs for `FastAPI release/drop succeeded` messages.

---

## Post-Implementation Notes

- **iDempiere Application Dictionary** registration (Table, Columns, Window, Tab, Fields for `HR_MailIntercept`) must be done as a separate task — this plan covers only the Java model code.
- **Database migration SQL** (`CREATE TABLE HR_MailIntercept ...`) must be created as an iDempiere migration script separately.
- **`LDAP_BOX_URL`** must be configured in iDempiere System Configurator before testing `MMailIntercept`.
- The old `MX_RBL` Java files (`I_MX_RBL.java`, `X_MX_RBL.java`, `MRealtimeBlockList.java`) are intentionally kept — do not remove.
