"""
Send an HTML email via Gmail API.

Usage:
    python tools/send_email_gmail.py --html .tmp/newsletter_final.html --subject "Your Newsletter"
                                     [--to recipient@example.com]
"""

import argparse
import base64
import os
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_gmail_service():
    creds = None
    token_path = Path("token.json")
    creds_path = Path("credentials.json")

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                print("ERROR: credentials.json not found. Download it from Google Cloud Console.", file=sys.stderr)
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send(html_content: str, subject: str, to: str, sender: str) -> str:
    service = get_gmail_service()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to

    # Plain text fallback
    plain = "This email requires an HTML-capable email client."
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result["id"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", required=True, help="Path to HTML file to send")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--to", help="Recipient email (defaults to GMAIL_SENDER in .env)")
    args = parser.parse_args()

    sender = os.getenv("GMAIL_SENDER", "")
    if not sender or sender == "your_email@gmail.com":
        print("ERROR: GMAIL_SENDER not set in .env", file=sys.stderr)
        sys.exit(1)

    recipient = args.to or sender

    html_path = Path(args.html)
    if not html_path.exists():
        print(f"ERROR: HTML file not found: {args.html}", file=sys.stderr)
        sys.exit(1)

    html_content = html_path.read_text(encoding="utf-8")

    print(f"Sending to: {recipient}")
    message_id = send(html_content, args.subject, recipient, sender)
    print(f"Sent. Message ID: {message_id}")


if __name__ == "__main__":
    main()
