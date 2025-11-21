"""
User management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import logging

from core.database import SessionLocal
from models.user import User, UserRole
from api.v1.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic models
class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    picture_url: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    role: str = UserRole.USER.value


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


def require_admin(token: str, db: Session) -> User:
    """Require admin role"""
    user = get_current_user(token, db)
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    token = authorization.replace("Bearer ", "")
    require_admin(token, db)

    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        UserResponse(
            id=str(u.id),
            email=u.email,
            name=u.name,
            picture_url=u.picture_url,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at,
            last_login_at=u.last_login_at
        )
        for u in users
    ]


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """Create a new user (admin only)"""
    token = authorization.replace("Bearer ", "")
    require_admin(token, db)

    # Check if user already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Validate role
    if user_data.role not in [r.value for r in UserRole]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}"
        )

    user = User(
        email=user_data.email,
        name=user_data.name,
        role=user_data.role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"Created user: {user.email} with role: {user.role}")

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    token = authorization.replace("Bearer ", "")
    require_admin(token, db)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """Update user (admin only)"""
    token = authorization.replace("Bearer ", "")
    require_admin(token, db)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user_data.name is not None:
        user.name = user_data.name

    if user_data.role is not None:
        if user_data.role not in [r.value for r in UserRole]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}"
            )
        user.role = user_data.role

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    logger.info(f"Updated user: {user.email}")

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at
    )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)"""
    token = authorization.replace("Bearer ", "")
    admin = require_admin(token, db)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deletion
    if str(user.id) == str(admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    db.delete(user)
    db.commit()

    logger.info(f"Deleted user: {user.email}")

    return {"message": f"User {user.email} deleted successfully"}
