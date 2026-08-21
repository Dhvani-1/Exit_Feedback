from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    total_employees: int
    scheduled_employees: int
    cancelled_employees: int
    due_this_month: int
    emails_scheduled: int
    emails_sent: int
    emails_failed: int
    emails_due_today: int
    feedback_pending: int = 0
    feedback_submitted: int = 0
    feedback_expired: int = 0
    submission_rate: float = 0.0

