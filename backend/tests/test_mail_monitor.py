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
