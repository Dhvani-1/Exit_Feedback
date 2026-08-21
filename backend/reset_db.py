import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database.connection import engine, SessionLocal
from app.models.employee import Employee
from app.models.email_job import EmailJob
from app.models.feedback_record import FeedbackRecord, AuditLog


def reset_test_data():
    """
    Clears all testing data (employees, email jobs, feedback records, audit logs)
    while preserving admin users and system settings so testing can be repeated easily.
    """
    db = SessionLocal()
    try:
        print("[*] Clearing test data tables...")
        
        # Delete dependent tables first to respect foreign key constraints
        num_audits = db.query(AuditLog).delete()
        num_feedback = db.query(FeedbackRecord).delete()
        num_jobs = db.query(EmailJob).delete()
        num_emps = db.query(Employee).delete()
        
        db.commit()
        print(f"[OK] Database cleared successfully!")
        print(f"     - Removed {num_audits} Audit Logs")
        print(f"     - Removed {num_feedback} Feedback Records")
        print(f"     - Removed {num_jobs} Email Jobs")
        print(f"     - Removed {num_emps} Employee Records")
        print("[+] Admin users and system settings were preserved.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to reset data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    reset_test_data()
