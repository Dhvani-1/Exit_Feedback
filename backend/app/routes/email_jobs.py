import math
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.employee import Employee, EmployeeStatus
from app.models.email_job import EmailJob, EmailJobStatus, EmailType
from app.schemas.email_job import EmailJobResponse, RescheduleRequest, EmailJobPaginatedResponse
from app.services.worker_service import claim_job, process_due_jobs
from app.utils.security import get_current_user
from app.utils.exceptions import AppException

router = APIRouter(prefix="/email", tags=["Email Jobs"])


@router.post("/employees/{id}/send-now", response_model=EmailJobResponse)
def send_email_now(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atomically claims and dispatches initial feedback email immediately for an employee."""
    employee = db.query(Employee).filter(Employee.id == id).first()
    if not employee:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EMPLOYEE_NOT_FOUND",
            message=f"Employee with ID {id} not found",
        )

    job = (
        db.query(EmailJob)
        .filter(
            EmailJob.employee_id == id,
            EmailJob.email_type == EmailType.EXIT_FEEDBACK_INITIAL,
        )
        .first()
    )

    if not job:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EMAIL_JOB_NOT_FOUND",
            message="No initial email job exists for this employee",
        )

    if job.status == EmailJobStatus.SENT:
        sent_str = job.sent_at.strftime("%Y-%m-%d %H:%M:%S UTC") if job.sent_at else "earlier"
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="EMAIL_ALREADY_SENT",
            message=f"Email already sent on {sent_str}. duplicate sending is prevented.",
        )

    if job.status == EmailJobStatus.CANCELLED:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="EMAIL_CANCELLED",
            message="Cannot send an email job that has been cancelled",
        )

    if job.status == EmailJobStatus.PROCESSING:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="EMAIL_PROCESSING",
            message="Email job is currently being processed by a worker",
        )

    # Force scheduled_at to UTC_NOW so worker/immediate process claims it
    job.scheduled_at = datetime.utcnow()
    db.commit()

    # Trigger due job processing
    process_due_jobs(db, worker_id=f"hr_user_{current_user.id}_send_now")
    db.refresh(job)

    return job


@router.post("/employees/{id}/cancel", response_model=EmailJobResponse)
def cancel_email_job(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancels a scheduled email job."""
    job = (
        db.query(EmailJob)
        .filter(
            EmailJob.employee_id == id,
            EmailJob.email_type == EmailType.EXIT_FEEDBACK_INITIAL,
        )
        .first()
    )

    if not job:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EMAIL_JOB_NOT_FOUND",
            message="No initial email job exists for this employee",
        )

    if job.status == EmailJobStatus.SENT:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="EMAIL_ALREADY_SENT",
            message="Cannot cancel an email job that has already been sent",
        )

    if job.status == EmailJobStatus.PROCESSING:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="EMAIL_PROCESSING",
            message="Cannot cancel an email job that is currently processing",
        )

    job.status = EmailJobStatus.CANCELLED
    job.cancelled_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return job


@router.post("/employees/{id}/reschedule", response_model=EmailJobResponse)
def reschedule_email_job(
    id: int,
    payload: RescheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reschedules an unsent SCHEDULED email job to a new date and time."""
    job = (
        db.query(EmailJob)
        .filter(
            EmailJob.employee_id == id,
            EmailJob.email_type == EmailType.EXIT_FEEDBACK_INITIAL,
        )
        .first()
    )

    if not job:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EMAIL_JOB_NOT_FOUND",
            message="No initial email job exists for this employee",
        )

    if job.status != EmailJobStatus.SCHEDULED:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="INVALID_JOB_STATE_FOR_RESCHEDULE",
            message=f"Only SCHEDULED jobs can be rescheduled. Current status: '{job.status}'",
        )

    # Convert naive to UTC if necessary
    new_scheduled = payload.scheduled_at.replace(tzinfo=None)
    job.scheduled_at = new_scheduled
    db.commit()
    db.refresh(job)
    return job


@router.post("/employees/{id}/retry", response_model=EmailJobResponse)
def retry_failed_email_job(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually resets a FAILED email job back to SCHEDULED for immediate retry."""
    job = (
        db.query(EmailJob)
        .filter(
            EmailJob.employee_id == id,
            EmailJob.email_type == EmailType.EXIT_FEEDBACK_INITIAL,
        )
        .first()
    )

    if not job:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EMAIL_JOB_NOT_FOUND",
            message="No email job exists for this employee",
        )

    if job.status != EmailJobStatus.FAILED:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="INVALID_JOB_STATE_FOR_RETRY",
            message=f"Only FAILED jobs can be manually retried. Current status: '{job.status}'",
        )

    job.status = EmailJobStatus.SCHEDULED
    job.scheduled_at = datetime.utcnow()
    job.last_error = None
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=EmailJobPaginatedResponse)
def list_email_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists all email jobs with status filtering and pagination safety."""
    query = db.query(EmailJob)

    if status_filter and status_filter.strip():
        query = query.filter(EmailJob.status == status_filter.strip().upper())

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(EmailJob.created_at.desc()).offset(offset).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return EmailJobPaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
