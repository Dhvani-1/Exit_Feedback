from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.services.report_service import (
    generate_employee_report,
    generate_feedback_report,
    generate_email_report,
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/reports", tags=["Report Generation & Export"])


class EmployeeReportRequest(BaseModel):
    date_filter: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    feedback_status: Optional[str] = None


class FeedbackReportRequest(BaseModel):
    date_filter: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class EmailReportRequest(BaseModel):
    date_filter: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    email_type: Optional[str] = None
    status: Optional[str] = None


def format_report_filename(prefix: str, start_date: Optional[str], end_date: Optional[str]) -> str:
    """Generates clean, sanitized filename for report exports."""
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    if start_date and end_date:
        s_clean = start_date[:10]
        e_clean = end_date[:10]
        return f"{prefix}_{s_clean}_to_{e_clean}.xlsx"
    return f"{prefix}_{today_str}.xlsx"


@router.post("/employees")
def export_employee_report(
    payload: EmployeeReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exports comprehensive Employee Exit Feedback Report (.xlsx).
    Requires HR authentication.
    """
    excel_bytes = generate_employee_report(
        db,
        date_filter=payload.date_filter,
        start_date=payload.start_date,
        end_date=payload.end_date,
        emp_status=payload.status,
        feedback_status=payload.feedback_status,
    )
    filename = format_report_filename("employee_report", payload.start_date, payload.end_date)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/feedback")
def export_feedback_report(
    payload: FeedbackReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exports Feedback Focused Lifecycle Report (.xlsx).
    Requires HR authentication.
    """
    excel_bytes = generate_feedback_report(
        db,
        date_filter=payload.date_filter,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    filename = format_report_filename("feedback_report", payload.start_date, payload.end_date)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/email-jobs")
def export_email_report(
    payload: EmailReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exports Email Dispatch History Report (.xlsx).
    Requires HR authentication.
    """
    excel_bytes = generate_email_report(
        db,
        date_filter=payload.date_filter,
        start_date=payload.start_date,
        end_date=payload.end_date,
        email_type=payload.email_type,
        job_status=payload.status,
    )
    filename = format_report_filename("email_report", payload.start_date, payload.end_date)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
