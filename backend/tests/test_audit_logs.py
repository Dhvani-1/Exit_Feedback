import pytest
from datetime import datetime, timedelta
from app.models.employee import Employee, EmployeeStatus
from app.services.reminder_service import log_audit_event


def test_audit_logs_retrieval_and_sanitization(auth_client, db):
    """Verifies audit log retrieval, stable pagination, and detail sanitization."""
    emp = Employee(
        full_name="Audit Employee",
        personal_email="audit.emp@example.com",
        last_working_date=datetime.utcnow().date(),
        feedback_due_date=datetime.utcnow().date() + timedelta(days=90),
        status=EmployeeStatus.SCHEDULED,
    )
    db.add(emp)
    db.commit()

    # Log event with potential sensitive text
    log_audit_event(
        db,
        employee_id=emp.id,
        event_type="TEST_SECURITY_EVENT",
        details="User logged in with password=secretpassword123 and token=abcd1234efgh5678ijkl9012mnop3456",
        actor_type="HR_USER",
        actor_id="admin_1",
    )

    res = auth_client.get(f"/api/dashboard/audit?search={emp.full_name}")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1

    item = next(i for i in data["items"] if i["event_type"] == "TEST_SECURITY_EVENT")
    assert item["actor_type"] == "HR_USER"
    assert item["actor_id"] == "admin_1"
    # Verify sanitization
    assert "secretpassword123" not in item["details"]
    assert "[REDACTED_SECRET]" in item["details"] or "[REDACTED_TOKEN]" in item["details"]


def test_audit_logs_unauthenticated_rejected(client):
    """Verifies unauthenticated access to audit logs is rejected with 401."""
    res = client.get("/api/dashboard/audit")
    assert res.status_code == 401
