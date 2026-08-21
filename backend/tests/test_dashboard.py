import pytest
from datetime import datetime, timedelta
from app.models.employee import Employee, EmployeeStatus
from app.models.email_job import EmailJob, EmailJobStatus, EmailType
from app.models.feedback_record import FeedbackRecord, FeedbackStatus


def test_dashboard_summary_metrics_and_response_rate(auth_client, db):
    """Verifies dashboard summary metrics and exact response rate calculation."""
    # Create employee 1: Initial email SENT, feedback SUBMITTED
    emp1 = Employee(
        full_name="User One",
        personal_email="user1@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp1)
    db.commit()

    fb1 = FeedbackRecord(
        employee_id=emp1.id,
        feedback_token="tok1",
        status=FeedbackStatus.SUBMITTED,
        form_url="http://localhost/feedback/tok1",
        submitted_at=datetime.utcnow(),
    )
    db.add(fb1)

    job1 = EmailJob(
        employee_id=emp1.id,
        email_type=EmailType.EXIT_FEEDBACK_INITIAL,
        idempotency_key=f"EXIT_FEEDBACK_INITIAL:{emp1.id}",
        recipient_email=emp1.personal_email,
        scheduled_at=datetime.utcnow(),
        status=EmailJobStatus.SENT,
        sent_at=datetime.utcnow(),
    )
    db.add(job1)
    db.commit()

    # Create employee 2: Initial email SENT, feedback PENDING
    emp2 = Employee(
        full_name="User Two",
        personal_email="user2@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp2)
    db.commit()

    fb2 = FeedbackRecord(
        employee_id=emp2.id,
        feedback_token="tok2",
        status=FeedbackStatus.PENDING,
        form_url="http://localhost/feedback/tok2",
    )
    db.add(fb2)

    job2 = EmailJob(
        employee_id=emp2.id,
        email_type=EmailType.EXIT_FEEDBACK_INITIAL,
        idempotency_key=f"EXIT_FEEDBACK_INITIAL:{emp2.id}",
        recipient_email=emp2.personal_email,
        scheduled_at=datetime.utcnow(),
        status=EmailJobStatus.SENT,
        sent_at=datetime.utcnow(),
    )
    db.add(job2)
    db.commit()

    res = auth_client.get("/api/dashboard/summary")
    assert res.status_code == 200
    data = res.json()

    assert data["employees"]["total"] >= 2
    assert data["feedback"]["submitted"] >= 1
    assert data["feedback"]["pending"] >= 1
    assert data["feedback"]["eligible_cycles"] >= 2
    # 1 submitted / 2 eligible = 50.0%
    assert data["feedback"]["response_rate"] == 50.0


def test_dashboard_overdue_feedback(auth_client, db):
    """Verifies overdue calculation (PENDING + initial SENT + past overdue threshold)."""
    emp = Employee(
        full_name="Overdue User",
        personal_email="overdue@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    fb = FeedbackRecord(
        employee_id=emp.id,
        feedback_token="tok_overdue",
        status=FeedbackStatus.PENDING,
        form_url="http://localhost/feedback/tok_overdue",
    )
    db.add(fb)

    # Initial email sent 20 days ago (past default 14 day threshold)
    job = EmailJob(
        employee_id=emp.id,
        email_type=EmailType.EXIT_FEEDBACK_INITIAL,
        idempotency_key=f"EXIT_FEEDBACK_INITIAL:{emp.id}",
        recipient_email=emp.personal_email,
        scheduled_at=datetime.utcnow() - timedelta(days=20),
        status=EmailJobStatus.SENT,
        sent_at=datetime.utcnow() - timedelta(days=20),
    )
    db.add(job)
    db.commit()

    res = auth_client.get("/api/dashboard/overdue?overdue_days=14")
    assert res.status_code == 200
    data = res.json()
    assert data["overdue_count"] >= 1
    overdue_item = next(item for item in data["items"] if item["employee_id"] == emp.id)
    assert overdue_item["full_name"] == "Overdue User"
    assert overdue_item["days_pending"] >= 20


def test_dashboard_trends(auth_client, db):
    """Verifies monthly trend endpoint returns structured series."""
    res = auth_client.get("/api/dashboard/trends?months=6")
    assert res.status_code == 200
    data = res.json()
    assert "series" in data
    assert len(data["series"]) == 6
    assert "feedback_due" in data["series"][0]
    assert "initial_emails_sent" in data["series"][0]
    assert "feedback_submitted" in data["series"][0]


def test_dashboard_unauthenticated_rejected(client):
    """Verifies unauthenticated access to dashboard API is rejected with 401."""
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 401
