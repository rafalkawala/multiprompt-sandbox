"""
Integration test fixtures for API endpoint testing

These tests focus on testing complete API request/response flows
with mocked database, simulating real HTTP interactions.
"""
import pytest
import sys
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

# Set dummy environment variables BEFORE importing any modules
os.environ["SECRET_KEY"] = "test-secret-key-1234567890"
os.environ["ENVIRONMENT"] = "test"

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from models.user import User, UserRole
from models.project import Project, Dataset
from models.image import Image


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def admin_user():
    """Create an admin user for testing"""
    return User(
        id="11111111-1111-1111-1111-111111111111",
        email="admin@test.com",
        google_id="google-admin-123",
        name="Admin User",
        picture_url="https://example.com/admin.jpg",
        role=UserRole.ADMIN.value,
        is_active=True,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        last_login_at=datetime(2024, 1, 15, 10, 0, 0)
    )


@pytest.fixture
def viewer_user():
    """Create a viewer user for testing"""
    return User(
        id="33333333-3333-3333-3333-333333333333",
        email="viewer@test.com",
        google_id="google-viewer-789",
        name="Viewer User",
        picture_url=None,
        role=UserRole.VIEWER.value,
        is_active=True,
        created_at=datetime(2024, 1, 10, 10, 0, 0),
        last_login_at=datetime(2024, 1, 15, 8, 0, 0)
    )


@pytest.fixture
def test_project(admin_user):
    """Create a test project"""
    project = Project(
        id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        name="Integration Test Project",
        description="A project for integration testing",
        question_text="Is this test passing?",
        question_type="binary",
        created_by_id=admin_user.id,
        created_at=datetime(2024, 1, 5, 10, 0, 0),
        updated_at=datetime(2024, 1, 10, 15, 0, 0)
    )
    project.datasets = []
    project.created_by = admin_user  # Add relationship for serialization
    return project


@pytest.fixture
def test_dataset(test_project, admin_user):
    """Create a test dataset"""
    dataset = Dataset(
        id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        name="Integration Test Dataset",
        project_id=test_project.id,
        created_by_id=admin_user.id,
        created_at=datetime(2024, 1, 6, 10, 0, 0),
        processing_status="ready",
        total_files=0,
        processed_files=0,
        failed_files=0
    )
    dataset.images = []
    return dataset


# ============================================================================
# Mock Database Fixture
# ============================================================================

@pytest.fixture
def mock_db_session(mocker):
    """Create a mocked database session"""
    mock_session = mocker.Mock(spec=Session)
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.query.return_value.filter.return_value.all.return_value = []
    mock_session.query.return_value.get.return_value = None
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    mock_session.close.return_value = None
    mock_session.add.return_value = None
    mock_session.delete.return_value = None
    mock_session.refresh.return_value = None
    return mock_session


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
def integration_client(mock_db_session, admin_user):
    """
    Create a FastAPI TestClient for integration testing

    This client tests complete API request/response flows.
    """
    from main import app
    from api.v1.auth import get_db as auth_get_db, get_current_user as auth_get_current_user
    from api.deps import get_db as deps_get_db, get_current_user as deps_get_current_user, require_write_access

    def override_get_db():
        return mock_db_session

    app.dependency_overrides[auth_get_db] = override_get_db
    app.dependency_overrides[deps_get_db] = override_get_db
    app.dependency_overrides[auth_get_current_user] = lambda: admin_user
    app.dependency_overrides[deps_get_current_user] = lambda: admin_user
    app.dependency_overrides[require_write_access] = lambda: admin_user

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


@pytest.fixture
def viewer_client(mock_db_session, viewer_user):
    """
    Create a FastAPI TestClient authenticated as a viewer

    Viewers should have read-only access.
    """
    from main import app
    from api.v1.auth import get_db as auth_get_db, get_current_user as auth_get_current_user
    from api.deps import get_db as deps_get_db, get_current_user as deps_get_current_user

    def override_get_db():
        return mock_db_session

    app.dependency_overrides[auth_get_db] = override_get_db
    app.dependency_overrides[deps_get_db] = override_get_db
    app.dependency_overrides[auth_get_current_user] = lambda: viewer_user
    app.dependency_overrides[deps_get_current_user] = lambda: viewer_user

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(mock_db_session):
    """
    Create a FastAPI TestClient without authentication

    Use for testing authentication requirements.
    """
    from main import app
    from api.v1.auth import get_db as auth_get_db
    from api.deps import get_db as deps_get_db

    def override_get_db():
        return mock_db_session

    app.dependency_overrides[auth_get_db] = override_get_db
    app.dependency_overrides[deps_get_db] = override_get_db

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()
