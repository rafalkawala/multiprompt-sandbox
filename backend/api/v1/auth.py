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

    # Log authentication attempt for debugging mobile issues
    user_agent = request.headers.get("user-agent", "unknown")
    has_cookie = bool(auth_token)
    has_auth_header = "Authorization" in request.headers

    logger.debug(
        f"Auth attempt - Cookie: {has_cookie}, Header: {has_auth_header}, "
        f"UA: {user_agent[:100]}"
    )

    # Try to get token from cookie first, then fall back to Authorization header
    token = auth_token
    token_source = "cookie"
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            token_source = "header"

    if not token:
        logger.warning(
            f"No token found - Cookie: {has_cookie}, Header: {has_auth_header}, "
            f"UA: {user_agent[:100]}"
        )
        raise credentials_exception

    logger.debug(f"Token found in {token_source}")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning(f"No email in token payload, source: {token_source}")
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"JWT decode error: {str(e)}, source: {token_source}")
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        logger.warning(f"User not found in DB: {email}")
        raise credentials_exception
    if not user.is_active:
        logger.warning(f"Inactive user attempted login: {email}")
        raise HTTPException(status_code=400, detail="Inactive user")

    logger.debug(f"Auth successful for {email} via {token_source}")
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

        # Get user info
        email = userinfo.get("email")
        google_id = userinfo.get("id")
        name = userinfo.get("name")
        picture = userinfo.get("picture")

        # Check email domain restriction
        allowed_domains = settings.ALLOWED_DOMAIN_LIST
        if allowed_domains:
            email_domain = email.lower().split('@')[-1]
            if email_domain not in allowed_domains:
                logger.warning(f"Access denied for {email} - domain {email_domain} not in allowed list: {allowed_domains}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Only users from approved domains are allowed."
                )

        # Check if user exists in database - only existing users can log in
        user = db.query(User).filter(User.email == email).first()

        if not user:
            logger.warning(f"Access denied for {email} - user not found in database")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Your account has not been provisioned. Please contact an administrator."
            )

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Access denied for {email} - user account is deactivated")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Your account has been deactivated."
            )

        # Update existing user info
        user.google_id = google_id
        user.name = name
        user.picture_url = picture
        user.last_login_at = datetime.utcnow()
        db.commit()
        logger.info(f"User logged in: {email}")

        # Create JWT token
        jwt_token = create_access_token(
            data={"sub": user.email, "role": user.role}
        )

        # Redirect to frontend with token in URL hash (avoids third-party cookie issues)
        redirect_url = f"{settings.FRONTEND_URL}/auth/callback#token={jwt_token}"
        response = RedirectResponse(url=redirect_url)

        # Also set cookie as fallback for same-origin setups
        is_production = settings.ENVIRONMENT == "production"
        response.set_cookie(
            key="auth_token",
            value=jwt_token,
            httponly=True,
            secure=is_production,
            samesite="none" if is_production else "lax",
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

    # Match the cookie settings used during login to ensure proper deletion
    is_production = settings.ENVIRONMENT == "production"
    response.delete_cookie(
        key="auth_token",
        path="/",
        httponly=True,
        secure=is_production,
        samesite="none" if is_production else "lax"
    )

    # Also clear the token from localStorage on the frontend side
    # (Note: This is handled by frontend, backend just clears the cookie)
    return response
