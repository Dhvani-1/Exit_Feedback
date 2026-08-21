import logging
from app.database.connection import engine, SessionLocal
from app.database.base import Base
# Import all SQLAlchemy models to register them with Base.metadata
import app.models  # noqa: F401
from app.models.email_template import EmailTemplate

logger = logging.getLogger("init_db")

INITIAL_TEMPLATE_SUBJECT = "Confidential Employee Exit Feedback Request - {{ company_name }}"
INITIAL_TEMPLATE_BODY = """<div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333333; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
  <p>Dear {{ employee_name }},</p>
  
  <p>Thank you for your valuable service with <strong>{{ company_name }}</strong>{% if designation %} as <strong>{{ designation }}</strong>{% endif %}{% if start_date %} from <strong>{{ start_date }}</strong>{% endif %} to <strong>{{ last_working_date }}</strong>.</p>
  
  <p>During your time with us, you have been an important part of our organization, and we appreciate the contributions you have made{% if tenure %} throughout your <strong>{{ tenure }}</strong>{% endif %} with {{ company_name }}.</p>
  
  <p>As part of our exit process following your last working day on <strong>{{ last_working_date }}</strong>, we invite you to share your feedback and experiences with us. Your feedback will help us identify areas for improvement and continue building a better workplace for our employees.</p>
  
  <div style="margin: 25px 0;">
    <a href="{{ feedback_form_url }}" style="background-color: #0284c7; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Complete Exit Feedback Form &rarr;</a>
  </div>
  
  <p>If the button above does not work, please copy and paste the following URL into your browser:<br>
  <a href="{{ feedback_form_url }}" style="color: #0284c7; word-break: break-all;">{{ feedback_form_url }}</a></p>
  
  <p>We appreciate you taking the time to share your valuable feedback.</p>
  
  <p>Best regards,<br>
  <strong>Human Resources Team</strong><br>
  <strong>{{ company_name }}</strong></p>
</div>"""


def init_db():
    """
    Creates all database tables automatically and seeds initial email templates if empty.
    Safe to run on every startup (idempotent).
    """
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seed default initial email template if missing
        initial_tmpl = db.query(EmailTemplate).filter(EmailTemplate.template_key == "EXIT_FEEDBACK_INITIAL").first()
        if not initial_tmpl:
            tmpl = EmailTemplate(
                template_key="EXIT_FEEDBACK_INITIAL",
                subject=INITIAL_TEMPLATE_SUBJECT,
                body=INITIAL_TEMPLATE_BODY,
                version="1.0",
                is_active=True,
            )
            db.add(tmpl)
            db.commit()
            logger.info("Seeded default EXIT_FEEDBACK_INITIAL email template")
    except Exception as e:
        logger.error(f"Error seeding email templates: {e}")
    finally:
        db.close()
