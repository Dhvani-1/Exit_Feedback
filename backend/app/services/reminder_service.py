import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.employee import Employee, EmployeeStatus
from app.models.email_job import EmailJob, EmailJobStatus, EmailType
from app.models.feedback_record import FeedbackRecord, FeedbackStatus, AuditLog
from app.models.system_setting import SystemSetting
from app.config import settings

logger = logging.getLogger("reminder_service")


def generate_secure_token() -> str:
    """Generates a cryptographically secure random token (32 bytes urlsafe)."""
    return secrets.token_urlsafe(32)


def sanitize_audit_details(details: Optional[str]) -> Optional[str]:
    """Sanitizes sensitive information from audit log details."""
    if not details:
        return details
    import re
    cleaned = details
    # Redact password key-values e.g. password=secretpassword123
    cleaned = re.sub(r'password=[^\s&,]+', 'password=[REDACTED_SECRET]', cleaned, flags=re.IGNORECASE)
    # Redact token key-values e.g. token=abcd1234...
    cleaned = re.sub(r'token=[^\s&,]+', 'token=[REDACTED_TOKEN]', cleaned, flags=re.IGNORECASE)
    # Redact raw Bearer tokens
    cleaned = re.sub(r'bearer\s+[^\s&,]+', 'bearer [REDACTED_TOKEN]', cleaned, flags=re.IGNORECASE)
    return cleaned


def log_audit_event(
    db: Session,
    employee_id: int,
    event_type: str,
    details: Optional[str] = None,
    actor_type: str = "SYSTEM",
    actor_id: Optional[str] = None,
) -> AuditLog:
    """Records a feedback/reminder audit log event with sanitized details and actor tracking."""
    safe_details = sanitize_audit_details(details)
    log_entry = AuditLog(
        employee_id=employee_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=str(actor_id) if actor_id else None,
        details=safe_details,
        created_at=datetime.utcnow(),
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def get_reminder_settings(db: Session) -> dict:
    """Fetches Phase 3 reminder settings with fallbacks."""
    db_settings = db.query(SystemSetting).all()
    s_map = {s.key: s.value for s in db_settings}

    reminders_enabled_raw = s_map.get("reminders_enabled", "false").lower()
    reminders_enabled = reminders_enabled_raw in ("true", "1", "t", "yes")

    return {
        "reminders_enabled": reminders_enabled,
        "reminder_count": int(s_map.get("reminder_count", "0")),
        "reminder_interval_days": int(s_map.get("reminder_interval_days", "7")),
        "feedback_expiry_days": int(s_map.get("feedback_expiry_days", "30")),
        "feedback_base_url": s_map.get("feedback_base_url", "http://localhost:5173"),
    }


def ensure_feedback_record(db: Session, employee: Employee) -> FeedbackRecord:
    """
    Ensures a FeedbackRecord exists for the given employee.
    Created at lifecycle initialization (e.g. employee creation or backfill).
    """
    existing = db.query(FeedbackRecord).filter(FeedbackRecord.employee_id == employee.id).first()
    if existing:
        return existing

    cfg = get_reminder_settings(db)
    expiry_days = cfg["feedback_expiry_days"]
    expires_at = datetime.utcnow() + timedelta(days=expiry_days) if expiry_days > 0 else None

    token = generate_secure_token()
    base_url = cfg["feedback_base_url"].rstrip("/")
    form_url = f"{base_url}/feedback/{token}"

    record = FeedbackRecord(
        employee_id=employee.id,
        feedback_token=token,
        status=FeedbackStatus.PENDING,
        form_url=form_url,
        expires_at=expires_at,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
        log_audit_event(db, employee.id, "FEEDBACK_RECORD_CREATED", f"Feedback record initialized with token {token[:8]}...")
        logger.info(f"Created FeedbackRecord for employee {employee.employee_id} ({employee.id})")
    except IntegrityError:
        db.rollback()
        record = db.query(FeedbackRecord).filter(FeedbackRecord.employee_id == employee.id).first()

    return record


def check_and_expire_feedback(db: Session, record: FeedbackRecord) -> bool:
    """
    Checks if a PENDING feedback record has passed its expiry date and updates status to EXPIRED.
    Returns True if expired, False otherwise.
    """
    if record.status == FeedbackStatus.PENDING and record.expires_at:
        if datetime.utcnow() > record.expires_at:
            record.status = FeedbackStatus.EXPIRED
            db.commit()
            cancel_future_reminders(db, record.employee_id)
            log_audit_event(db, record.employee_id, "FEEDBACK_EXPIRED", "Feedback form token expired")
            logger.info(f"Feedback record {record.id} expired for employee {record.employee_id}")
            return True
    return record.status == FeedbackStatus.EXPIRED


def schedule_reminders_on_initial_sent(db: Session, employee_id: int, sent_at: datetime) -> int:
    """
    Schedules reminder jobs ONLY after initial email reaches SENT.
    Reminder dates are calculated starting from the actual sent_at timestamp.
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee or employee.status == EmployeeStatus.CANCELLED:
        return 0

    record = db.query(FeedbackRecord).filter(FeedbackRecord.employee_id == employee_id).first()
    if not record:
        record = ensure_feedback_record(db, employee)

    if check_and_expire_feedback(db, record) or record.status != FeedbackStatus.PENDING:
        logger.info(f"Not scheduling reminders for employee {employee_id}: feedback status is {record.status}")
        return 0

    cfg = get_reminder_settings(db)
    if not cfg["reminders_enabled"] or cfg["reminder_count"] <= 0:
        logger.info(f"Reminders disabled or count is 0 for employee {employee_id}")
        return 0

    count = cfg["reminder_count"]
    interval_days = cfg["reminder_interval_days"]

    created_count = 0
    for idx in range(1, count + 1):
        email_type = f"EXIT_FEEDBACK_REMINDER_{idx}"
        idempotency_key = f"{email_type}:{employee_id}"

        existing = (
            db.query(EmailJob)
            .filter(
                EmailJob.employee_id == employee_id,
                EmailJob.email_type == email_type,
            )
            .first()
        )

        if not existing:
            scheduled_at = sent_at + timedelta(days=idx * interval_days)
            job = EmailJob(
                employee_id=employee_id,
                email_type=email_type,
                idempotency_key=idempotency_key,
                recipient_email=employee.personal_email,
                scheduled_at=scheduled_at,
                status=EmailJobStatus.SCHEDULED,
                attempt_count=0,
                max_attempts=3,
                template_version="1.0",
            )
            db.add(job)
            try:
                db.commit()
                created_count += 1
                log_audit_event(
                    db,
                    employee_id,
                    "REMINDER_SCHEDULED",
                    f"Scheduled {email_type} for {scheduled_at.isoformat()}",
                )
                logger.info(f"Scheduled {email_type} for employee {employee_id} at {scheduled_at}")
            except IntegrityError:
                db.rollback()
                logger.info(f"Duplicate reminder job skipped for {email_type}:{employee_id}")

    return created_count


def cancel_future_reminders(db: Session, employee_id: int) -> int:
    """
    Cancels all scheduled future reminder jobs for an employee.
    """
    reminder_jobs = (
        db.query(EmailJob)
        .filter(
            EmailJob.employee_id == employee_id,
            EmailJob.email_type.like("EXIT_FEEDBACK_REMINDER_%"),
            EmailJob.status == EmailJobStatus.SCHEDULED,
        )
        .all()
    )

    cancelled_count = 0
    now_utc = datetime.utcnow()
    for job in reminder_jobs:
        job.status = EmailJobStatus.CANCELLED
        job.cancelled_at = now_utc
        cancelled_count += 1

    if cancelled_count > 0:
        db.commit()
        log_audit_event(db, employee_id, "REMINDER_CANCELLED", f"Cancelled {cancelled_count} future reminder job(s)")
        logger.info(f"Cancelled {cancelled_count} reminder jobs for employee {employee_id}")

    return cancelled_count
