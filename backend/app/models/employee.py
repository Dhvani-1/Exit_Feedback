from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, UniqueConstraint
from app.database.base import Base


class EmployeeStatus:
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"

    ALL_STATUSES = {SCHEDULED, CANCELLED}


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String(100), index=True, nullable=False)
    personal_email = Column(String(100), index=True, nullable=False)
    last_working_date = Column(Date, index=True, nullable=False)
    designation = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    tenure = Column(String(50), nullable=True)
    feedback_due_date = Column(Date, index=True, nullable=False)
    status = Column(String(30), default=EmployeeStatus.SCHEDULED, index=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)  # Optimistic locking version control
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("personal_email", "last_working_date", name="uq_personal_email_last_working_date"),
    )

    @property
    def employee_name(self) -> str:
        """Backward compatibility alias for full_name."""
        return self.full_name

    @property
    def employee_id(self) -> str:
        """Backward compatibility alias for ID string."""
        return f"EMP-{self.id}"

    @property
    def feedback_status(self) -> str:
        if hasattr(self, "feedback_record") and self.feedback_record:
            rec = self.feedback_record[0] if isinstance(self.feedback_record, list) else self.feedback_record
            return getattr(rec, "status", "PENDING")
        return "PENDING"

    @property
    def feedback_submitted_at(self):
        if hasattr(self, "feedback_record") and self.feedback_record:
            rec = self.feedback_record[0] if isinstance(self.feedback_record, list) else self.feedback_record
            return getattr(rec, "submitted_at", None)
        return None

    @property
    def feedback_expires_at(self):
        if hasattr(self, "feedback_record") and self.feedback_record:
            rec = self.feedback_record[0] if isinstance(self.feedback_record, list) else self.feedback_record
            return getattr(rec, "expires_at", None)
        return None
