from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.database.base import Base


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    template_key = Column(String(50), unique=True, index=True, nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    version = Column(String(20), nullable=False, default="1.0")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
