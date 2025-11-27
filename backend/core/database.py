from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

# Construct database URL from components or use direct URL if provided
if settings.DATABASE_URL:
    db_url = settings.DATABASE_URL
else:
    db_url = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

engine = create_engine(
    db_url,
    pool_size=20,  # Increased from default 5 to handle more concurrent requests
    max_overflow=30,  # Increased from default 10 for burst traffic
    pool_timeout=60,  # Increased from default 30s
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
    # connect_args={"check_same_thread": False} # This is for SQLite only
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
