import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.base import Base
from app.database.connection import get_db
from app.models.user import User
from app.models.email_template import EmailTemplate
from app.models.system_setting import SystemSetting
from app.utils.security import hash_password

# In-memory SQLite database for isolated test runs
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Provides a fresh database session per test function with default templates and settings seeded."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        # Seed default initial email template for test suite
        t1 = EmailTemplate(
            template_key="EXIT_FEEDBACK_INITIAL",
            subject="Confidential Exit Feedback Request - {{company_name}}",
            body="<p>Dear {{employee_name}}, please fill form at {{feedback_form_url}}</p>",
            version="1.0",
            is_active=True,
        )
        t2 = EmailTemplate(
            template_key="EXIT_FEEDBACK_REMINDER_1",
            subject="Reminder 1: Confidential Exit Feedback Request - {{company_name}}",
            body="<p>Dear {{employee_name}}, please fill form at {{feedback_form_url}}</p>",
            version="1.0",
            is_active=True,
        )
        t3 = EmailTemplate(
            template_key="EXIT_FEEDBACK_REMINDER_2",
            subject="Reminder 2: Confidential Exit Feedback Request - {{company_name}}",
            body="<p>Dear {{employee_name}}, please fill form at {{feedback_form_url}}</p>",
            version="1.0",
            is_active=True,
        )
        session.add_all([t1, t2, t3])


        # Seed default system settings
        default_settings = [
            SystemSetting(key="company_name", value="Laxmi Organics Industries Ltd", description="Company Name"),
            SystemSetting(key="feedback_form_url", value="https://feedback.company.com/exit-form", description="Feedback URL"),
            SystemSetting(key="sender_email", value="hr@company.com", description="Sender Email"),
            SystemSetting(key="sender_name", value="HR Department", description="Sender Name"),
            SystemSetting(key="email_send_hour", value="9", description="Send Hour"),
            SystemSetting(key="timezone", value="Asia/Kolkata", description="Timezone"),
            SystemSetting(key="weekend_behavior", value="SEND_ON_DUE_DATE", description="Weekend Behavior"),
        ]
        for s in default_settings:
            session.add(s)
        session.commit()

        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Provides FastAPI TestClient connected to test database session."""
    def _get_test_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db):
    """Creates a standard HR user for authenticated testing."""
    user = User(
        name="HR Test User",
        email="hr.test@company.com",
        password_hash=hash_password("Password123!"),
        role="HR",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_client(client, test_user):
    """Logs in and returns TestClient with valid HttpOnly access token cookie set."""
    response = client.post(
        "/api/auth/login",
        json={"email": "hr.test@company.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    return client
