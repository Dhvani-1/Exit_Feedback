from datetime import datetime, timedelta
from app.models.email_job import EmailJob, EmailJobStatus
from app.services.worker_service import (
    claim_job,
    process_due_jobs,
    recover_stuck_processing_jobs,
)


def test_atomic_claim_job_concurrency(db, auth_client):
    payload = {
        "full_name": "Claim User",
        "personal_email": "claim@company.com",
        "last_working_date": "2026-01-15",
    }
    auth_client.post("/api/employees", json=payload)
    job = db.query(EmailJob).first()

    # Worker A claims job
    claimed_a = claim_job(db, job.id, "worker_A")
    assert claimed_a is True

    # Worker B attempts to claim same job immediately after
    claimed_b = claim_job(db, job.id, "worker_B")
    assert claimed_b is False


def test_worker_processes_due_job_successfully(db, auth_client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "EMAIL_MODE", "console")
    payload = {
        "full_name": "Worker User",
        "personal_email": "worker.user@company.com",
        "last_working_date": "2026-01-15",
    }
    res = auth_client.post("/api/employees", json=payload)
    emp_id = res.json()["id"]

    job = db.query(EmailJob).filter(EmailJob.employee_id == emp_id).first()
    # Force scheduled_at to past timestamp so worker finds it due
    job.scheduled_at = datetime.utcnow() - timedelta(minutes=10)
    db.commit()

    processed_count = process_due_jobs(db, worker_id="test_worker")
    assert processed_count == 1

    db.refresh(job)
    assert job.status == EmailJobStatus.SENT
    assert job.sent_at is not None
    assert job.message_id is not None
    assert job.message_id.startswith("SIMULATED-")


def test_stuck_processing_job_lease_recovery(db, auth_client):
    payload = {
        "full_name": "Stuck User",
        "personal_email": "stuck@company.com",
        "last_working_date": "2026-02-10",
    }
    res = auth_client.post("/api/employees", json=payload)
    emp_id = res.json()["id"]

    job = db.query(EmailJob).filter(EmailJob.employee_id == emp_id).first()
    
    # Simulate crashed worker: job stuck in PROCESSING with lease > 15 mins ago
    job.status = EmailJobStatus.PROCESSING
    job.processing_started_at = datetime.utcnow() - timedelta(minutes=20)
    db.commit()

    recovered_count = recover_stuck_processing_jobs(db, timeout_minutes=15)
    assert recovered_count == 1

    db.refresh(job)
    assert job.status == EmailJobStatus.SCHEDULED
    assert job.attempt_count == 1


def test_send_now_api_prevents_duplicate_send_on_already_sent_job(auth_client, db, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "EMAIL_MODE", "console")
    payload = {
        "full_name": "SendNow User",
        "personal_email": "sendnow@company.com",
        "last_working_date": "2026-03-01",
    }
    res = auth_client.post("/api/employees", json=payload)
    emp_id = res.json()["id"]

    # First Send Now call triggers email delivery -> status becomes SENT
    res1 = auth_client.post(f"/api/email/employees/{emp_id}/send-now")
    assert res1.status_code == 200
    assert res1.json()["status"] == EmailJobStatus.SENT

    # Second Send Now call is blocked with 409 EMAIL_ALREADY_SENT error
    res2 = auth_client.post(f"/api/email/employees/{emp_id}/send-now")
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "EMAIL_ALREADY_SENT"
