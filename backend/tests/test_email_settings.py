import pytest


def test_get_email_settings(auth_client, db):
    """Verifies getting system email settings returns actual configured values and mode without exposing secrets."""
    res = auth_client.get("/api/settings/email")
    assert res.status_code == 200
    data = res.json()
    assert "sender_email" in data
    assert "sender_name" in data
    assert "email_mode" in data
    assert "email_provider" in data
    assert "is_secret_configured" in data
    # Ensure password or secrets are NOT returned
    assert "smtp_password" not in data
    assert "password" not in data


def test_send_test_email(auth_client, db, monkeypatch):
    """Verifies dispatching a test email to an explicitly specified recipient."""
    from app.config import settings
    monkeypatch.setattr(settings, "EMAIL_MODE", "console")
    payload = {"recipient_email": "test.recipient@example.com"}
    res = auth_client.post("/api/settings/test-email", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "test.recipient@example.com" in data["message"]
    assert "message_id" in data
