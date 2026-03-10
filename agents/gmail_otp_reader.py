"""
Gmail IMAP OTP Reader — Reads Greenhouse verification codes from Gmail inbox.
Requires Gmail App Password (not regular password).
Set EMAIL_SENDER and EMAIL_PASSWORD in .env file.
"""
import imaplib
import email
import re
import time
from email.header import decode_header
from agents.config import EMAIL_SENDER, EMAIL_PASSWORD
from agents.logger import get_logger

logger = get_logger("GmailOTP")

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993


def fetch_greenhouse_otp(max_wait_seconds: int = 90, poll_interval: int = 5) -> str | None:
    """
    Poll Gmail inbox for a Greenhouse verification code email.
    Returns the 8-character code if found, None if timeout.
    """
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        logger.warning("Gmail credentials not configured (EMAIL_SENDER / EMAIL_PASSWORD)")
        return None

    start_time = time.time()
    logger.info(f"Polling Gmail for Greenhouse OTP (max {max_wait_seconds}s)...")

    while time.time() - start_time < max_wait_seconds:
        try:
            code = _check_inbox_for_otp()
            if code:
                logger.info(f"Found OTP: {code}")
                return code
        except Exception as e:
            logger.warning(f"IMAP error: {e}")

        remaining = max_wait_seconds - (time.time() - start_time)
        if remaining > poll_interval:
            time.sleep(poll_interval)
        else:
            break

    logger.warning("OTP not found within timeout")
    return None


def _check_inbox_for_otp() -> str | None:
    """Connect to Gmail IMAP, search recent emails for Greenhouse verification code."""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    try:
        mail.login(EMAIL_SENDER, EMAIL_PASSWORD)
        mail.select("INBOX")

        # Search for recent emails from Greenhouse (last 1 day)
        _, message_numbers = mail.search(None, '(FROM "greenhouse" UNSEEN)')
        if not message_numbers[0]:
            # Also try seen messages in case it was already read
            _, message_numbers = mail.search(None, '(FROM "greenhouse")')

        if not message_numbers[0]:
            return None

        # Get the most recent email
        nums = message_numbers[0].split()
        latest = nums[-1]

        _, msg_data = mail.fetch(latest, "(RFC822)")
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Extract subject
        subject = ""
        raw_subject = msg.get("Subject", "")
        if raw_subject:
            decoded = decode_header(raw_subject)
            subject = str(decoded[0][0], decoded[0][1] or "utf-8") if isinstance(decoded[0][0], bytes) else str(decoded[0][0])

        # Check if it's a verification email
        if "verif" not in subject.lower() and "code" not in subject.lower() and "security" not in subject.lower():
            # Check body too
            body = _get_email_body(msg)
            if "verification" not in body.lower() and "security code" not in body.lower():
                return None
        else:
            body = _get_email_body(msg)

        # Extract 8-character alphanumeric code
        # Greenhouse codes are typically 8 chars, alphanumeric
        patterns = [
            r'\b([A-Za-z0-9]{8})\b',  # Generic 8-char alphanumeric
            r'code[:\s]+([A-Za-z0-9]{8})',  # "code: XXXXXXXX"
            r'([A-Z0-9]{8})',  # All caps/digits 8-char
        ]

        for pattern in patterns:
            matches = re.findall(pattern, body)
            for match in matches:
                # Filter out common words and non-code strings
                if match.lower() in ("password", "security", "verified", "applicat", "somethin", "continue", "https://"):
                    continue
                if len(match) == 8 and re.match(r'^[A-Za-z0-9]+$', match):
                    # Mark email as read
                    mail.store(latest, '+FLAGS', '\\Seen')
                    return match

        return None
    finally:
        try:
            mail.logout()
        except:
            pass


def _get_email_body(msg) -> str:
    """Extract text body from email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode("utf-8", errors="ignore")
            elif content_type == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    html = payload.decode("utf-8", errors="ignore")
                    # Strip HTML tags for code extraction
                    body += re.sub(r'<[^>]+>', ' ', html)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="ignore")
    return body
