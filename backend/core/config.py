"""
Application configuration using Pydantic settings
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""

    # Project info
    PROJECT_NAME: str = "MultiPrompt Sandbox"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"

    # CORS - can be set via CORS_ALLOWED_ORIGINS env var (comma-separated)
    CORS_ALLOWED_ORIGINS: str = ""

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Get allowed origins from env var or use defaults for dev"""
        if self.CORS_ALLOWED_ORIGINS:
            return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",")]
        # Default origins for local development
        return [
            "http://localhost:4200",
            "http://localhost:3000",
            "http://localhost:8080",
        ]

    # Database - can use DATABASE_URL directly or construct from components
    DATABASE_URL: str = ""
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_NAME: str = ""

    # Google Cloud / Gemini Configuration
    GEMINI_API_KEY: str = ""
    GCP_PROJECT_ID: str = ""
    GEMINI_MODEL: str = "gemini-pro-vision"
    GCS_BUCKET_NAME: str = ""  # GCS bucket for image uploads
    STORAGE_TYPE: str = "local" # local or gcs
    UPLOAD_DIR: str = "uploads" # Directory for local storage

    # LangChain Configuration
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""

    # Agent Configuration
    MAX_ITERATIONS: int = 10
    AGENT_TIMEOUT: int = 300  # seconds

    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]

    # Security - SECRET_KEY must be provided via environment variable
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:4200"

    # Admin emails - comma-separated list of emails that should be admin on first login
    ADMIN_EMAILS: str = ""

    # Allowed email domains for access control (comma-separated, e.g., "gmail.com,google.com")
    ALLOWED_EMAIL_DOMAINS: str = ""

    @property
    def ADMIN_EMAIL_LIST(self) -> List[str]:
        """Get list of admin emails from env var"""
        if self.ADMIN_EMAILS:
            return [email.strip().lower() for email in self.ADMIN_EMAILS.split(",")]
        return []

    @property
    def ALLOWED_DOMAIN_LIST(self) -> List[str]:
        """Get list of allowed email domains for access control"""
        if self.ALLOWED_EMAIL_DOMAINS:
            return [domain.strip().lower() for domain in self.ALLOWED_EMAIL_DOMAINS.split(",")]
        return []

    class Config:
        env_file = ".env"
        case_sensitive = True

    def validate_production_settings(self):
        """Validate that critical settings are properly configured for production"""
        errors = []
        # SECRET_KEY is always required
        if not self.SECRET_KEY:
            errors.append("SECRET_KEY must be set via environment variable")

        if self.ENVIRONMENT == "production":
            if not self.DATABASE_URL and not self.DB_PASSWORD:
                errors.append("DATABASE_URL or DB_PASSWORD must be set in production")
            if not self.GOOGLE_CLIENT_ID:
                errors.append("GOOGLE_CLIENT_ID must be set in production")
            if not self.GOOGLE_CLIENT_SECRET:
                errors.append("GOOGLE_CLIENT_SECRET must be set in production")

        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")


# Create settings instance
settings = Settings()
settings.validate_production_settings()
