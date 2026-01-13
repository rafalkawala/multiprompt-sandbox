#!/usr/bin/env python3
"""
Verify pgvector extension is available and provide helpful error messages.
This script runs before migrations to ensure the database is properly configured.
"""
import sys
import os
from sqlalchemy import create_engine, text

def verify_pgvector(database_url: str) -> bool:
    """
    Verify that pgvector extension is available in the database.

    Returns:
        True if pgvector is available, False otherwise
    """
    try:
        engine = create_engine(database_url)

        with engine.connect() as conn:
            # Check if pgvector is available as an extension
            result = conn.execute(text(
                "SELECT * FROM pg_available_extensions WHERE name = 'vector';"
            ))
            extension = result.fetchone()

            if not extension:
                print("[ERROR] pgvector extension is not available in this PostgreSQL instance")
                print("\n[CLOUD SQL SETUP REQUIRED]")
                print("   Cloud SQL for PostgreSQL 11+ supports pgvector.")
                print("   However, the extension must be available in your instance.")
                print("\n[SOLUTION]")
                print("   1. Verify your Cloud SQL instance is PostgreSQL 11+")
                print("   2. Check if pgvector is supported in your Cloud SQL tier")
                print("   3. Contact Google Cloud Support if pgvector is not available")
                print("\n[DOCS] https://cloud.google.com/sql/docs/postgres/extensions")
                return False

            print(f"[OK] pgvector extension is available (version {extension[1]})")

            # Check if extension is already installed
            result = conn.execute(text(
                "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
            ))
            installed = result.fetchone()

            if installed:
                print(f"[OK] pgvector extension is already installed (version {installed[1]})")
            else:
                print("[WARN] pgvector extension is available but not yet installed")
                print("       It will be installed automatically by Alembic migration bdb80060ab5g")

                # Verify we have permission to create extensions
                try:
                    # Test if we can create/drop the extension (rollback after)
                    conn.execute(text("BEGIN;"))
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    print("[OK] Database user has permission to create extensions")
                    conn.execute(text("ROLLBACK;"))
                except Exception as perm_error:
                    print(f"[ERROR] Cannot create pgvector extension: {perm_error}")
                    print("\n[PERMISSION ISSUE]")
                    print("   The database user needs permission to create extensions.")
                    print("\n   For Cloud SQL, grant cloudsqlsuperuser role:")
                    print(f"   ALTER USER {os.getenv('DB_USER', 'your_user')} WITH SUPERUSER;")
                    print("\n   Or run as a superuser:")
                    print("   gcloud sql connect <instance> --user=postgres")
                    print("   CREATE EXTENSION IF NOT EXISTS vector;")
                    return False

            return True

    except Exception as e:
        print(f"[ERROR] Failed to connect to database: {e}")
        print("\n[DATABASE CONNECTION ISSUE]")
        print("   Verify DATABASE_URL or individual DB_* environment variables are set correctly")
        return False

def main():
    """Main entry point for the verification script."""
    print("\n" + "="*60)
    print("Verifying pgvector Extension Setup")
    print("="*60 + "\n")

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        # Try to build from individual components
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "")
        db_name = os.getenv("DB_NAME", "postgres")

        if not db_password:
            print("[WARN] DB_PASSWORD not set, attempting connection without password")

        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    success = verify_pgvector(database_url)

    print("\n" + "="*60)
    if success:
        print("[SUCCESS] pgvector verification PASSED")
        print("="*60 + "\n")
        sys.exit(0)
    else:
        print("[FAILED] pgvector verification FAILED")
        print("="*60 + "\n")
        print("[WARN] The application may not start correctly without pgvector.")
        print("       See error messages above for resolution steps.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
