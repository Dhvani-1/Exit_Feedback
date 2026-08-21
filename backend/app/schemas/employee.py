from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class EmployeeCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100, description="Full Name of Employee")
    personal_email: EmailStr = Field(..., description="Valid Personal Email Address")
    last_working_date: date = Field(..., description="Last Working Date (YYYY-MM-DD)")
    designation: Optional[str] = Field(None, max_length=100, description="Job Title / Designation")
    start_date: Optional[date] = Field(None, description="Start Date / Joining Date (YYYY-MM-DD)")
    tenure: Optional[str] = Field(None, max_length=50, description="Tenure with Company")


class EmployeeUpdate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100, description="Full Name of Employee")
    personal_email: EmailStr = Field(..., description="Valid Personal Email Address")
    last_working_date: date = Field(..., description="Last Working Date (YYYY-MM-DD)")
    designation: Optional[str] = Field(None, max_length=100, description="Job Title / Designation")
    start_date: Optional[date] = Field(None, description="Start Date / Joining Date (YYYY-MM-DD)")
    tenure: Optional[str] = Field(None, max_length=50, description="Tenure with Company")
    version: int = Field(..., description="Optimistic locking version number for concurrency control")


class EmployeeResponse(BaseModel):
    id: int
    full_name: str
    personal_email: EmailStr
    last_working_date: date
    designation: Optional[str] = None
    start_date: Optional[date] = None
    tenure: Optional[str] = None
    feedback_due_date: date
    status: str
    feedback_status: Optional[str] = "PENDING"
    feedback_submitted_at: Optional[datetime] = None
    feedback_expires_at: Optional[datetime] = None
    version: int
    created_at: datetime
    updated_at: datetime

    @property
    def employee_name(self) -> str:
        return self.full_name

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    id: int
    employee_id: int
    event_type: str
    details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeePaginatedResponse(BaseModel):
    items: List[EmployeeResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
