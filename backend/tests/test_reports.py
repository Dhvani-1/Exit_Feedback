import io
import openpyxl
import pytest


def test_export_employee_report(auth_client, db):
    """Verifies generating employee Excel report with readable headers and no secrets."""
    payload = {"date_filter": "all_time"}
    res = auth_client.post("/api/reports/employees", json=payload)
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument" in res.headers["content-type"]

    wb = openpyxl.load_workbook(io.BytesIO(res.content))
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    assert rows[0][0] == "Full Name"
    assert rows[0][1] == "Personal Email"
    # Ensure sensitive tokens are NOT columns
    assert "feedback_token" not in rows[0]
    assert "jwt_token" not in rows[0]


def test_export_feedback_report(auth_client, db):
    """Verifies generating feedback focused Excel report."""
    payload = {"date_filter": "this_month"}
    res = auth_client.post("/api/reports/feedback", json=payload)
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument" in res.headers["content-type"]


def test_export_email_report(auth_client, db):
    """Verifies generating email delivery Excel report."""
    payload = {"date_filter": "last_30_days"}
    res = auth_client.post("/api/reports/email-jobs", json=payload)
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument" in res.headers["content-type"]


def test_unauthenticated_reports_rejected(client):
    """Verifies unauthenticated report export requests return 401."""
    res = client.post("/api/reports/employees", json={})
    assert res.status_code == 401
