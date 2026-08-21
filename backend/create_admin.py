import os
import sys
import argparse

# Add parent directory to path so app modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import engine, SessionLocal
from app.database.base import Base
from app.models.user import User
from app.utils.security import hash_password


def create_admin_user(email: str, password: str, name: str, role: str):
    """Creates initial admin or HR user in database."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"[!] User with email '{email}' already exists.")
            return

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[OK] Successfully created user '{user.email}' with role '{user.role}'.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create initial HR or Admin user.")
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL", "hr@company.com"), help="User Email")
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD", "AdminPass123!"), help="User Password")
    parser.add_argument("--name", default=os.getenv("ADMIN_NAME", "HR Administrator"), help="User Name")
    parser.add_argument("--role", default=os.getenv("ADMIN_ROLE", "ADMIN"), help="User Role (ADMIN or HR)")

    args = parser.parse_args()
    create_admin_user(args.email, args.password, args.name, args.role)
