"""
Shared pytest fixtures for unit tests

This file provides reusable fixtures and mocks for all unit tests.
Fixtures defined here are automatically available to all test files in tests/unit/
"""
import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Set dummy environment variables BEFORE importing any modules that use config
os.environ["SECRET_KEY"] = "test-secret-key-1234567890"
os.environ["ENVIRONMENT"] = "test"

# Add backend directory to Python path so we can import modules
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Import models for creating test data
from models.user import User, UserRole
from models.project import Project


# ============================================================================
# Sample Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_admin_user():
    """
    Create a sample admin user for testing

    Returns:
        User: Admin user with all fields populated

    Usage:
        def test_something(sample_admin_user):
            assert sample_admin_user.role == UserRole.ADMIN.value
    """
    return User(
        id="11111111-1111-1111-1111-111111111111",
        email="admin@test.com",
        google_id="google-123",
        name="Admin User",
        picture_url="https://example.com/avatar.jpg",
        role=UserRole.ADMIN.value,
        is_active=True,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        last_login_at=datetime(2024, 1, 15, 10, 30, 0)
    )


@pytest.fixture
def sample_regular_user():
    """
    Create a sample regular user for testing

    Returns:
        User: Regular user with standard permissions

    Usage:
        def test_something(sample_regular_user):
            assert sample_regular_user.role == UserRole.USER.value
    """
    return User(
        id="22222222-2222-2222-2222-222222222222",
        email="user@test.com",
        google_id="google-456",
        name="Regular User",
        picture_url="https://example.com/user-avatar.jpg",
        role=UserRole.USER.value,
        is_active=True,
        created_at=datetime(2024, 1, 10, 14, 0, 0),
        last_login_at=datetime(2024, 1, 15, 9, 0, 0)
    )


@pytest.fixture
def sample_inactive_user():
    """
    Create a sample inactive user for testing

    Returns:
        User: Inactive user (deactivated account)

    Usage:
        def test_something(sample_inactive_user):
            assert sample_inactive_user.is_active == False
    """
    return User(
        id="99999999-9999-9999-9999-999999999999",
        email="inactive@test.com",
        google_id="google-999",
        name="Inactive User",
        picture_url=None,
        role=UserRole.USER.value,
        is_active=False,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        last_login_at=None
    )


@pytest.fixture
def sample_project(sample_admin_user):
    """
    Create a sample project for testing

    Args:
        sample_admin_user: Admin user who owns the project

    Returns:
        Project: Sample project with all fields

    Usage:
        def test_something(sample_project):
            assert sample_project.name == "Test Project"
    """
    return Project(
        id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        name="Test Project",
        description="A test project for unit tests",
        question_text="Is this a test?",
        question_type="binary",
        created_by_id=sample_admin_user.id,
        created_at=datetime(2024, 1, 5, 10, 0, 0),
        updated_at=datetime(2024, 1, 10, 15, 30, 0)
    )


# ============================================================================
# Mock Database Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session(mocker):
    """
    Create a mocked database session

    This mock prevents real database calls and allows you to control
    what data is returned from queries.

    Returns:
        Mock: Mocked SQLAlchemy Session

    Usage:
        def test_something(mock_db_session, sample_admin_user):
            # Configure the mock to return specific data
            mock_db_session.query.return_value.filter.return_value.first.return_value = sample_admin_user

            # Now db.query(User).filter(...).first() will return sample_admin_user
            result = db.query(User).filter(User.email == "admin@test.com").first()
            assert result == sample_admin_user
    """
    mock_session = mocker.Mock(spec=Session)

    # Set up default behavior for common query patterns
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.query.return_value.filter.return_value.all.return_value = []
    mock_session.query.return_value.get.return_value = None

    # Mock commit/rollback/close to prevent errors
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    mock_session.close.return_value = None
    mock_session.add.return_value = None
    mock_session.delete.return_value = None

    return mock_session


# ============================================================================
# Mock External Services Fixtures
# ============================================================================

@pytest.fixture
def mock_httpx_client(mocker):
    """
    Create a mocked httpx.AsyncClient for HTTP requests

    Use this to mock LLM API calls, OAuth calls, etc.

    Returns:
        AsyncMock: Mocked httpx.AsyncClient

    Usage:
        @pytest.mark.asyncio
        async def test_api_call(mock_httpx_client):
            # Configure mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": "success"}
            mock_httpx_client.post.return_value = mock_response

            # Mock the client getter
            mocker.patch('httpx.AsyncClient', return_value=mock_httpx_client)

            # Now httpx calls will use the mock
            async with httpx.AsyncClient() as client:
                response = await client.post("https://api.example.com")
                assert response.json() == {"result": "success"}
    """
    mock_client = mocker.AsyncMock()

    # Set up default successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}
    mock_response.text = ""

    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response
    mock_client.put.return_value = mock_response
    mock_client.delete.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_gcs_client(mocker):
    """
    Create a mocked Google Cloud Storage client

    Returns:
        Mock: Mocked GCS Client

    Usage:
        def test_upload(mock_gcs_client):
            # Mock is already patched, just configure behavior
            mock_bucket = mock_gcs_client.bucket.return_value
            mock_blob = mock_bucket.blob.return_value

            # Test your GCS code
            from infrastructure.storage.gcs import GCSStorageProvider
            provider = GCSStorageProvider()
            await provider.upload_file("test.jpg", b"data")

            # Verify upload was called
            mock_blob.upload_from_string.assert_called_once()
    """
    mock_client = mocker.Mock()

    # Set up default bucket/blob structure
    mock_blob = Mock()
    mock_blob.upload_from_string.return_value = None
    mock_blob.download_as_bytes.return_value = b"fake file content"
    mock_blob.public_url = "https://storage.googleapis.com/bucket/file.jpg"

    mock_bucket = Mock()
    mock_bucket.blob.return_value = mock_blob

    mock_client.bucket.return_value = mock_bucket

    # Patch the GCS client globally
    mocker.patch('google.cloud.storage.Client', return_value=mock_client)

    return mock_client


@pytest.fixture
def mock_oauth_client(mocker):
    """
    Create a mocked OAuth client for Google authentication

    Returns:
        Mock: Mocked OAuth client

    Usage:
        def test_oauth_flow(mock_oauth_client):
            # OAuth client is already mocked
            # Configure the authorize_access_token response
            mock_oauth_client.google.authorize_access_token.return_value = {
                "access_token": "fake-token",
                "userinfo": {
                    "email": "test@example.com",
                    "name": "Test User"
                }
            }
    """
    mock_oauth = mocker.Mock()

    # Set up Google OAuth provider
    mock_google = Mock()
    mock_google.authorize_access_token.return_value = {
        "access_token": "fake-access-token",
        "id_token": "fake-id-token"
    }

    mock_oauth.google = mock_google

    # Patch the OAuth instance
    mocker.patch('api.v1.auth.oauth', mock_oauth)

    return mock_oauth


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================

@pytest.fixture
def client(mock_db_session):
    """
    Create a FastAPI TestClient with mocked database

    This provides a test client that can make HTTP requests to your API
    without starting a real server.

    Args:
        mock_db_session: Mocked database session

    Returns:
        TestClient: FastAPI test client

    Usage:
        def test_endpoint(client):
            response = client.get("/api/v1/health")
            assert response.status_code == 200
    """
    from main import app
    from api.v1.auth import get_db as auth_get_db
    from api.deps import get_db as deps_get_db

    # Override the database dependency for all modules
    def override_get_db():
        return mock_db_session

    app.dependency_overrides[auth_get_db] = override_get_db
    app.dependency_overrides[deps_get_db] = override_get_db

    # Create test client
    test_client = TestClient(app)

    # Return client and clean up after test
    yield test_client

    # Cleanup - remove dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(client, sample_admin_user):
    """
    Create a FastAPI TestClient with authentication already set up

    This provides a test client where the current_user dependency
    is already overridden to return the admin user.

    Args:
        client: Base FastAPI test client
        sample_admin_user: Admin user to authenticate as

    Returns:
        TestClient: Authenticated test client

    Usage:
        def test_protected_endpoint(authenticated_client):
            # Requests are already authenticated as admin
            response = authenticated_client.get("/api/v1/protected")
            assert response.status_code == 200
    """
    from main import app
    from api.v1.auth import get_current_user as auth_get_current_user
    from api.deps import get_current_user as deps_get_current_user
    from api.deps import require_write_access

    # Override authentication to return admin user for all modules
    app.dependency_overrides[auth_get_current_user] = lambda: sample_admin_user
    app.dependency_overrides[deps_get_current_user] = lambda: sample_admin_user
    app.dependency_overrides[require_write_access] = lambda: sample_admin_user

    yield client

    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def mock_settings(mocker):
    """
    Mock application settings for testing

    Returns:
        Mock: Mocked settings object

    Usage:
        def test_with_custom_settings(mock_settings):
            mock_settings.SECRET_KEY = "test-secret-key"
            mock_settings.ENVIRONMENT = "test"
    """
    from core.config import settings

    # Create a mock settings object
    mock_settings_obj = Mock()
    mock_settings_obj.SECRET_KEY = "test-secret-key-123456789"
    mock_settings_obj.ALGORITHM = "HS256"
    mock_settings_obj.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    mock_settings_obj.GOOGLE_CLIENT_ID = "test-client-id"
    mock_settings_obj.GOOGLE_CLIENT_SECRET = "test-client-secret"
    mock_settings_obj.GOOGLE_REDIRECT_URI = "http://localhost:8000/api/v1/auth/google/callback"
    mock_settings_obj.FRONTEND_URL = "http://localhost:4200"
    mock_settings_obj.ALLOWED_ORIGINS = ["http://localhost:4200", "http://localhost:3000"]
    mock_settings_obj.ALLOWED_DOMAIN_LIST = []
    mock_settings_obj.ENVIRONMENT = "test"

    # Patch the settings import
    mocker.patch('core.config.settings', mock_settings_obj)
    mocker.patch('api.v1.auth.settings', mock_settings_obj)

    return mock_settings_obj


@pytest.fixture
def fixed_datetime(mocker):
    """
    Mock datetime.utcnow() to return a fixed time

    This makes tests deterministic when testing time-sensitive code.

    Returns:
        datetime: Fixed datetime object

    Usage:
        def test_with_fixed_time(fixed_datetime):
            # datetime.utcnow() will always return fixed_datetime
            from datetime import datetime
            assert datetime.utcnow() == fixed_datetime
    """
    fixed_time = datetime(2024, 1, 15, 12, 0, 0)

    # Mock datetime.utcnow()
    mocker.patch('datetime.datetime', wraps=datetime)
    mocker.patch('datetime.datetime.utcnow', return_value=fixed_time)

    return fixed_time


# ============================================================================
# Marker Definitions
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (fast, mocked dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (slower, real dependencies)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
