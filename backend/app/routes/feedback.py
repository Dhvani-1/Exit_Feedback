from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Header, Body, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.employee import Employee
from app.models.feedback_record import FeedbackRecord, FeedbackStatus
from app.services.reminder_service import check_and_expire_feedback, cancel_future_reminders, log_audit_event
from app.services.backfill_service import get_system_settings_dict
from app.utils.exceptions import AppException

router = APIRouter(prefix="/feedback", tags=["Public Feedback"])


class FeedbackSubmitPayload(BaseModel):
    submission_source: Optional[str] = "CUSTOM_FORM"
    comments: Optional[str] = None  # Optional general comment if submitted directly


class WebhookPayload(BaseModel):
    token: Optional[str] = None
    feedback_token: Optional[str] = None
    submission_id: Optional[str] = None
    source: Optional[str] = "WEBHOOK"


@router.get("/{token}")
def get_feedback_status(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Public token validation endpoint.
    Checks feedback token validity, expiry, and current submission status.
    """
    record = db.query(FeedbackRecord).filter(FeedbackRecord.feedback_token == token).first()
    if not record:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="INVALID_FEEDBACK_TOKEN",
            message="This feedback form link is invalid or does not exist.",
        )

    is_expired = check_and_expire_feedback(db, record)
    sys_settings = get_system_settings_dict(db)
    employee = db.query(Employee).filter(Employee.id == record.employee_id).first()

    return {
        "token": record.feedback_token,
        "status": record.status,
        "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        "company_name": sys_settings["company_name"],
        "employee_name": employee.employee_name if employee else "Employee",
    }


@router.post("/{token}/submit")
def submit_feedback(
    token: str,
    payload: Optional[FeedbackSubmitPayload] = None,
    db: Session = Depends(get_db),
):
    """
    Public feedback submission endpoint.
    Idempotent: If already submitted, returns existing status without altering history.
    """
    record = db.query(FeedbackRecord).filter(FeedbackRecord.feedback_token == token).first()
    if not record:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="INVALID_FEEDBACK_TOKEN",
            message="This feedback form link is invalid or does not exist.",
        )

    # Expiry Check
    if check_and_expire_feedback(db, record):
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="FEEDBACK_EXPIRED",
            message="This feedback form has expired and is no longer accepting responses.",
        )

    # Idempotent re-submission check
    if record.status == FeedbackStatus.SUBMITTED:
        return {
            "status": FeedbackStatus.SUBMITTED,
            "message": "Feedback already submitted. Thank you!",
            "submitted_at": record.submitted_at.isoformat() if record.submitted_at else None,
            "already_submitted": True,
        }

    source_val = payload.submission_source if payload and payload.submission_source else "CUSTOM_FORM"
    now_utc = datetime.utcnow()

    # Update feedback record
    record.status = FeedbackStatus.SUBMITTED
    record.submitted_at = now_utc
    record.submission_source = source_val
    db.commit()

    # Transactionally cancel all future scheduled reminders
    cancel_future_reminders(db, record.employee_id)

    # Log audit event
    log_audit_event(
        db,
        record.employee_id,
        "FEEDBACK_SUBMITTED",
        f"Feedback submitted via {source_val}",
    )

    return {
        "status": FeedbackStatus.SUBMITTED,
        "message": "Thank you! Your exit feedback has been successfully submitted.",
        "submitted_at": now_utc.isoformat(),
        "already_submitted": False,
    }


@router.post("/webhook")
def feedback_webhook(
    payload: WebhookPayload,
    x_feedback_token: Optional[str] = Header(None, alias="X-Feedback-Token"),
    db: Session = Depends(get_db),
):
    """
    Secure webhook endpoint for external form providers (e.g. MS Forms, Google Forms, Typeform).
    Accepts token via header or payload body. Idempotently marks feedback as SUBMITTED.
    """
    target_token = x_feedback_token or payload.token or payload.feedback_token
    if not target_token:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MISSING_FEEDBACK_TOKEN",
            message="Feedback token must be provided via 'X-Feedback-Token' header or body token field.",
        )

    record = db.query(FeedbackRecord).filter(FeedbackRecord.feedback_token == target_token).first()
    if not record:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="INVALID_FEEDBACK_TOKEN",
            message="Feedback token not found.",
        )

    if check_and_expire_feedback(db, record):
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="FEEDBACK_EXPIRED",
            message="Feedback token has expired.",
        )

    if record.status == FeedbackStatus.SUBMITTED:
        return {
            "status": "success",
            "message": "Webhook received; feedback was already submitted.",
            "already_submitted": True,
        }

    now_utc = datetime.utcnow()
    record.status = FeedbackStatus.SUBMITTED
    record.submitted_at = now_utc
    record.submission_source = payload.source or "WEBHOOK"
    db.commit()

    cancel_future_reminders(db, record.employee_id)
    log_audit_event(
        db,
        record.employee_id,
        "FEEDBACK_SUBMITTED",
        f"Feedback submitted via external webhook ({payload.source})",
    )

    return {
        "status": "success",
        "message": "Feedback submission processed successfully via webhook.",
        "already_submitted": False,
    }
