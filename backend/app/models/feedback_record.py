from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base


class FeedbackStatus:
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    EXPIRED = "EXPIRED"

    ALL_STATUSES = {PENDING, SUBMITTED, EXPIRED}


class AuditActorType:
    SYSTEM = "SYSTEM"
    HR_USER = "HR_USER"
    EMPLOYEE = "EMPLOYEE"
    EXTERNAL_PROVIDER = "EXTERNAL_PROVIDER"
    WORKER = "WORKER"


class FeedbackRecord(Base):
    __tablename__ = "feedback_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    feedback_token = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(30), default=FeedbackStatus.PENDING, index=True, nullable=False)
    form_url = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    submission_source = Column(String(50), nullable=True)  # CUSTOM_FORM, WEBHOOK, MANUAL
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = relationship("Employee", backref="feedback_record")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), index=True, nullable=False)
    actor_type = Column(String(50), default=AuditActorType.SYSTEM, nullable=True)
    actor_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    employee = relationship("Employee", backref="audit_logs")
