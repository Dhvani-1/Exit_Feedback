from pydantic import BaseModel, EmailStr, HttpUrl, Field, field_validator
import pytz


class SystemSettingsResponse(BaseModel):
    company_name: str
    feedback_form_url: str
    sender_email: str
    sender_name: str
    email_send_hour: int
    timezone: str
    weekend_behavior: str
    reminders_enabled: bool = True
    reminder_count: int = 2
    reminder_interval_days: int = 7
    feedback_expiry_days: int = 30
    feedback_base_url: str = "http://localhost:5173"
    email_mode: str = "Console / Simulation"
    email_provider: str = "Console"
    is_secret_configured: bool = False
    is_env_managed: bool = True


class SystemSettingsUpdate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=100)
    feedback_form_url: str = Field(..., description="Valid HTTP or HTTPS URL")
    sender_email: EmailStr
    sender_name: str = Field(..., min_length=1, max_length=100)
    email_send_hour: int = Field(..., ge=0, le=23, description="Send hour (0-23)")
    timezone: str = Field(..., description="IANA timezone string e.g. Asia/Kolkata")
    weekend_behavior: str = Field("SEND_ON_DUE_DATE", description="SEND_ON_DUE_DATE, NEXT_WORKING_DAY, or PREVIOUS_WORKING_DAY")
    reminders_enabled: bool = Field(True, description="Enable automatic reminder dispatches")
    reminder_count: int = Field(2, ge=0, le=5, description="Number of reminder emails (0-5)")
    reminder_interval_days: int = Field(7, ge=1, le=60, description="Interval in days between reminders")
    feedback_expiry_days: int = Field(30, ge=1, le=365, description="Days after which feedback token expires")
    feedback_base_url: str = Field("http://localhost:5173", description="Base frontend URL for feedback page")

    @field_validator("feedback_form_url", "feedback_base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith("http://") and not v.startswith("https://"):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_iana_timezone(cls, v: str) -> str:
        if v not in pytz.all_timezones:
            raise ValueError(f"'{v}' is not a valid IANA timezone name")
        return v

    @field_validator("weekend_behavior")
    @classmethod
    def validate_weekend_behavior(cls, v: str) -> str:
        valid_options = {"SEND_ON_DUE_DATE", "NEXT_WORKING_DAY", "PREVIOUS_WORKING_DAY"}
        if v not in valid_options:
            raise ValueError(f"weekend_behavior must be one of {valid_options}")
        return v


class TestEmailRequest(BaseModel):
    recipient_email: EmailStr = Field(..., description="Explicit recipient email for test message")
