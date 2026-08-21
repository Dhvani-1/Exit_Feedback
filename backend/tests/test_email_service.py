from app.services.email_service import send_email, is_retryable_error
from app.services.template_service import render_email_template


def test_is_retryable_error_classification():
    # Retryable errors
    assert is_retryable_error("SMTP connection timeout after 10 seconds") is True
    assert is_retryable_error("Temporary 500 Internal Server Error") is True
    assert is_retryable_error("429 Too Many Requests") is True

    # Non-retryable errors
    assert is_retryable_error("Invalid recipient email address syntax") is False
    assert is_retryable_error("User unknown in local recipient table (5.1.1)") is False
    assert is_retryable_error("SMTP Authentication Failed: invalid credentials") is False


def test_sandboxed_jinja2_template_rendering():
    template = "Hello {{employee_name}}, your exit date is {{last_working_date}} at {{company_name}}."
    context = {
        "employee_name": "Jane Doe",
        "last_working_date": "2026-04-30",
        "company_name": "Laxmi Organics",
        "unauthorized_var": "Should be ignored",
    }
    output = render_email_template(template, context)
    assert "Hello Jane Doe" in output
    assert "2026-04-30" in output
    assert "Laxmi Organics" in output
    assert "Should be ignored" not in output


def test_console_mode_simulated_email_delivery(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "EMAIL_MODE", "console")
    success, msg_id, error_str = send_email(
        recipient_email="test.recipient@example.com",
        subject="Test Exit Feedback",
        html_body="<p>Test Content</p>",
        idempotency_key="EXIT_FEEDBACK_INITIAL:999",
    )
    assert success is True
    assert msg_id.startswith("SIMULATED-")
    assert error_str is None
