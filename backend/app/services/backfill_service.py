import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.employee import Employee, EmployeeStatus
from app.models.email_job import EmailJob, EmailJobStatus, EmailType
from app.models.system_setting import SystemSetting
from app.services.date_calculator import compute_scheduled_at
from app.services.reminder_service import ensure_feedback_record
from app.config import get_settings

logger = logging.getLogger("backfill_service")



def get_system_settings_dict(db: Session) -> dict:
    """Helper to fetch system settings or fallback to defaults."""
    live_settings = get_settings()
    db_settings = db.query(SystemSetting).all()
    s_map = {s.key: s.value for s in db_settings}

    reminders_enabled_raw = s_map.get("reminders_enabled", "false").lower()
    reminders_enabled = reminders_enabled_raw in ("true", "1", "t", "yes")

    db_sender = s_map.get("sender_email")
    sender_email = live_settings.EMAIL_FROM if (not db_sender or db_sender in ("hr@company.com", "dhvani111005@gmail.com")) else db_sender

    db_sender_name = s_map.get("sender_name")
    sender_name = live_settings.EMAIL_FROM_NAME if not db_sender_name else db_sender_name

    return {
        "company_name": s_map.get("company_name", live_settings.DEFAULT_COMPANY_NAME),
        "feedback_form_url": s_map.get("feedback_form_url", live_settings.DEFAULT_FEEDBACK_FORM_URL),
        "sender_email": sender_email,
        "sender_name": sender_name,
        "email_send_hour": int(s_map.get("email_send_hour", live_settings.DEFAULT_SEND_HOUR)),
        "timezone": s_map.get("timezone", live_settings.DEFAULT_TIMEZONE),
        "weekend_behavior": s_map.get("weekend_behavior", live_settings.DEFAULT_WEEKEND_BEHAVIOR),
        "reminders_enabled": reminders_enabled,
        "reminder_count": int(s_map.get("reminder_count", "0")),
        "reminder_interval_days": int(s_map.get("reminder_interval_days", "7")),
        "feedback_expiry_days": int(s_map.get("feedback_expiry_days", "30")),
        "feedback_base_url": s_map.get("feedback_base_url", "http://localhost:5173"),
    }



def backfill_missing_email_jobs(db: Session) -> int:
    """
    Scans active employees and creates missing initial email jobs idempotently.
    
    Returns:
    - Count of newly created email jobs.
    """
    sys_settings = get_system_settings_dict(db)
    send_hour = sys_settings["email_send_hour"]
    tz_str = sys_settings["timezone"]
    weekend_behavior = sys_settings["weekend_behavior"]

    active_employees = (
        db.query(Employee)
        .filter(Employee.status == EmployeeStatus.SCHEDULED)
        .all()
    )

    created_count = 0
    for emp in active_employees:
        ensure_feedback_record(db, emp)
        idempotency_key = f"EXIT_FEEDBACK_INITIAL:{emp.id}"


        # Check existing job by idempotency_key or unique employee_id + email_type constraint
        existing = (
            db.query(EmailJob)
            .filter(
                EmailJob.employee_id == emp.id,
                EmailJob.email_type == EmailType.EXIT_FEEDBACK_INITIAL,
            )
            .first()
        )

        if not existing:
            scheduled_at_utc = compute_scheduled_at(
                emp.feedback_due_date,
                send_hour=send_hour,
                timezone_str=tz_str,
                weekend_behavior=weekend_behavior,
            )

            job = EmailJob(
                employee_id=emp.id,
                email_type=EmailType.EXIT_FEEDBACK_INITIAL,
                idempotency_key=idempotency_key,
                recipient_email=emp.personal_email,
                scheduled_at=scheduled_at_utc,
                status=EmailJobStatus.SCHEDULED,
                attempt_count=0,
                max_attempts=3,
                template_version="1.0",
            )
            db.add(job)
            try:
                db.commit()
                created_count += 1
                logger.info(f"Backfilled email job for employee {emp.employee_id} ({emp.id})")
            except IntegrityError:
                db.rollback()
                logger.info(f"Idempotent backfill duplicate skipped for employee {emp.id}")

    return created_count
