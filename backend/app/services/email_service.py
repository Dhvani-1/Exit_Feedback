import smtplib
import uuid
import logging
from email.message import EmailMessage
from typing import Tuple, Optional

from app.config import settings, get_settings

logger = logging.getLogger("email_service")
logger.setLevel(logging.INFO)


def is_retryable_error(error_msg: str) -> bool:
    """
    Classifies email delivery failure messages into retryable vs non-retryable errors.
    
    Retryable:
    - Connection timeouts / socket timeouts
    - Temporary SMTP 5xx / 4xx server responses
    - Rate limit (429) / connection drops
    
    Non-retryable:
    - Invalid recipient email format / user unknown
    - Authentication rejected by provider
    - Malformed sender configuration
    """
    if not error_msg:
        return True

    msg_lower = error_msg.lower()

    non_retryable_keywords = [
        "invalid recipient",
        "user unknown",
        "mailbox unavailable",
        "5.1.1",
        "authentication failed",
        "invalid credentials",
        "5.7.8",
        "syntax error",
    ]

    for keyword in non_retryable_keywords:
        if keyword in msg_lower:
            return False

    return True


def send_email(
    recipient_email: str,
    subject: str,
    html_body: str,
    idempotency_key: Optional[str] = None,
    sender_email: Optional[str] = None,
    sender_name: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Dispatches an HTML email using the configured provider (console or SMTP).
    
    Returns:
    - (success: bool, message_id: Optional[str], error_message: Optional[str])
    """
    live_settings = get_settings()
    from_addr = sender_email or live_settings.EMAIL_FROM
    from_name = sender_name or live_settings.EMAIL_FROM_NAME

    effective_mode = live_settings.EMAIL_MODE.lower()
    has_credentials = bool(live_settings.SMTP_USERNAME and live_settings.SMTP_PASSWORD and live_settings.SMTP_HOST and live_settings.SMTP_HOST != "localhost")

    # If configured for SMTP but credentials are missing, fall back to console mode safely
    if effective_mode == "smtp" and not has_credentials:
        logger.warning("EMAIL_MODE is set to 'smtp', but valid SMTP credentials are missing. Falling back to console mode.")
        effective_mode = "console"

    # 1. Development / Console Mode
    if effective_mode == "console":
        simulated_msg_id = f"SIMULATED-{uuid.uuid4().hex[:12].upper()}"
        logger.info(
            f"\n[EMAIL_MODE=CONSOLE] [DELIVERY_MODE=SIMULATED]\n"
            f"IDEMPOTENCY_KEY: {idempotency_key}\n"
            f"FROM: {from_name} <{from_addr}>\n"
            f"TO: {recipient_email}\n"
            f"SUBJECT: {subject}\n"
            f"BODY PREVIEW:\n{html_body[:300]}...\n"
            f"MESSAGE_ID: {simulated_msg_id}\n"
        )
        return True, simulated_msg_id, None

    # 2. Production SMTP Mode
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_addr}>"
        msg["To"] = recipient_email
        msg_id = f"<{uuid.uuid4().hex}@{live_settings.SMTP_HOST}>"
        msg["Message-ID"] = msg_id
        if idempotency_key:
            msg["X-Idempotency-Key"] = idempotency_key

        msg.set_content("Please use an HTML compatible email viewer to view this message.")
        msg.add_alternative(html_body, subtype="html")

        # Connect with 10s timeout to prevent hanging the worker
        if live_settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(live_settings.SMTP_HOST, live_settings.SMTP_PORT, timeout=10) as server:
                if live_settings.SMTP_USERNAME and live_settings.SMTP_PASSWORD:
                    server.login(live_settings.SMTP_USERNAME, live_settings.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(live_settings.SMTP_HOST, live_settings.SMTP_PORT, timeout=10) as server:
                if live_settings.SMTP_USE_TLS:
                    server.starttls()
                if live_settings.SMTP_USERNAME and live_settings.SMTP_PASSWORD:
                    server.login(live_settings.SMTP_USERNAME, live_settings.SMTP_PASSWORD)
                server.send_message(msg)

        return True, msg_id, None

    except Exception as e:
        error_str = f"SMTP Delivery Failure: {type(e).__name__} - {str(e)}"
        logger.error(f"Failed to send email to {recipient_email}: {error_str}")
        return False, None, error_str
