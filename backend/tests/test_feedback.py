import pytest
from datetime import datetime, timedelta
from app.models.employee import Employee, EmployeeStatus
from app.models.email_job import EmailJob, EmailJobStatus, EmailType
from app.models.feedback_record import FeedbackRecord, FeedbackStatus
from app.services.reminder_service import (
    ensure_feedback_record,
    generate_secure_token,
    check_and_expire_feedback,
)


def test_feedback_record_initialization(db):
    """Verifies feedback record and secure token creation at initialization."""
    emp = Employee(
        full_name="Alice Smith",
        personal_email="alice.smith@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    record = ensure_feedback_record(db, emp)
    assert record is not None
    assert record.employee_id == emp.id
    assert len(record.feedback_token) > 20
    assert record.status == FeedbackStatus.PENDING
    assert "/feedback/" in record.form_url


def test_feedback_token_uniqueness(db):
    """Verifies that each employee receives a distinct, unique feedback token."""
    t1 = generate_secure_token()
    t2 = generate_secure_token()
    assert t1 != t2


def test_public_feedback_get_endpoint(client, db):
    """Tests GET /api/feedback/{token} public validation endpoint."""
    emp = Employee(
        full_name="Bob Jones",
        personal_email="bob.jones@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    record = ensure_feedback_record(db, emp)

    res = client.get(f"/api/feedback/{record.feedback_token}")
    assert res.status_code == 200
    data = res.json()
    assert data["token"] == record.feedback_token
    assert data["status"] == "PENDING"
    assert data["employee_name"] == "Bob Jones"


def test_public_feedback_submit_endpoint_idempotency(client, db):
    """Tests POST /api/feedback/{token}/submit public submission & idempotency."""
    emp = Employee(
        full_name="Charlie Brown",
        personal_email="charlie@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    record = ensure_feedback_record(db, emp)

    # First submission
    res1 = client.post(f"/api/feedback/{record.feedback_token}/submit", json={"submission_source": "CUSTOM_FORM"})
    assert res1.status_code == 200
    assert res1.json()["status"] == "SUBMITTED"
    assert res1.json()["already_submitted"] is False

    first_submitted_at = res1.json()["submitted_at"]

    # Second submission (Idempotent check)
    res2 = client.post(f"/api/feedback/{record.feedback_token}/submit", json={"submission_source": "CUSTOM_FORM"})
    assert res2.status_code == 200
    assert res2.json()["status"] == "SUBMITTED"
    assert res2.json()["already_submitted"] is True
    assert res2.json()["submitted_at"] == first_submitted_at


def test_expired_feedback_token(client, db):
    """Tests that expired feedback tokens prevent submission."""
    emp = Employee(
        full_name="David Miller",
        personal_email="david@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    record = ensure_feedback_record(db, emp)
    # Manually set expires_at in the past
    record.expires_at = datetime.utcnow() - timedelta(days=1)
    db.commit()

    res = client.post(f"/api/feedback/{record.feedback_token}/submit")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "FEEDBACK_EXPIRED"
