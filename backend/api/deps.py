from typing import Generator
from fastapi import Depends, HTTPException, status
from models.user import User
from models.user import UserRole
from api.v1.auth import get_current_user
from core.database import SessionLocal
from sqlalchemy.orm import Session

__all__ = ['get_db', 'require_write_access', 'get_current_user']

def get_db() -> Generator[Session, None, None]:
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_write_access(current_user: User = Depends(get_current_user)) -> User:
    """Require user to have write access (not a viewer)"""
    if current_user.role == UserRole.VIEWER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers have read-only access. Cannot create, update, or delete resources."
        )
    return current_user
