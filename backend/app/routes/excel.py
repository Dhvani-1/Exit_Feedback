from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.employee import Employee, EmployeeStatus
from app.models.email_job import EmailJob, EmailJobStatus, EmailType
from app.services.excel_service import (
    parse_and_validate_excel,
    generate_excel_template,
    generate_error_report,
)
from app.services.date_calculator import calculate_feedback_due_date, compute_scheduled_at
from app.services.backfill_service import get_system_settings_dict
from app.services.reminder_service import ensure_feedback_record
from app.utils.security import get_current_user
from app.utils.exceptions import AppException

router = APIRouter(prefix="/employees", tags=["Excel Importer"])


class ConfirmImportRequest(BaseModel):
    valid_rows: List[Dict[str, Any]]


class ExportErrorReportRequest(BaseModel):
    invalid_rows: List[Dict[str, Any]]


@router.get("/excel-template")
def download_excel_template(
    current_user: User = Depends(get_current_user),
):
    """Downloads the standard Excel import template with exact 3 required headers."""
    content = generate_excel_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=Exit_Feedback_Import_Template.xlsx"
        },
    )


@router.post("/upload-preview")

async def upload_excel_preview(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Parses and validates uploaded Excel file.
    Returns preview statistics (total, valid, invalid, duplicate count) and error reasons without importing.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_FILE_TYPE",
            message="Only Excel files (.xlsx, .xls) are supported.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="FILE_TOO_LARGE",
            message="File size exceeds maximum limit of 5MB.",
        )

    result = parse_and_validate_excel(file_bytes, db)
    if "error_code" in result:
        raise AppException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code=result["error_code"],
            message=result["message"],
        )

    return result


@router.post("/import-confirm")
def confirm_excel_import(
    payload: ConfirmImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Confirms and executes batch creation of valid imported employees.
    Reuses existing date calculation, feedback record initialization, and initial email scheduling services.
    """
    imported_count = 0
    skipped_duplicates = 0

    sys_settings = get_system_settings_dict(db)

    for item in payload.valid_rows:
        if item.get("is_duplicate"):
            skipped_duplicates += 1
            continue

        p_email = item["personal_email"].strip().lower()
        lwd_str = item["last_working_date"]
        lwd_date = datetime.strptime(lwd_str, "%Y-%m-%d").date()

        # Re-check database duplicate inside transaction
        existing = db.query(Employee).filter(
            Employee.personal_email == p_email,
            Employee.last_working_date == lwd_date,
        ).first()

        if existing:
            skipped_duplicates += 1
            continue

        due_date = calculate_feedback_due_date(lwd_date)

        sd_str = item.get("start_date")
        sd_date = datetime.strptime(sd_str, "%Y-%m-%d").date() if sd_str else None

        employee = Employee(
            full_name=item["full_name"].strip(),
            personal_email=p_email,
            last_working_date=lwd_date,
            designation=item.get("designation"),
            start_date=sd_date,
            tenure=item.get("tenure"),
            feedback_due_date=due_date,
            status=EmployeeStatus.SCHEDULED,
            version=1,
        )

        db.add(employee)
        db.flush()  # populate employee.id

        ensure_feedback_record(db, employee)

        scheduled_at_utc = compute_scheduled_at(
            due_date,
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
        imported_count += 1

    db.commit()

    return {
        "status": "success",
        "imported_count": imported_count,
        "skipped_duplicates_count": skipped_duplicates,
        "total_processed": len(payload.valid_rows),
    }


@router.post("/export-error-report")
def export_error_report(
    payload: ExportErrorReportRequest,
    current_user: User = Depends(get_current_user),
):
    """Generates a downloadable Excel file containing error details for invalid rows."""
    content = generate_error_report(payload.invalid_rows)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=Import_Error_Report.xlsx"
        },
    )
