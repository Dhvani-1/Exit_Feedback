import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Employee Exit Feedback Automation System"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api"

    # Database
    DATABASE_URL: str = "sqlite:///./exit_feedback.db"

    # JWT Security
    SECRET_KEY: str = "dev_secret_key_exit_feedback_automation_2026_super_secure_32bytes"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = False  # Set to True in production (HTTPS)
    COOKIE_SAMESITE: str = "lax"

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Environment
    ENVIRONMENT: str = "development"

    # Phase 2: Email Configuration
    EMAIL_MODE: str = "console"  # 'console' (simulated/log mode) or 'smtp'
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: str = "onlyapp.testing@gmail.com"
    EMAIL_FROM_NAME: str = "HR Department"
    
    # Phase 2: Default System Settings
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"
    DEFAULT_SEND_HOUR: int = 9
    DEFAULT_WEEKEND_BEHAVIOR: str = "SEND_ON_DUE_DATE"  # SEND_ON_DUE_DATE, NEXT_WORKING_DAY, PREVIOUS_WORKING_DAY
    DEFAULT_COMPANY_NAME: str = "Laxmi Organics Industries Ltd"
    DEFAULT_FEEDBACK_FORM_URL: str = "https://feedback.company.com/exit-form"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()


def get_settings() -> Settings:
    """Returns the application settings singleton."""
    return settings
