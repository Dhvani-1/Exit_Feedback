from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class EmailJobResponse(BaseModel):
    id: int
    employee_id: int
    email_type: str
    idempotency_key: str
    recipient_email: str
    sender_email: Optional[str] = "hr@company.com"
    scheduled_at: datetime
    status: str
    attempt_count: int
    max_attempts: int
    last_attempt_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    last_error: Optional[str] = None
    template_version: Optional[str] = None
    message_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RescheduleRequest(BaseModel):
    scheduled_at: datetime = Field(..., description="New scheduled ISO datetime in UTC")


class EmailJobPaginatedResponse(BaseModel):
    items: List[EmailJobResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
