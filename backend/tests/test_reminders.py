import pytest
from datetime import datetime, timedelta
from app.models.employee import Employee, EmployeeStatus
from app.models.email_job import EmailJob, EmailJobStatus, EmailType
from app.models.feedback_record import FeedbackRecord, FeedbackStatus
from app.services.reminder_service import (
    ensure_feedback_record,
    schedule_reminders_on_initial_sent,
    cancel_future_reminders,
)
from app.services.worker_service import process_due_jobs


def test_reminders_not_created_before_initial_sent(db):
    """Verifies reminder jobs are NOT created when initial email is SCHEDULED or FAILED."""
    emp = Employee(
        full_name="Eva Green",
        personal_email="eva@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    ensure_feedback_record(db, emp)

    # Initial email is SCHEDULED
    job = EmailJob(
        employee_id=emp.id,
        email_type=EmailType.EXIT_FEEDBACK_INITIAL,
        idempotency_key=f"EXIT_FEEDBACK_INITIAL:{emp.id}",
        recipient_email=emp.personal_email,
        scheduled_at=datetime.utcnow(),
        status=EmailJobStatus.SCHEDULED,
    )
    db.add(job)
    db.commit()

    # Query reminder jobs
    reminders = db.query(EmailJob).filter(
        EmailJob.employee_id == emp.id,
        EmailJob.email_type.like("EXIT_FEEDBACK_REMINDER_%"),
    ).all()

    assert len(reminders) == 0


def test_reminders_created_after_initial_sent(db, monkeypatch):
    """Verifies reminders are created and scheduled starting from initial sent_at time."""
    monkeypatch.setattr(
        "app.services.reminder_service.get_reminder_settings",
        lambda db: {
            "reminders_enabled": True,
            "reminder_count": 2,
            "reminder_interval_days": 7,
            "feedback_expiry_days": 30,
            "feedback_base_url": "http://localhost:5173",
        },
    )
    emp = Employee(
        full_name="Frank Wright",
        personal_email="frank@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    sent_time = datetime.utcnow() - timedelta(hours=1)
    schedule_reminders_on_initial_sent(db, emp.id, sent_time)

    reminders = db.query(EmailJob).filter(
        EmailJob.employee_id == emp.id,
        EmailJob.email_type.like("EXIT_FEEDBACK_REMINDER_%"),
    ).order_by(EmailJob.scheduled_at.asc()).all()

    assert len(reminders) == 2
    assert reminders[0].email_type == EmailType.EXIT_FEEDBACK_REMINDER_1
    assert reminders[1].email_type == EmailType.EXIT_FEEDBACK_REMINDER_2
    assert reminders[0].scheduled_at == sent_time + timedelta(days=7)
    assert reminders[1].scheduled_at == sent_time + timedelta(days=14)


def test_feedback_submission_cancels_reminders(client, db, monkeypatch):
    """Verifies submitting feedback cancels future scheduled reminder jobs."""
    monkeypatch.setattr(
        "app.services.reminder_service.get_reminder_settings",
        lambda db: {
            "reminders_enabled": True,
            "reminder_count": 2,
            "reminder_interval_days": 7,
            "feedback_expiry_days": 30,
            "feedback_base_url": "http://localhost:5173",
        },
    )
    emp = Employee(
        full_name="Grace Hopper",
        personal_email="grace@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    record = ensure_feedback_record(db, emp)
    sent_time = datetime.utcnow()
    schedule_reminders_on_initial_sent(db, emp.id, sent_time)

    # Confirm reminders are SCHEDULED
    active_reminders = db.query(EmailJob).filter(
        EmailJob.employee_id == emp.id,
        EmailJob.status == EmailJobStatus.SCHEDULED,
    ).all()
    assert len(active_reminders) == 2

    # Submit feedback
    res = client.post(f"/api/feedback/{record.feedback_token}/submit")
    assert res.status_code == 200

    # Confirm reminders are now CANCELLED
    cancelled_reminders = db.query(EmailJob).filter(
        EmailJob.employee_id == emp.id,
        EmailJob.status == EmailJobStatus.CANCELLED,
    ).all()
    assert len(cancelled_reminders) == 2


def test_worker_race_protection_skips_submitted_feedback(db, monkeypatch):
    """Verifies that if a reminder worker runs when feedback is SUBMITTED, it cancels the reminder instead of sending."""
    monkeypatch.setattr(
        "app.services.reminder_service.get_reminder_settings",
        lambda db: {
            "reminders_enabled": True,
            "reminder_count": 2,
            "reminder_interval_days": 7,
            "feedback_expiry_days": 30,
            "feedback_base_url": "http://localhost:5173",
        },
    )
    emp = Employee(
        full_name="Hank Pym",
        personal_email="hank@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    record = ensure_feedback_record(db, emp)
    schedule_reminders_on_initial_sent(db, emp.id, datetime.utcnow())

    # Manually set reminder scheduled_at to past so process_due_jobs picks it up
    r1 = db.query(EmailJob).filter(
        EmailJob.employee_id == emp.id,
        EmailJob.email_type == EmailType.EXIT_FEEDBACK_REMINDER_1,
    ).first()
    r1.scheduled_at = datetime.utcnow() - timedelta(minutes=10)

    # Simulate submission BEFORE worker processes
    record.status = FeedbackStatus.SUBMITTED
    db.commit()

    # Process worker jobs
    processed = process_due_jobs(db, worker_id="test_worker_race")

    # Re-query r1
    db.refresh(r1)
    assert r1.status == EmailJobStatus.CANCELLED
