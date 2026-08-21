from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.models.user import User
from app.models.system_setting import SystemSetting
from app.schemas.settings import SystemSettingsResponse, SystemSettingsUpdate, TestEmailRequest
from app.services.backfill_service import get_system_settings_dict
from app.services.email_service import send_email
from app.utils.security import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/settings", tags=["System Settings"])


@router.get("/email", response_model=SystemSettingsResponse)
def get_email_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves system configuration settings including email sender, provider, and mode."""
    live_settings = get_settings()
    s_dict = get_system_settings_dict(db)

    is_smtp = live_settings.EMAIL_MODE.lower() == "smtp"
    email_mode = "Production" if is_smtp else "Console / Simulation"
    email_provider = "SMTP" if is_smtp else "Console Logger"
    is_secret_configured = bool(live_settings.SMTP_PASSWORD and live_settings.SMTP_PASSWORD.strip())

    return SystemSettingsResponse(
        **s_dict,
        email_mode=email_mode,
        email_provider=email_provider,
        is_secret_configured=is_secret_configured,
        is_env_managed=True,
    )


@router.put("/email", response_model=SystemSettingsResponse)
def update_email_settings(
    payload: SystemSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Updates non-secret system settings with strict validation."""
    settings_data = {
        "company_name": payload.company_name.strip(),
        "feedback_form_url": payload.feedback_form_url.strip(),
        "sender_email": payload.sender_email.strip(),
        "sender_name": payload.sender_name.strip(),
        "email_send_hour": str(payload.email_send_hour),
        "timezone": payload.timezone.strip(),
        "weekend_behavior": payload.weekend_behavior.strip(),
        "reminders_enabled": "true" if payload.reminders_enabled else "false",
        "reminder_count": str(payload.reminder_count),
        "reminder_interval_days": str(payload.reminder_interval_days),
        "feedback_expiry_days": str(payload.feedback_expiry_days),
        "feedback_base_url": payload.feedback_base_url.strip(),
    }

    for key, val in settings_data.items():
        existing = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if existing:
            existing.value = val
        else:
            setting_obj = SystemSetting(key=key, value=val, description=key.replace("_", " ").title())
            db.add(setting_obj)

    db.commit()
    return get_email_settings(db=db, current_user=current_user)


@router.post("/test-email")
def send_test_email(
    payload: TestEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dispatches a test email to an explicitly specified recipient using configured sender settings."""
    live_settings = get_settings()
    s_dict = get_system_settings_dict(db)
    subject = f"Test Email - Exit Feedback System ({s_dict['company_name']})"
    html_body = f"""
    <h2>System Test Email</h2>
    <p>This is a test email dispatched from the Employee Exit Feedback Automation System.</p>
    <p><b>Sender Name:</b> {s_dict['sender_name']}</p>
    <p><b>Sender Email:</b> {s_dict['sender_email']}</p>
    <p><b>Mode:</b> {live_settings.EMAIL_MODE.upper()}</p>
    """

    success, msg_id, err_msg = send_email(
        recipient_email=payload.recipient_email,
        subject=subject,
        html_body=html_body,
        idempotency_key=f"TEST_EMAIL_{payload.recipient_email}",
        sender_email=s_dict['sender_email'],
        sender_name=s_dict['sender_name'],
    )

    if not success:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="TEST_EMAIL_FAILED",
            message=f"Failed to dispatch test email: {err_msg}",
        )

    return {
        "status": "success",
        "message": f"Test email dispatched successfully to {payload.recipient_email}",
        "message_id": msg_id,
        "mode": settings.EMAIL_MODE,
        "sender": f"{s_dict['sender_name']} <{s_dict['sender_email']}>",
    }


@router.post("/reset-test-data")
def reset_test_data_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clears all test data (Audit Logs, Feedback Records, Email Jobs, Employees) for testing repeat submissions."""
    from app.models.employee import Employee
    from app.models.email_job import EmailJob
    from app.models.feedback_record import FeedbackRecord, AuditLog

    num_audits = db.query(AuditLog).delete()
    num_feedback = db.query(FeedbackRecord).delete()
    num_jobs = db.query(EmailJob).delete()
    num_emps = db.query(Employee).delete()
    db.commit()

    return {
        "status": "success",
        "message": "All testing logs and data have been cleared successfully.",
        "cleared_records": {
            "audit_logs": num_audits,
            "feedback_records": num_feedback,
            "email_jobs": num_jobs,
            "employees": num_emps,
        },
    }
