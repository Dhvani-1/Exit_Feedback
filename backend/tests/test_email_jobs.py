from datetime import datetime, date, timedelta
from app.models.employee import Employee, EmployeeStatus
from app.models.email_job import EmailJob, EmailJobStatus, EmailType
from app.services.backfill_service import backfill_missing_email_jobs


def test_employee_creation_schedules_email_job(auth_client, db):
    payload = {
        "full_name": "Email Test User",
        "personal_email": "test.email@company.com",
        "last_working_date": "2026-01-31",
    }
    res = auth_client.post("/api/employees", json=payload)
    assert res.status_code == 201
    emp_id = res.json()["id"]

    # Verify scheduled email job was created automatically
    job = db.query(EmailJob).filter(EmailJob.employee_id == emp_id).first()
    assert job is not None
    assert job.email_type == EmailType.EXIT_FEEDBACK_INITIAL
    assert job.status == EmailJobStatus.SCHEDULED
    assert job.idempotency_key == f"EXIT_FEEDBACK_INITIAL:{emp_id}"
    assert job.recipient_email == "test.email@company.com"


def test_idempotent_backfill_service(auth_client, db):
    # Create employee manually without email job to simulate existing Phase 1 record
    emp = Employee(
        full_name="Old Employee",
        personal_email="old.emp@gmail.com",
        last_working_date=date(2026, 5, 10),
        feedback_due_date=date(2026, 8, 10),
        status=EmployeeStatus.SCHEDULED,
        version=1,
    )
    db.add(emp)
    db.commit()

    # Run backfill first time
    created_count = backfill_missing_email_jobs(db)
    assert created_count >= 1

    # Run backfill second time (idempotency check: 0 new jobs created)
    re_created_count = backfill_missing_email_jobs(db)
    assert re_created_count == 0


def test_update_lwd_and_email_syncs_unsent_job(auth_client, db):
    payload = {
        "full_name": "Sync Test",
        "personal_email": "original.email@company.com",
        "last_working_date": "2026-02-15",
    }
    res = auth_client.post("/api/employees", json=payload)
    emp_data = res.json()
    emp_id = emp_data["id"]

    # Update LWD and personal email
    update_payload = {
        "full_name": "Sync Test Modified",
        "personal_email": "updated.email@company.com",
        "last_working_date": "2026-03-31",
        "version": emp_data["version"],
    }
    update_res = auth_client.put(f"/api/employees/{emp_id}", json=update_payload)
    assert update_res.status_code == 200

    job = db.query(EmailJob).filter(EmailJob.employee_id == emp_id).first()
    assert job.recipient_email == "updated.email@company.com"


def test_transactional_employee_cancellation_cancels_job(auth_client, db):
    payload = {
        "full_name": "Cancel User",
        "personal_email": "cancel.user@company.com",
        "last_working_date": "2026-04-10",
    }
    res = auth_client.post("/api/employees", json=payload)
    emp_id = res.json()["id"]

    # Cancel employee
    cancel_res = auth_client.post(f"/api/employees/{emp_id}/cancel")
    assert cancel_res.status_code == 200

    job = db.query(EmailJob).filter(EmailJob.employee_id == emp_id).first()
    assert job.status == EmailJobStatus.CANCELLED
    assert job.cancelled_at is not None


def test_reschedule_api_allowed_only_for_scheduled(auth_client, db):
    payload = {
        "full_name": "Reschedule User",
        "personal_email": "reschedule@company.com",
        "last_working_date": "2026-06-01",
    }
    res = auth_client.post("/api/employees", json=payload)
    emp_id = res.json()["id"]

    future_time = (datetime.utcnow() + timedelta(days=10)).isoformat()
    reschedule_res = auth_client.post(
        f"/api/email/employees/{emp_id}/reschedule",
        json={"scheduled_at": future_time},
    )
    assert reschedule_res.status_code == 200
    assert reschedule_res.json()["status"] == EmailJobStatus.SCHEDULED


def test_retry_api_allowed_only_for_failed_jobs(auth_client, db):
    payload = {
        "full_name": "Retry User",
        "personal_email": "retry.user@company.com",
        "last_working_date": "2026-07-01",
    }
    res = auth_client.post("/api/employees", json=payload)
    emp_id = res.json()["id"]

    job = db.query(EmailJob).filter(EmailJob.employee_id == emp_id).first()
    
    # Attempting to retry a SCHEDULED job should fail with 409
    retry_scheduled_res = auth_client.post(f"/api/email/employees/{emp_id}/retry")
    assert retry_scheduled_res.status_code == 409

    # Manually set job to FAILED
    job.status = EmailJobStatus.FAILED
    job.last_error = "Provider Connection Error"
    db.commit()

    # Retry API should succeed
    retry_res = auth_client.post(f"/api/email/employees/{emp_id}/retry")
    assert retry_res.status_code == 200
    assert retry_res.json()["status"] == EmailJobStatus.SCHEDULED
    assert retry_res.json()["last_error"] is None
