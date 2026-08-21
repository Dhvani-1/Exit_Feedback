from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base


class EmailJobStatus:
    SCHEDULED = "SCHEDULED"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    ALL_STATUSES = {SCHEDULED, PROCESSING, SENT, FAILED, CANCELLED}


class EmailType:
    EXIT_FEEDBACK_INITIAL = "EXIT_FEEDBACK_INITIAL"
    EXIT_FEEDBACK_REMINDER_1 = "EXIT_FEEDBACK_REMINDER_1"
    EXIT_FEEDBACK_REMINDER_2 = "EXIT_FEEDBACK_REMINDER_2"
    EXIT_FEEDBACK_REMINDER_3 = "EXIT_FEEDBACK_REMINDER_3"


class EmailJob(Base):
    __tablename__ = "email_jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    email_type = Column(String(50), nullable=False, default=EmailType.EXIT_FEEDBACK_INITIAL)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=False)
    recipient_email = Column(String(100), index=True, nullable=False)
    scheduled_at = Column(DateTime, index=True, nullable=False)
    status = Column(String(30), default=EmailJobStatus.SCHEDULED, index=True, nullable=False)
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    last_attempt_at = Column(DateTime, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    worker_id = Column(String(100), nullable=True)
    sent_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    template_version = Column(String(20), nullable=True, default="1.0")
    message_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = relationship("Employee", backref="email_jobs")

    __table_args__ = (
        UniqueConstraint("employee_id", "email_type", name="uq_employee_email_type"),
    )
