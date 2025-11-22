"""
Application configuration using Pydantic settings
"""
from pydantic_settings import BaseSettings
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

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:4200",
        "http://localhost:3000",
        "http://localhost:8080",
        "https://multiprompt-frontend-h7qqra6pma-uc.a.run.app",
        "https://multiprompt-frontend-595703335416.us-central1.run.app"
    ]

    # Database - can use DATABASE_URL directly or construct from components
    DATABASE_URL: str = ""
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_USER: str = "user"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "appdb"

    # Google Cloud / Gemini Configuration
    GEMINI_API_KEY: str = ""
    GCP_PROJECT_ID: str = ""
    GEMINI_MODEL: str = "gemini-pro-vision"

    # LangChain Configuration
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""

    # Agent Configuration
    MAX_ITERATIONS: int = 10
    AGENT_TIMEOUT: int = 300  # seconds

    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:4200"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
