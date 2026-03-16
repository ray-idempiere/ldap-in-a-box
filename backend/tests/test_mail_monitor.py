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


# ── GET /mail/queue ──────────────────────────────────────────────────────────
from fastapi.testclient import TestClient
from app.main import app as fastapi_app

_queue_client = TestClient(fastapi_app)

POSTCAT_QUEUE_MSG = """
*** MESSAGE CONTENTS Q001 ***
From: alice@company.com
To: partner@ext.com
Subject: Q3 Report

Body text.

*** HEADER EXTRACTED ***
"""


def _mock_postqueue_p(queue_ids):
    """Return a mock subprocess result for postqueue -p listing held IDs."""
    lines = "\n".join(f"{qid}!  some info" for qid in queue_ids)
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = lines
    mock.stderr = ""
    return mock


def test_queue_endpoint_returns_messages():
    with patch("app.mail_monitor.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _mock_postqueue_p(["Q001"]),
            _mock_run(POSTCAT_QUEUE_MSG),
        ]
        resp = _queue_client.get("/api/v1/mail/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["messages"][0]["queue_id"] == "Q001"
    assert data["messages"][0]["sender"] == "alice@company.com"
    assert data["messages"][0]["recipient"] == "partner@ext.com"
    assert data["messages"][0]["subject"] == "Q3 Report"


def test_queue_endpoint_returns_empty_when_no_held_mail():
    with patch("app.mail_monitor.subprocess.run") as mock_run:
        mock_run.return_value = _mock_postqueue_p([])
        resp = _queue_client.get("/api/v1/mail/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["messages"] == []


def test_queue_endpoint_skips_messages_that_fail_to_parse():
    """parse_postcat_output returns None on error — those queue IDs must be silently skipped."""
    with patch("app.mail_monitor.subprocess.run") as mock_run:
        mock_run.side_effect = [
            _mock_postqueue_p(["GOOD1", "BAD2"]),
            _mock_run(POSTCAT_QUEUE_MSG),   # GOOD1 parses OK
            _mock_run("", returncode=1),    # BAD2 fails → None
        ]
        resp = _queue_client.get("/api/v1/mail/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["messages"][0]["queue_id"] == "GOOD1"
