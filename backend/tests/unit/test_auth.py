"""
Tests for authentication module
Located at: backend/api/v1/auth.py

These tests cover JWT token creation/validation and user authentication.
All external dependencies (database, OAuth, HTTP calls) are mocked.
"""
import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
from unittest.mock import Mock, AsyncMock, patch
from jose import jwt

# Import functions to test
from api.v1.auth import (
    create_access_token,
    get_current_user,
)
from core.config import settings
from models.user import User, UserRole


class TestCreateAccessToken:
    """Test JWT token creation"""

    def test_create_access_token_with_default_expiry(self, mock_settings):
        """
        Test that create_access_token generates a valid JWT with default expiration

        Expected: Token is created with exp claim set to default expiry time
        """
        # Arrange
        user_data = {"sub": "test@example.com", "role": "user"}

        # Act
        token = create_access_token(user_data)

        # Assert
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify token contents
        payload = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        assert payload["sub"] == "test@example.com"
        assert payload["role"] == "user"
        assert "exp" in payload

    def test_create_access_token_with_custom_expiry(self, mock_settings):
        """
        Test that create_access_token respects custom expiration time

        Expected: Token exp claim is approximately custom expiry delta from now
        """
        # Arrange
        user_data = {"sub": "admin@example.com", "role": "admin"}
        custom_expiry = timedelta(minutes=60)

        # Record time before creating token
        before_creation = datetime.utcnow()

        # Act
        token = create_access_token(user_data, expires_delta=custom_expiry)

        # Assert - decode and verify the exp is within expected range
        payload = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM],
            options={"verify_exp": False}
        )

        # Calculate expected expiry range (allow 5 second tolerance)
        expected_min = before_creation + custom_expiry - timedelta(seconds=5)
        expected_max = before_creation + custom_expiry + timedelta(seconds=5)
        actual_exp = datetime.utcfromtimestamp(payload["exp"])

        assert expected_min <= actual_exp <= expected_max

    def test_create_access_token_includes_all_data(self, mock_settings):
        """
        Test that all provided data is included in the token payload

        Expected: Token contains all key-value pairs from input data
        """
        # Arrange
        user_data = {
            "sub": "test@example.com",
            "role": "admin",
            "user_id": "uuid-1234",
            "custom_field": "custom_value"
        }

        # Act
        token = create_access_token(user_data)

        # Assert
        payload = jwt.decode(
            token,
            mock_settings.SECRET_KEY,
            algorithms=[mock_settings.ALGORITHM]
        )
        assert payload["sub"] == "test@example.com"
        assert payload["role"] == "admin"
        assert payload["user_id"] == "uuid-1234"
        assert payload["custom_field"] == "custom_value"


class TestGetCurrentUser:
    """Test user authentication from JWT token"""

    @pytest.mark.asyncio
    async def test_get_current_user_from_cookie_success(self, mock_db_session, sample_admin_user, mock_settings):
        """
        Test that get_current_user successfully extracts user from cookie token

        Expected: User is returned when valid token is in cookie
        """
        # Arrange - Create a valid JWT token
        token = jwt.encode(
            {"sub": sample_admin_user.email, "role": sample_admin_user.role},
            mock_settings.SECRET_KEY,
            algorithm=mock_settings.ALGORITHM
        )

        # Mock database to return the user
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_admin_user

        # Create mock request with cookie
        mock_request = Mock(spec=Request)
        mock_request.headers = {"user-agent": "test-agent"}

        # Act
        result = await get_current_user(
            request=mock_request,
            db=mock_db_session,
            auth_token=token
        )

        # Assert
        assert result == sample_admin_user
        assert result.email == "admin@test.com"
        assert result.role == UserRole.ADMIN.value

    @pytest.mark.asyncio
    async def test_get_current_user_from_header_success(self, mock_db_session, sample_regular_user, mock_settings):
        """
        Test that get_current_user successfully extracts user from Authorization header

        Expected: User is returned when valid Bearer token is in header
        """
        # Arrange - Create a valid JWT token
        token = jwt.encode(
            {"sub": sample_regular_user.email, "role": sample_regular_user.role},
            mock_settings.SECRET_KEY,
            algorithm=mock_settings.ALGORITHM
        )

        # Mock database to return the user
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_regular_user

        # Create mock request with Authorization header but no cookie
        # Use a class that supports both get() and 'in' operator
        class MockHeaders(dict):
            def get(self, key, default=None):
                return super().get(key, default)

        mock_request = Mock(spec=Request)
        mock_request.headers = MockHeaders({
            "user-agent": "test-agent",
            "Authorization": f"Bearer {token}"
        })

        # Act
        result = await get_current_user(
            request=mock_request,
            db=mock_db_session,
            auth_token=None  # No cookie
        )

        # Assert
        assert result == sample_regular_user
        assert result.email == "user@test.com"

    @pytest.mark.asyncio
    async def test_get_current_user_no_token_raises_401(self, mock_db_session, mock_settings):
        """
        Test that get_current_user raises 401 when no token is provided

        Expected: HTTPException with 401 status code
        """
        # Arrange - No token in cookie or header
        mock_request = Mock(spec=Request)
        mock_request.headers = {"user-agent": "test-agent"}

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=mock_request,
                db=mock_db_session,
                auth_token=None
            )

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token_raises_401(self, mock_db_session, mock_settings):
        """
        Test that get_current_user raises 401 when token is invalid/malformed

        Expected: HTTPException with 401 status code
        """
        # Arrange - Invalid JWT token
        invalid_token = "this.is.not.a.valid.jwt.token"

        mock_request = Mock(spec=Request)
        mock_request.headers = {"user-agent": "test-agent"}

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=mock_request,
                db=mock_db_session,
                auth_token=invalid_token
            )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_inactive_user_raises_400(self, mock_db_session, sample_inactive_user, mock_settings):
        """
        Test that get_current_user raises 400 when user is inactive

        Expected: HTTPException with 400 status code and "Inactive user" detail
        """
        # Arrange - Create valid token for inactive user
        token = jwt.encode(
            {"sub": sample_inactive_user.email, "role": sample_inactive_user.role},
            mock_settings.SECRET_KEY,
            algorithm=mock_settings.ALGORITHM
        )

        # Mock database to return inactive user
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_inactive_user

        mock_request = Mock(spec=Request)
        mock_request.headers = {"user-agent": "test-agent"}

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=mock_request,
                db=mock_db_session,
                auth_token=token
            )

        assert exc_info.value.status_code == 400
        assert "Inactive user" in exc_info.value.detail


# ============================================================================
# TODO: Add more authentication tests (Priority: HIGH)
# ============================================================================
#
# Add these tests to increase coverage to 80%+:
#
# 1. test_google_login_returns_auth_url()
#    - Test /google/login endpoint returns OAuth URL
#
# 2. test_google_callback_creates_user_session()
#    - Test successful OAuth callback flow
#
# 3. test_google_callback_domain_restriction()
#    - Test email domain validation in callback
#
# 4. test_google_callback_user_not_found_raises_403()
#    - Test that users not in DB cannot log in
#
# 5. test_logout_clears_cookie()
#    - Test /logout endpoint clears auth cookie
#
# 6. test_get_current_user_expired_token_raises_401()
#    - Test expired JWT tokens are rejected
#
# 7. test_get_current_user_missing_email_in_payload_raises_401()
#    - Test tokens without 'sub' claim are rejected
#
# 8. test_get_current_user_user_not_in_db_raises_401()
#    - Test tokens for non-existent users are rejected
#
# 9. test_google_callback_updates_existing_user()
#    - Test returning user's info is updated
#
# 10. test_google_callback_sets_cookie_correctly()
#     - Test cookie is set with correct attributes
#
# See TESTING_GUIDE.md for examples and patterns to follow.
# ============================================================================
