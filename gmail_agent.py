"""Gmail agent for sending outreach emails to leads."""

from __future__ import annotations

import base64
import logging
from email.mime.text import MIMEText
from html import escape as html_escape

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

import config
from models import Lead

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

_MAX_SUBJECT_LENGTH = 200
_MAX_BODY_LENGTH = 50_000


class GmailAgentError(Exception):
    """Raised for Gmail operation failures."""


class GmailAgent:
    """Sends outreach emails via the Gmail API."""

    def __init__(self) -> None:
        try:
            creds = Credentials.from_service_account_file(
                config.GMAIL_CREDENTIALS_FILE, scopes=_SCOPES
            )
            delegated = creds.with_subject(config.GMAIL_SENDER_EMAIL)
            self._service = build("gmail", "v1", credentials=delegated)
        except FileNotFoundError:
            raise GmailAgentError(
                f"Credentials file not found: {config.GMAIL_CREDENTIALS_FILE}"
            )
        except Exception as exc:
            raise GmailAgentError(f"Failed to initialise Gmail agent: {exc}")

    def send_email(
        self,
        to: str,
        subject: str,
        body_text: str,
        *,
        body_html: str | None = None,
    ) -> str:
        """Send an email and return the message ID.

        Args:
            to: Recipient email address (validated by Lead model).
            subject: Plain-text subject line.
            body_text: Plain-text body content.
            body_html: Optional HTML body. User-supplied values are escaped to
                       prevent XSS when rendered in webmail clients.
        """
        if len(subject) > _MAX_SUBJECT_LENGTH:
            raise ValueError(
                f"Subject exceeds max length of {_MAX_SUBJECT_LENGTH} characters"
            )
        if len(body_text) > _MAX_BODY_LENGTH:
            raise ValueError(
                f"Body exceeds max length of {_MAX_BODY_LENGTH} characters"
            )

        if body_html is not None:
            mime = MIMEText(body_html, "html")
        else:
            mime = MIMEText(body_text, "plain")

        mime["to"] = to
        mime["from"] = config.GMAIL_SENDER_EMAIL
        mime["subject"] = subject

        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

        try:
            result = (
                self._service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )
            message_id: str = result.get("id", "")
            logger.info("Sent email to %s (message_id=%s)", to, message_id)
            return message_id
        except Exception as exc:
            raise GmailAgentError(f"Failed to send email to {to}: {exc}")

    def send_outreach(self, lead: Lead, subject: str, body: str) -> str:
        """Send a personalised outreach email.

        Lead fields inserted into templates are HTML-escaped to prevent
        stored XSS if the email is later rendered as HTML.
        """
        safe_first = html_escape(lead.first_name)
        safe_last = html_escape(lead.last_name)
        safe_company = html_escape(lead.company)

        personalised_subject = subject.format(
            first_name=safe_first,
            last_name=safe_last,
            company=safe_company,
        )
        personalised_body = body.format(
            first_name=safe_first,
            last_name=safe_last,
            company=safe_company,
        )

        return self.send_email(
            to=lead.email,
            subject=personalised_subject,
            body_text=personalised_body,
        )
