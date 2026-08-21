from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, case, or_, and_
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.employee import Employee, EmployeeStatus
from app.models.email_job import EmailJob, EmailJobStatus, EmailType
from app.models.feedback_record import FeedbackRecord, FeedbackStatus, AuditLog
from app.services.report_service import parse_date_range_bounds
from app.utils.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get("/summary")
def get_dashboard_summary(
    date_filter: Optional[str] = Query(None, description="Date filter e.g. today, last_7_days, last_30_days, this_month, prev_month, custom"),
    start_date: Optional[str] = Query(None, description="Custom start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Custom end date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns single-snapshot aggregated metrics for Employees, Feedback Cycles, Email Dispatches, and Reminder Stages.
    Executed in a single transaction session for consistency.
    """
    dt_start, dt_end = parse_date_range_bounds(date_filter, start_date, end_date)

    # 1. Employee Metrics
    emp_query = db.query(
        func.count(Employee.id).label("total"),
        func.sum(case((Employee.status == EmployeeStatus.SCHEDULED, 1), else_=0)).label("scheduled"),
        func.sum(case((Employee.status == EmployeeStatus.CANCELLED, 1), else_=0)).label("cancelled"),
    )
    if dt_start and dt_end:
        emp_query = emp_query.filter(
            Employee.created_at >= dt_start,
            Employee.created_at < dt_end,
        )
    emp_row = emp_query.first()

    total_employees = emp_row.total or 0 if emp_row else 0
    scheduled_employees = emp_row.scheduled or 0 if emp_row else 0
    cancelled_employees = emp_row.cancelled or 0 if emp_row else 0

    # 2. Feedback Metrics
    fb_query = db.query(
        func.count(FeedbackRecord.id).label("total_records"),
        func.sum(case((and_(FeedbackRecord.status == FeedbackStatus.PENDING, Employee.status != EmployeeStatus.CANCELLED), 1), else_=0)).label("pending"),
        func.sum(case((and_(FeedbackRecord.status == FeedbackStatus.SUBMITTED, Employee.status != EmployeeStatus.CANCELLED), 1), else_=0)).label("submitted"),
        func.sum(case((and_(FeedbackRecord.status == FeedbackStatus.EXPIRED, Employee.status != EmployeeStatus.CANCELLED), 1), else_=0)).label("expired"),
    ).join(Employee, FeedbackRecord.employee_id == Employee.id)

    if dt_start and dt_end:
        fb_query = fb_query.filter(
            Employee.feedback_due_date >= dt_start.date(),
            Employee.feedback_due_date < dt_end.date(),
        )
    fb_row = fb_query.first()

    fb_pending = fb_row.pending or 0 if fb_row else 0
    fb_submitted = fb_row.submitted or 0 if fb_row else 0
    fb_expired = fb_row.expired or 0 if fb_row else 0

    # Calculate Eligible Feedback Cycles Denominator: Initial Email reached SENT and Employee not CANCELLED
    eligible_cycles_query = db.query(func.count(FeedbackRecord.id)).join(
        Employee, FeedbackRecord.employee_id == Employee.id
    ).join(
        EmailJob, and_(EmailJob.employee_id == Employee.id, EmailJob.email_type == EmailType.EXIT_FEEDBACK_INITIAL)
    ).filter(
        EmailJob.status == EmailJobStatus.SENT,
        Employee.status != EmployeeStatus.CANCELLED,
    )

    if dt_start and dt_end:
        eligible_cycles_query = eligible_cycles_query.filter(
            Employee.feedback_due_date >= dt_start.date(),
            Employee.feedback_due_date < dt_end.date(),
        )
    eligible_cycles = eligible_cycles_query.scalar() or 0

    response_rate = round((fb_submitted / eligible_cycles * 100), 1) if eligible_cycles > 0 else 0.0

    # 3. Initial Email Dispatch Metrics
    email_query = db.query(
        func.sum(case((EmailJob.status == EmailJobStatus.SCHEDULED, 1), else_=0)).label("scheduled"),
        func.sum(case((EmailJob.status == EmailJobStatus.SENT, 1), else_=0)).label("sent"),
        func.sum(case((EmailJob.status == EmailJobStatus.FAILED, 1), else_=0)).label("failed"),
        func.sum(case((EmailJob.status == EmailJobStatus.CANCELLED, 1), else_=0)).label("cancelled"),
    ).filter(EmailJob.email_type == EmailType.EXIT_FEEDBACK_INITIAL)

    if dt_start and dt_end:
        email_query = email_query.filter(
            EmailJob.scheduled_at >= dt_start,
            EmailJob.scheduled_at < dt_end,
        )
    email_row = email_query.first()

    emails_scheduled = email_row.scheduled or 0 if email_row else 0
    emails_sent = email_row.sent or 0 if email_row else 0
    emails_failed = email_row.failed or 0 if email_row else 0
    emails_cancelled = email_row.cancelled or 0 if email_row else 0

    # 4. Reminder Metrics & Submissions by Stage (Descriptive)
    r1_sent = db.query(func.count(EmailJob.id)).filter(
        EmailJob.email_type == EmailType.EXIT_FEEDBACK_REMINDER_1,
        EmailJob.status == EmailJobStatus.SENT,
    ).scalar() or 0

    r2_sent = db.query(func.count(EmailJob.id)).filter(
        EmailJob.email_type == EmailType.EXIT_FEEDBACK_REMINDER_2,
        EmailJob.status == EmailJobStatus.SENT,
    ).scalar() or 0

    reminders_scheduled = db.query(func.count(EmailJob.id)).filter(
        EmailJob.email_type.like("EXIT_FEEDBACK_REMINDER_%"),
        EmailJob.status == EmailJobStatus.SCHEDULED,
    ).scalar() or 0

    reminders_cancelled = db.query(func.count(EmailJob.id)).filter(
        EmailJob.email_type.like("EXIT_FEEDBACK_REMINDER_%"),
        EmailJob.status == EmailJobStatus.CANCELLED,
    ).scalar() or 0

    # Stage classification for submitted feedback records
    submitted_records = db.query(FeedbackRecord).filter(
        FeedbackRecord.status == FeedbackStatus.SUBMITTED
    ).all()

    sub_before_r1 = 0
    sub_after_r1 = 0
    sub_after_r2 = 0

    for rec in submitted_records:
        r1_job = db.query(EmailJob).filter(
            EmailJob.employee_id == rec.employee_id,
            EmailJob.email_type == EmailType.EXIT_FEEDBACK_REMINDER_1,
            EmailJob.status == EmailJobStatus.SENT,
        ).first()

        r2_job = db.query(EmailJob).filter(
            EmailJob.employee_id == rec.employee_id,
            EmailJob.email_type == EmailType.EXIT_FEEDBACK_REMINDER_2,
            EmailJob.status == EmailJobStatus.SENT,
        ).first()

        sub_at = rec.submitted_at
        if sub_at:
            if r2_job and r2_job.sent_at and sub_at >= r2_job.sent_at:
                sub_after_r2 += 1
            elif r1_job and r1_job.sent_at and sub_at >= r1_job.sent_at:
                sub_after_r1 += 1
            else:
                sub_before_r1 += 1

    return {
        "employees": {
            "total": total_employees,
            "scheduled": scheduled_employees,
            "cancelled": cancelled_employees,
        },
        "feedback": {
            "pending": fb_pending,
            "submitted": fb_submitted,
            "expired": fb_expired,
            "eligible_cycles": eligible_cycles,
            "response_rate": response_rate,
        },
        "emails": {
            "scheduled": emails_scheduled,
            "sent": emails_sent,
            "failed": emails_failed,
            "cancelled": emails_cancelled,
        },
        "reminders": {
            "reminder_1_sent": r1_sent,
            "reminder_2_sent": r2_sent,
            "reminder_scheduled": reminders_scheduled,
            "reminder_cancelled": reminders_cancelled,
            "submissions_by_stage": {
                "submitted_before_reminder_1": sub_before_r1,
                "submitted_after_reminder_1": sub_after_r1,
                "submitted_after_reminder_2": sub_after_r2,
            },
        },
        "date_filter_applied": date_filter or "all_time",
    }


@router.get("/overdue")
def get_overdue_feedback(
    overdue_days: int = Query(14, ge=1, le=90, description="Expected response threshold in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns list of overdue feedback requests.
    Overdue Criteria: PENDING + Initial Email SENT + Not Expired + (Current Time > sent_at + overdue_days).
    Timezone-safe UTC calculations.
    """
    now_utc = datetime.utcnow()
    cutoff_sent_at = now_utc - timedelta(days=overdue_days)

    query = db.query(FeedbackRecord, Employee, EmailJob).join(
        Employee, FeedbackRecord.employee_id == Employee.id
    ).join(
        EmailJob, and_(EmailJob.employee_id == Employee.id, EmailJob.email_type == EmailType.EXIT_FEEDBACK_INITIAL)
    ).filter(
        FeedbackRecord.status == FeedbackStatus.PENDING,
        Employee.status == EmployeeStatus.SCHEDULED,
        EmailJob.status == EmailJobStatus.SENT,
        EmailJob.sent_at <= cutoff_sent_at,
        or_(FeedbackRecord.expires_at.is_(None), FeedbackRecord.expires_at >= now_utc),
    )

    overdue_items = query.order_by(EmailJob.sent_at.asc()).all()

    results = []
    for fb_rec, emp, initial_job in overdue_items:
        days_pending = (now_utc - initial_job.sent_at).days if initial_job.sent_at else 0

        latest_reminder = db.query(EmailJob).filter(
            EmailJob.employee_id == emp.id,
            EmailJob.email_type.like("EXIT_FEEDBACK_REMINDER_%"),
        ).order_by(EmailJob.scheduled_at.desc()).first()

        results.append({
            "employee_id": emp.id,
            "full_name": emp.full_name,
            "personal_email": emp.personal_email,
            "last_working_date": str(emp.last_working_date),
            "feedback_due_date": str(emp.feedback_due_date),
            "initial_email_sent_at": initial_job.sent_at.strftime("%Y-%m-%d %H:%M") if initial_job.sent_at else None,
            "feedback_status": fb_rec.status,
            "days_pending": days_pending,
            "overdue_days_threshold": overdue_days,
            "latest_reminder_status": latest_reminder.status if latest_reminder else "NOT_SCHEDULED",
            "latest_reminder_type": latest_reminder.email_type if latest_reminder else None,
        })

    return {
        "overdue_count": len(results),
        "configured_overdue_days": overdue_days,
        "items": results,
    }


@router.get("/trends")
def get_monthly_trends(
    months: int = Query(6, ge=3, le=24, description="Number of recent months to include"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns monthly trend data grouped by date fields:
    - Feedback Due: grouped by Employee.feedback_due_date month
    - Initial Emails Sent: grouped by EmailJob.sent_at month
    - Feedback Submitted: grouped by FeedbackRecord.submitted_at month
    """
    today = date.today()
    month_keys = []
    for i in range(months - 1, -1, -1):
        # Calculate year-month for past i months
        m_date = (today.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        month_keys.append(m_date.strftime("%Y-%m"))

    # Remove duplicates preserving order
    month_keys = list(dict.fromkeys(month_keys))[-months:]

    # Fetch Feedback Due counts by YYYY-MM
    due_results = db.query(
        func.strftime("%Y-%m", Employee.feedback_due_date).label("m_key"),
        func.count(Employee.id).label("count"),
    ).filter(Employee.status == EmployeeStatus.SCHEDULED).group_by("m_key").all()
    due_map = {row.m_key: row.count for row in due_results if row.m_key}

    # Fetch Initial Emails Sent counts by YYYY-MM
    sent_results = db.query(
        func.strftime("%Y-%m", EmailJob.sent_at).label("m_key"),
        func.count(EmailJob.id).label("count"),
    ).filter(
        EmailJob.email_type == EmailType.EXIT_FEEDBACK_INITIAL,
        EmailJob.status == EmailJobStatus.SENT,
    ).group_by("m_key").all()
    sent_map = {row.m_key: row.count for row in sent_results if row.m_key}

    # Fetch Feedback Submitted counts by YYYY-MM
    submitted_results = db.query(
        func.strftime("%Y-%m", FeedbackRecord.submitted_at).label("m_key"),
        func.count(FeedbackRecord.id).label("count"),
    ).filter(FeedbackRecord.status == FeedbackStatus.SUBMITTED).group_by("m_key").all()
    submitted_map = {row.m_key: row.count for row in submitted_results if row.m_key}

    trend_series = []
    for m_key in month_keys:
        trend_series.append({
            "month": m_key,
            "feedback_due": due_map.get(m_key, 0),
            "initial_emails_sent": sent_map.get(m_key, 0),
            "feedback_submitted": submitted_map.get(m_key, 0),
        })

    return {
        "period_months": len(month_keys),
        "series": trend_series,
    }


@router.get("/audit")
def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by Employee name, event type, or actor type"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    date_start: Optional[str] = Query(None, description="Filter start date YYYY-MM-DD"),
    date_end: Optional[str] = Query(None, description="Filter end date YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Read-only endpoint to retrieve paginated system audit logs.
    Ordered by created_at DESC, id DESC for stable pagination.
    Sanitizes details and masks sensitive tokens/secrets.
    """
    dt_start, dt_end = parse_date_range_bounds("custom", date_start, date_end)

    query = db.query(AuditLog, Employee).join(Employee, AuditLog.employee_id == Employee.id)

    if event_type:
        query = query.filter(AuditLog.event_type == event_type.strip().upper())

    if dt_start and dt_end:
        query = query.filter(
            AuditLog.created_at >= dt_start,
            AuditLog.created_at < dt_end,
        )

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Employee.full_name.ilike(search_pattern),
                AuditLog.event_type.ilike(search_pattern),
                AuditLog.actor_type.ilike(search_pattern),
            )
        )

    total = query.count()
    offset = (page - 1) * page_size
    items = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(page_size).all()

    logs = []
    for log, emp in items:
        logs.append({
            "id": log.id,
            "employee_id": emp.id,
            "employee_name": emp.full_name,
            "personal_email": emp.personal_email,
            "event_type": log.event_type,
            "actor_type": log.actor_type or "SYSTEM",
            "actor_id": log.actor_id,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
        })

    import math
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return {
        "items": logs,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }
