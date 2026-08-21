import pytest
from datetime import datetime, timedelta
from app.models.employee import Employee, EmployeeStatus
from app.models.feedback_record import FeedbackRecord, FeedbackStatus
from app.services.reminder_service import ensure_feedback_record


def test_webhook_submission_via_header(client, db):
    """Tests webhook feedback submission using X-Feedback-Token header."""
    emp = Employee(
        full_name="Ian Malcolm",
        personal_email="ian@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    record = ensure_feedback_record(db, emp)

    res = client.post(
        "/api/feedback/webhook",
        json={"source": "MS_FORMS"},
        headers={"X-Feedback-Token": record.feedback_token},
    )

    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert res.json()["already_submitted"] is False

    db.refresh(record)
    assert record.status == FeedbackStatus.SUBMITTED
    assert record.submission_source == "MS_FORMS"


def test_webhook_submission_via_body(client, db):
    """Tests webhook feedback submission using JSON body token field."""
    emp = Employee(
        full_name="Julia Roberts",
        personal_email="julia@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    record = ensure_feedback_record(db, emp)

    res = client.post(
        "/api/feedback/webhook",
        json={"token": record.feedback_token, "source": "TYPEFORM"},
    )

    assert res.status_code == 200
    assert res.json()["status"] == "success"

    db.refresh(record)
    assert record.status == FeedbackStatus.SUBMITTED


def test_webhook_idempotency(client, db):
    """Verifies duplicate webhook calls return success without creating duplicate events."""
    emp = Employee(
        full_name="Kevin Bacon",
        personal_email="kevin@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    record = ensure_feedback_record(db, emp)

    # Call 1
    res1 = client.post(
        "/api/feedback/webhook",
        json={"token": record.feedback_token, "source": "GOOGLE_FORMS"},
    )
    assert res1.status_code == 200
    assert res1.json()["already_submitted"] is False

    # Call 2
    res2 = client.post(
        "/api/feedback/webhook",
        json={"token": record.feedback_token, "source": "GOOGLE_FORMS"},
    )
    assert res2.status_code == 200
    assert res2.json()["already_submitted"] is True
