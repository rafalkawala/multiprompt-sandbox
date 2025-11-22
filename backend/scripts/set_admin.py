#!/usr/bin/env python3
"""
Script to set a user as admin directly in the database.
Usage: python set_admin.py <email>
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from core.config import settings

def set_admin(email: str):
    """Set user role to admin"""
    # Build database URL
    if settings.DATABASE_URL:
        db_url = settings.DATABASE_URL
    else:
        db_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Update user role
        result = conn.execute(
            text("UPDATE users SET role = 'admin' WHERE email = :email RETURNING id, email, role"),
            {"email": email}
        )
        row = result.fetchone()
        conn.commit()

        if row:
            print(f"Updated user {row[1]} to role: {row[2]}")
        else:
            print(f"User with email {email} not found")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python set_admin.py <email>")
        sys.exit(1)

    set_admin(sys.argv[1])
