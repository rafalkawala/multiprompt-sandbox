"""
Integration tests for Project API endpoints

These tests verify complete API request/response flows for project CRUD operations.
"""
import pytest
from datetime import datetime
from unittest.mock import patch

from models.project import Project


class TestProjectCreation:
    """Test project creation API endpoints"""

    def test_create_project_returns_201(self, integration_client, mock_db_session, admin_user):
        """
        Test that creating a project returns 201 Created

        Expected: 201 status with project data in response
        """
        # Arrange - Mock the add to capture the project
        created_project = None

        def capture_add(project):
            nonlocal created_project
            created_project = project
            project.id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            project.created_at = datetime(2024, 1, 15, 10, 0, 0)
            project.updated_at = datetime(2024, 1, 15, 10, 0, 0)

        mock_db_session.add.side_effect = capture_add

        # Act
        response = integration_client.post(
            "/api/v1/projects",
            json={
                "name": "New Project",
                "description": "Test description",
                "question_text": "Test question?",
                "question_type": "binary"
            }
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Project"
        assert data["description"] == "Test description"
        assert "id" in data

    def test_create_project_with_text_type(self, integration_client, mock_db_session, admin_user):
        """
        Test that project with text question_type is accepted

        Expected: 201 Created with text type
        """
        def capture_add(project):
            project.id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
            project.created_at = datetime(2024, 1, 15, 10, 0, 0)
            project.updated_at = datetime(2024, 1, 15, 10, 0, 0)

        mock_db_session.add.side_effect = capture_add

        response = integration_client.post(
            "/api/v1/projects",
            json={
                "name": "Text Project",
                "description": "Test",
                "question_text": "Test?",
                "question_type": "text"
            }
        )

        assert response.status_code == 201
        assert response.json()["question_type"] == "text"

    def test_create_project_requires_name(self, integration_client):
        """
        Test that name is required

        Expected: 422 Validation Error
        """
        response = integration_client.post(
            "/api/v1/projects",
            json={
                "description": "No name provided",
                "question_text": "Test?",
                "question_type": "binary"
            }
        )

        assert response.status_code == 422


class TestProjectListing:
    """Test project listing API endpoints"""

    def test_list_projects_returns_200(self, integration_client, mock_db_session, test_project):
        """
        Test that listing projects returns 200 OK

        Expected: 200 status with list of projects
        """
        # Arrange - list_projects uses order_by().all()
        mock_db_session.query.return_value.order_by.return_value.all.return_value = [test_project]

        # Act
        response = integration_client.get("/api/v1/projects")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == test_project.name

    def test_list_projects_returns_empty_list(self, integration_client, mock_db_session):
        """
        Test that empty project list returns empty array

        Expected: 200 status with empty array
        """
        mock_db_session.query.return_value.order_by.return_value.all.return_value = []

        response = integration_client.get("/api/v1/projects")

        assert response.status_code == 200
        assert response.json() == []


class TestProjectRetrieval:
    """Test single project retrieval"""

    def test_get_project_returns_200(self, integration_client, mock_db_session, test_project):
        """
        Test that getting a project returns 200 OK

        Expected: 200 status with project data
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = test_project

        response = integration_client.get(f"/api/v1/projects/{test_project.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_project.id)
        assert data["name"] == test_project.name

    def test_get_project_not_found(self, integration_client, mock_db_session):
        """
        Test that non-existent project returns 404

        Expected: 404 Not Found
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = integration_client.get("/api/v1/projects/ffffffff-ffff-ffff-ffff-ffffffffffff")

        assert response.status_code == 404

    def test_get_project_invalid_uuid(self, integration_client, mock_db_session):
        """
        Test that invalid UUID format returns 404

        Expected: 404 Not Found (invalid UUIDs are treated as not found)
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = integration_client.get("/api/v1/projects/not-a-uuid")

        # FastAPI/SQLAlchemy will handle invalid UUID as not found
        assert response.status_code == 404


class TestProjectUpdate:
    """Test project update endpoints"""

    def test_update_project_returns_200(self, integration_client, mock_db_session, test_project):
        """
        Test that updating a project returns 200 OK

        Expected: 200 status with updated project data
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = test_project

        response = integration_client.patch(
            f"/api/v1/projects/{test_project.id}",
            json={
                "name": "Updated Name"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    def test_update_project_not_found(self, integration_client, mock_db_session):
        """
        Test that updating non-existent project returns 404

        Expected: 404 Not Found
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = integration_client.patch(
            "/api/v1/projects/ffffffff-ffff-ffff-ffff-ffffffffffff",
            json={
                "name": "Updated"
            }
        )

        assert response.status_code == 404


class TestProjectDeletion:
    """Test project deletion endpoints"""

    def test_delete_project_returns_200(self, integration_client, mock_db_session, test_project):
        """
        Test that deleting a project returns 200 OK

        Expected: 200 status with success message
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = test_project

        response = integration_client.delete(f"/api/v1/projects/{test_project.id}")

        assert response.status_code == 200
        mock_db_session.delete.assert_called_once()

    def test_delete_project_not_found(self, integration_client, mock_db_session):
        """
        Test that deleting non-existent project returns 404

        Expected: 404 Not Found
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = integration_client.delete("/api/v1/projects/ffffffff-ffff-ffff-ffff-ffffffffffff")

        assert response.status_code == 404


class TestProjectAuthentication:
    """Test project endpoint authentication"""

    def test_list_projects_requires_auth(self, unauthenticated_client):
        """
        Test that listing projects requires authentication

        Expected: 401 Unauthorized
        """
        response = unauthenticated_client.get("/api/v1/projects")

        assert response.status_code == 401

    def test_create_project_requires_auth(self, unauthenticated_client):
        """
        Test that creating projects requires authentication

        Expected: 401 Unauthorized
        """
        response = unauthenticated_client.post(
            "/api/v1/projects",
            json={
                "name": "Test",
                "description": "Test",
                "question_text": "Test?",
                "question_type": "binary"
            }
        )

        assert response.status_code == 401


class TestProjectPermissions:
    """Test project access permissions"""

    def test_viewer_can_list_projects(self, viewer_client, mock_db_session, test_project):
        """
        Test that viewers can list projects

        Expected: 200 OK
        """
        mock_db_session.query.return_value.order_by.return_value.all.return_value = [test_project]

        response = viewer_client.get("/api/v1/projects")

        assert response.status_code == 200

    def test_viewer_can_get_project(self, viewer_client, mock_db_session, test_project):
        """
        Test that viewers can get a single project

        Expected: 200 OK
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = test_project

        response = viewer_client.get(f"/api/v1/projects/{test_project.id}")

        assert response.status_code == 200
