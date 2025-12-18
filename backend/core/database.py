from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

# Construct database URL from components or use direct URL if provided
if settings.DATABASE_URL:
    db_url = settings.DATABASE_URL
else:
    db_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_engine(
    db_url,
    pool_size=5,  # Optimized for single instance: 5 persistent connections
    max_overflow=10,  # Allow burst up to 15 total connections (within db-f1-micro limit)
    pool_timeout=300,  # Wait up to 5 minutes for a connection instead of failing
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
    # connect_args={"check_same_thread": False} # This is for SQLite only
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Database session dependency generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
