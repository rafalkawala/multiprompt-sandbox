"""
Google OAuth authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Cookie
from fastapi.responses import RedirectResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import httpx
import logging

from core.config import settings
from core.database import SessionLocal
from models.user import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()

# Security scheme for JWT
security = HTTPBearer()

# OAuth setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    auth_token: Optional[str] = Cookie(default=None)
) -> User:
    """Get current user from JWT token in HttpOnly cookie or Authorization header"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try to get token from cookie first, then fall back to Authorization header
    token = auth_token
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


@router.get("/google/login")
async def google_login():
    """Initiate Google OAuth login"""
    # Build the Google OAuth URL
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return {"auth_url": google_auth_url}


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    """Handle Google OAuth callback"""
    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                }
            )

            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.text}")
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            # Get user info from Google
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if userinfo_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info")

            userinfo = userinfo_response.json()

        # Get or create user
        email = userinfo.get("email")
        google_id = userinfo.get("id")
        name = userinfo.get("name")
        picture = userinfo.get("picture")

        user = db.query(User).filter(User.email == email).first()

        if not user:
            # Determine role - admin if email is in ADMIN_EMAILS list
            role = UserRole.ADMIN.value if email.lower() in settings.ADMIN_EMAIL_LIST else UserRole.USER.value

            # Create new user
            user = User(
                email=email,
                google_id=google_id,
                name=name,
                picture_url=picture,
                role=role,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created new user: {email} with role: {role}")
        else:
            # Update existing user
            user.google_id = google_id
            user.name = name
            user.picture_url = picture
            user.last_login_at = datetime.utcnow()
            db.commit()
            logger.info(f"Updated existing user: {email}")

        # Create JWT token
        jwt_token = create_access_token(
            data={"sub": user.email, "role": user.role}
        )

        # Redirect to frontend - cookie will be sent with subsequent requests
        redirect_url = f"{settings.FRONTEND_URL}/auth/callback"
        response = RedirectResponse(url=redirect_url)

        # Set secure HttpOnly cookie
        is_production = settings.ENVIRONMENT == "production"
        response.set_cookie(
            key="auth_token",
            value=jwt_token,
            httponly=True,
            secure=is_production,  # Only send over HTTPS in production
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "picture_url": current_user.picture_url,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None
    }


@router.post("/logout")
async def logout():
    """Logout endpoint - clears the auth cookie"""
    response = Response(content='{"message": "Logged out successfully"}', media_type="application/json")
    response.delete_cookie(
        key="auth_token",
        path="/",
        httponly=True,
        samesite="lax"
    )
    return response
