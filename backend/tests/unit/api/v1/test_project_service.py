import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from services.project_service import ProjectService
from models.project import Project

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def project_service(mock_db):
    return ProjectService(mock_db)

def test_list_projects(project_service, mock_db):
    mock_db.query.return_value.order_by.return_value.all.return_value = [Project(name="Test Project")]
    projects = project_service.list_projects()
    assert len(projects) == 1
    assert projects[0].name == "Test Project"

def test_get_project_found(project_service, mock_db):
    mock_project = Project(id="123", name="Test Project")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_project

    project = project_service.get_project("123")
    assert project.id == "123"
    assert project.name == "Test Project"

def test_get_project_not_found(project_service, mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        project_service.get_project("123")
    assert exc_info.value.status_code == 404

def test_create_project_invalid_type(project_service, mock_user):
    class MockProjectData:
        name = "Test"
        description = "Desc"
        question_text = "Q"
        question_type = "invalid"
        question_options = []

    with pytest.raises(HTTPException) as exc_info:
        project_service.create_project(MockProjectData(), mock_user)
    assert exc_info.value.status_code == 400

def test_delete_project_success(project_service, mock_db, mock_user):
    mock_project = Project(id="123", name="Test Project", created_by_id="user1")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_project

    name = project_service.delete_project("123", mock_user)

    assert name == "Test Project"
    mock_db.delete.assert_called_once_with(mock_project)
    mock_db.commit.assert_called_once()

def test_delete_project_not_owner(project_service, mock_db, mock_user):
    mock_project = Project(id="123", name="Test Project", created_by_id="other_user")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_project

    with pytest.raises(HTTPException) as exc_info:
        project_service.delete_project("123", mock_user)
    assert exc_info.value.status_code == 403
    mock_db.delete.assert_not_called()

def test_update_project_success(project_service, mock_db, mock_user):
    mock_project = Project(id="123", name="Old Name", created_by_id="user1")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_project

    class MockUpdateData:
        name = "New Name"
        description = None
        question_text = None
        question_type = None
        question_options = None

    updated = project_service.update_project("123", MockUpdateData(), mock_user)

    assert updated.name == "New Name"
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_project)

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = "user1"
    user.email = "test@example.com"
    return user
