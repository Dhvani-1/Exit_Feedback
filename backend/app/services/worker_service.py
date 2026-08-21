import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeStatus
from app.models.email_job import EmailJob, EmailJobStatus, EmailType
from app.models.email_template import EmailTemplate
from app.models.feedback_record import FeedbackRecord, FeedbackStatus
from app.services.email_service import send_email, is_retryable_error
from app.services.template_service import render_email_template
from app.services.backfill_service import get_system_settings_dict
from app.services.reminder_service import (
    ensure_feedback_record,
    schedule_reminders_on_initial_sent,
    check_and_expire_feedback,
)

logger = logging.getLogger("worker_service")



def claim_job(db: Session, job_id: int, worker_id: str) -> bool:
    """
    Executes atomic SQL query to claim a SCHEDULED job.
    Returns True if successfully claimed by this worker, False otherwise.
    """
    now_utc = datetime.utcnow()
    # SQL query for cross-DB atomic claim
    stmt = text(
        "UPDATE email_jobs "
        "SET status = :processing_status, processing_started_at = :now, worker_id = :worker_id, updated_at = :now "
        "WHERE id = :job_id AND status = :scheduled_status"
    )
    result = db.execute(
        stmt,
        {
            "processing_status": EmailJobStatus.PROCESSING,
            "now": now_utc,
            "worker_id": worker_id,
            "job_id": job_id,
            "scheduled_status": EmailJobStatus.SCHEDULED,
        },
    )
    db.commit()
    return result.rowcount > 0


def process_due_jobs(db: Session, worker_id: str = "worker_default") -> int:
    """
    Finds and dispatches due SCHEDULED email jobs.
    Returns count of processed jobs.
    """
    now_utc = datetime.utcnow()

    due_jobs = (
        db.query(EmailJob)
        .filter(
            EmailJob.status == EmailJobStatus.SCHEDULED,
            EmailJob.scheduled_at <= now_utc,
        )
        .all()
    )

    processed_count = 0
    for job in due_jobs:
        # Re-check employee status before processing
        employee = db.query(Employee).filter(Employee.id == job.employee_id).first()
        if not employee or employee.status == EmployeeStatus.CANCELLED:
            job.status = EmailJobStatus.CANCELLED
            job.cancelled_at = datetime.utcnow()
            db.commit()
            logger.info(f"Job {job.id} cancelled because employee {job.employee_id} is cancelled")
            continue

        # Phase 3 Race Protection Check: For reminder jobs, ensure feedback is still PENDING
        if job.email_type.startswith("EXIT_FEEDBACK_REMINDER_"):
            record = db.query(FeedbackRecord).filter(FeedbackRecord.employee_id == job.employee_id).first()
            if not record or check_and_expire_feedback(db, record) or record.status != FeedbackStatus.PENDING:
                job.status = EmailJobStatus.CANCELLED
                job.cancelled_at = datetime.utcnow()
                db.commit()
                status_str = record.status if record else "NOT_FOUND"
                logger.info(f"Reminder Job {job.id} cancelled because feedback status is '{status_str}'")
                continue

        # Atomically claim job
        claimed = claim_job(db, job.id, worker_id)
        if not claimed:
            logger.info(f"Job {job.id} already claimed by another worker")
            continue

        processed_count += 1
        sys_settings = get_system_settings_dict(db)

        # Ensure feedback record & secure token exist
        fb_record = ensure_feedback_record(db, employee)

        # Load active template
        template = (
            db.query(EmailTemplate)
            .filter(EmailTemplate.template_key == job.email_type, EmailTemplate.is_active == True)
            .first()
        )

        if not template:
            job.status = EmailJobStatus.FAILED
            job.failed_at = datetime.utcnow()
            job.last_error = f"Template '{job.email_type}' not found or inactive"
            db.commit()
            continue

        # Render template context
        context = {
            "employee_name": employee.employee_name,
            "employee_id": employee.employee_id,
            "last_working_date": str(employee.last_working_date),
            "feedback_due_date": str(employee.feedback_due_date),
            "feedback_form_url": fb_record.form_url if fb_record and fb_record.form_url else sys_settings["feedback_form_url"],
            "company_name": sys_settings["company_name"],
            "designation": getattr(employee, "designation", "") or "",
            "start_date": str(getattr(employee, "start_date", "")) if getattr(employee, "start_date", None) else "",
            "tenure": getattr(employee, "tenure", "") or "",
        }

        try:
            rendered_subject = render_email_template(template.subject, context)
            rendered_body = render_email_template(template.body, context)
        except Exception as te:
            # Template rendering failure is non-retryable
            job.status = EmailJobStatus.FAILED
            job.failed_at = datetime.utcnow()
            job.last_error = f"Template rendering error: {str(te)}"
            db.commit()
            continue

        # Dispatch email
        success, msg_id, error_str = send_email(
            recipient_email=job.recipient_email,
            subject=rendered_subject,
            html_body=rendered_body,
            idempotency_key=job.idempotency_key,
        )

        job.last_attempt_at = datetime.utcnow()
        job.template_version = template.version

        if success:
            job.status = EmailJobStatus.SENT
            job.sent_at = datetime.utcnow()
            job.message_id = msg_id
            job.attempt_count += 1
            job.last_error = None
            db.commit()
            logger.info(f"Job {job.id} ({job.email_type}) successfully SENT to {job.recipient_email}")

            # Phase 3 Hook: If initial email SENT, schedule active reminder jobs based on actual sent_at
            if job.email_type == EmailType.EXIT_FEEDBACK_INITIAL:
                schedule_reminders_on_initial_sent(db, job.employee_id, job.sent_at)
        else:
            job.attempt_count += 1
            job.last_error = error_str

            # Retry logic: check if error is retryable and attempts remain
            if is_retryable_error(error_str) and job.attempt_count < job.max_attempts:
                job.status = EmailJobStatus.SCHEDULED
                # Exponential backoff: 5 mins, 10 mins, 20 mins
                backoff_minutes = 5 * (2 ** (job.attempt_count - 1))
                job.scheduled_at = datetime.utcnow() + timedelta(minutes=backoff_minutes)
                logger.warning(
                    f"Job {job.id} failed temporarily ({error_str}). Retrying in {backoff_minutes} mins (attempt {job.attempt_count}/{job.max_attempts})"
                )
            else:
                job.status = EmailJobStatus.FAILED
                job.failed_at = datetime.utcnow()
                logger.error(f"Job {job.id} permanently FAILED: {error_str}")
            db.commit()


    return processed_count


def recover_stuck_processing_jobs(db: Session, timeout_minutes: int = 15) -> int:
    """
    Finds jobs stuck in PROCESSING for over timeout_minutes and recovers them.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    stuck_jobs = (
        db.query(EmailJob)
        .filter(
            EmailJob.status == EmailJobStatus.PROCESSING,
            EmailJob.processing_started_at <= cutoff,
        )
        .all()
    )

    recovered_count = 0
    for job in stuck_jobs:
        recovered_count += 1
        job.attempt_count += 1
        job.last_error = "PROCESSING lease timeout exceeded (worker crash recovery)"

        if job.attempt_count < job.max_attempts:
            job.status = EmailJobStatus.SCHEDULED
            job.scheduled_at = datetime.utcnow()
            logger.warning(f"Recovered stuck job {job.id} back to SCHEDULED")
        else:
            job.status = EmailJobStatus.FAILED
            job.failed_at = datetime.utcnow()
            logger.error(f"Stuck job {job.id} reached max attempts and marked FAILED")

        db.commit()

    return recovered_count
