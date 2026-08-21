import math
from typing import Optional, List
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError

from app.database.connection import get_db
from app.models.user import User
from app.models.employee import Employee, EmployeeStatus
from app.models.email_job import EmailJob, EmailJobStatus, EmailType
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeePaginatedResponse,
)
from app.schemas.email_job import EmailJobResponse
from app.services.date_calculator import calculate_feedback_due_date, compute_scheduled_at
from app.services.backfill_service import get_system_settings_dict
from app.utils.security import get_current_user
from app.utils.exceptions import AppException

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a new employee record with 3 required fields, calculates 3-calendar-month due date, and schedules initial email job."""
    # 1. Check duplicate personal_email + last_working_date
    existing_emp = (
        db.query(Employee)
        .filter(
            func.lower(Employee.personal_email) == payload.personal_email.lower().strip(),
            Employee.last_working_date == payload.last_working_date,
        )
        .first()
    )
    if existing_emp:
        err_code = "ACTIVE_EMPLOYEE_EXISTS_WITH_EMAIL" if existing_emp.status == EmployeeStatus.SCHEDULED else "EMPLOYEE_ALREADY_EXISTS"
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code=err_code,
            message=f"An employee record with email '{payload.personal_email}' and last working date '{payload.last_working_date}' already exists (Status: {existing_emp.status}).",
        )

    # 2. Calculate authoritative 3-calendar-month feedback due date
    calculated_due_date = calculate_feedback_due_date(payload.last_working_date)

    employee = Employee(
        full_name=payload.full_name.strip(),
        personal_email=payload.personal_email.lower().strip(),
        last_working_date=payload.last_working_date,
        designation=payload.designation.strip() if payload.designation else None,
        start_date=payload.start_date,
        tenure=payload.tenure.strip() if payload.tenure else None,
        feedback_due_date=calculated_due_date,
        status=EmployeeStatus.SCHEDULED,
        version=1,
    )

    db.add(employee)
    try:
        db.commit()
        db.refresh(employee)
    except IntegrityError:
        db.rollback()
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="EMPLOYEE_ALREADY_EXISTS",
            message=f"An employee record with email '{payload.personal_email}' and last working date '{payload.last_working_date}' already exists.",
        )

    # Initialize FeedbackRecord & token BEFORE initial email dispatch
    from app.services.reminder_service import ensure_feedback_record
    ensure_feedback_record(db, employee)

    # Automatically schedule initial feedback email job
    sys_settings = get_system_settings_dict(db)
    scheduled_at_utc = compute_scheduled_at(
        calculated_due_date,
        send_hour=sys_settings["email_send_hour"],
        timezone_str=sys_settings["timezone"],
        weekend_behavior=sys_settings["weekend_behavior"],
    )

    idempotency_key = f"EXIT_FEEDBACK_INITIAL:{employee.id}"
    email_job = EmailJob(
        employee_id=employee.id,
        email_type=EmailType.EXIT_FEEDBACK_INITIAL,
        idempotency_key=idempotency_key,
        recipient_email=employee.personal_email,
        scheduled_at=scheduled_at_utc,
        status=EmailJobStatus.SCHEDULED,
        attempt_count=0,
        max_attempts=3,
        template_version="1.0",
    )
    db.add(email_job)
    db.commit()

    return employee


@router.get("", response_model=EmployeePaginatedResponse)
def list_employees(
    search: Optional[str] = Query(None, description="Search by Full Name or Email"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by Employee Status"),
    feedback_status_filter: Optional[str] = Query(None, alias="feedback_status", description="Filter by Feedback Status (PENDING, SUBMITTED, EXPIRED)"),
    lwd_start: Optional[date] = Query(None, description="Filter Last Working Date from"),
    lwd_end: Optional[date] = Query(None, description="Filter Last Working Date to"),
    due_start: Optional[date] = Query(None, description="Filter Feedback Due Date from"),
    due_end: Optional[date] = Query(None, description="Filter Feedback Due Date to"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page (max 100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists employees with server-side search, multi-field filtering, sorting, and page size safety."""
    query = db.query(Employee)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Employee.full_name.ilike(term),
                Employee.personal_email.ilike(term),
            )
        )

    if status_filter and status_filter.strip():
        query = query.filter(Employee.status == status_filter.strip().upper())

    if feedback_status_filter and feedback_status_filter.strip():
        from app.models.feedback_record import FeedbackRecord
        query = query.join(FeedbackRecord, Employee.id == FeedbackRecord.employee_id).filter(
            FeedbackRecord.status == feedback_status_filter.strip().upper()
        )

    if lwd_start:
        query = query.filter(Employee.last_working_date >= lwd_start)
    if lwd_end:
        query = query.filter(Employee.last_working_date <= lwd_end)

    if due_start:
        query = query.filter(Employee.feedback_due_date >= due_start)
    if due_end:
        query = query.filter(Employee.feedback_due_date <= due_end)

    total = query.count()

    valid_sort_fields = {
        "last_working_date": Employee.last_working_date,
        "feedback_due_date": Employee.feedback_due_date,
        "full_name": Employee.full_name,
        "created_at": Employee.created_at,
    }
    sort_col = valid_sort_fields.get(sort_by, Employee.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return EmployeePaginatedResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{id:int}", response_model=EmployeeResponse)
def get_employee(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves employee record by primary key ID."""
    employee = db.query(Employee).filter(Employee.id == id).first()
    if not employee:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EMPLOYEE_NOT_FOUND",
            message=f"Employee with ID {id} not found",
        )
    return employee


@router.put("/{id}", response_model=EmployeeResponse)
def update_employee(
    id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Updates employee details and syncs unsent scheduled email jobs."""
    employee = db.query(Employee).filter(Employee.id == id).first()
    if not employee:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EMPLOYEE_NOT_FOUND",
            message=f"Employee with ID {id} not found",
        )

    if employee.version != payload.version:
        raise AppException(
            status_code=status.HTTP_409_CONFLICT,
            code="STALE_EMPLOYEE_RECORD",
            message="This employee record has been updated by another user. Please refresh and try again.",
            details={"current_version": employee.version, "submitted_version": payload.version},
        )

    if payload.personal_email.lower().strip() != employee.personal_email.lower() or payload.last_working_date != employee.last_working_date:
        active_email = (
            db.query(Employee)
            .filter(
                func.lower(Employee.personal_email) == payload.personal_email.lower().strip(),
                Employee.last_working_date == payload.last_working_date,
                Employee.status == EmployeeStatus.SCHEDULED,
                Employee.id != id,
            )
            .first()
        )
        if active_email:
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="ACTIVE_EMPLOYEE_EXISTS_WITH_EMAIL",
                message=f"Another active employee already exists with email '{payload.personal_email}' and date '{payload.last_working_date}'",
            )

    lwd_changed = payload.last_working_date != employee.last_working_date
    if lwd_changed:
        employee.last_working_date = payload.last_working_date
        employee.feedback_due_date = calculate_feedback_due_date(payload.last_working_date)

    employee.full_name = payload.full_name.strip()
    employee.personal_email = payload.personal_email.lower().strip()
    employee.designation = payload.designation.strip() if payload.designation else None
    employee.start_date = payload.start_date
    employee.tenure = payload.tenure.strip() if payload.tenure else None
    employee.version += 1

    # Sync unsent SCHEDULED email jobs
    unsent_jobs = (
        db.query(EmailJob)
        .filter(
            EmailJob.employee_id == id,
            EmailJob.status == EmailJobStatus.SCHEDULED,
        )
        .all()
    )

    for job in unsent_jobs:
        job.recipient_email = employee.personal_email
        if job.email_type == EmailType.EXIT_FEEDBACK_INITIAL and lwd_changed:
            sys_settings = get_system_settings_dict(db)
            job.scheduled_at = compute_scheduled_at(
                employee.feedback_due_date,
                send_hour=sys_settings["email_send_hour"],
                timezone_str=sys_settings["timezone"],
                weekend_behavior=sys_settings["weekend_behavior"],
            )

    db.commit()
    db.refresh(employee)

    return employee


@router.post("/{id}/cancel", response_model=EmployeeResponse)
def cancel_employee(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Transactionally cancels employee record and unsent email jobs."""
    employee = db.query(Employee).filter(Employee.id == id).first()
    if not employee:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EMPLOYEE_NOT_FOUND",
            message=f"Employee with ID {id} not found",
        )

    employee.status = EmployeeStatus.CANCELLED
    employee.version += 1

    unsent_jobs = (
        db.query(EmailJob)
        .filter(
            EmailJob.employee_id == id,
            EmailJob.status == EmailJobStatus.SCHEDULED,
        )
        .all()
    )
    for job in unsent_jobs:
        job.status = EmailJobStatus.CANCELLED
        job.cancelled_at = datetime.utcnow()

    db.commit()
    db.refresh(employee)
    return employee


@router.get("/{id}/email-history", response_model=List[EmailJobResponse])
def get_employee_email_history(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves full email audit history for an employee."""
    employee = db.query(Employee).filter(Employee.id == id).first()
    if not employee:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EMPLOYEE_NOT_FOUND",
            message=f"Employee with ID {id} not found",
        )

    jobs = (
        db.query(EmailJob)
        .filter(EmailJob.employee_id == id)
        .order_by(EmailJob.created_at.desc())
        .all()
    )
    return jobs


@router.get("/{id}/audit-logs")
def get_employee_audit_logs(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves full feedback and reminder audit timeline for an employee."""
    employee = db.query(Employee).filter(Employee.id == id).first()
    if not employee:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EMPLOYEE_NOT_FOUND",
            message=f"Employee with ID {id} not found",
        )

    from app.models.feedback_record import AuditLog
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.employee_id == id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )
    return logs
