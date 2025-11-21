"""
Seed script to create the initial admin user
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from core.database import SessionLocal, engine, Base
from models.user import User, UserRole

def seed_admin():
    """Create the initial admin user"""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin_email = "rafalkawtradegpt@gmail.com"

        # Check if admin already exists
        existing = db.query(User).filter(User.email == admin_email).first()
        if existing:
            print(f"Admin user {admin_email} already exists")
            if existing.role != UserRole.ADMIN.value:
                existing.role = UserRole.ADMIN.value
                db.commit()
                print(f"Updated role to admin")
            return

        # Create admin user
        admin = User(
            email=admin_email,
            name="Rafal Kawala",
            role=UserRole.ADMIN.value,
            is_active=True
        )
        db.add(admin)
        db.commit()
        print(f"Created admin user: {admin_email}")

    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
