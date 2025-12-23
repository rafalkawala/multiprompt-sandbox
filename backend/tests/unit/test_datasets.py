"""
Tests for Dataset CRUD API endpoints
Located at: backend/api/v1/datasets.py

These tests cover dataset creation, listing, and deletion.
All database operations are mocked.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from fastapi.testclient import TestClient

from models.project import Project, Dataset
from models.user import User, UserRole


class TestCreateDataset:
    """Test dataset creation endpoint"""

    def test_create_dataset_success(self, authenticated_client, mock_db_session, sample_project):
        """
        Test successful dataset creation

        Expected: Dataset created with 201 status and correct response
        """
        # Arrange - Mock project lookup to return our sample project
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_project

        # Mock dataset creation - refresh sets the created_at
        created_dataset = None

        def capture_add(dataset):
            nonlocal created_dataset
            created_dataset = dataset
            # Set ID and created_at that would normally be set by the DB
            dataset.id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
            dataset.created_at = datetime(2024, 1, 15, 10, 0, 0)

        mock_db_session.add.side_effect = capture_add
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        # Act
        response = authenticated_client.post(
            f"/api/v1/projects/{sample_project.id}/datasets",
            json={"name": "Test Dataset"}
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Dataset"
        assert data["project_id"] == str(sample_project.id)
        assert data["image_count"] == 0

    def test_create_dataset_project_not_found(self, authenticated_client, mock_db_session):
        """
        Test dataset creation when project doesn't exist

        Expected: 404 error with "Project not found" message
        """
        # Arrange - Mock project lookup to return None
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act - Use valid UUID format
        response = authenticated_client.post(
            "/api/v1/projects/cccccccc-cccc-cccc-cccc-cccccccccccc/datasets",
            json={"name": "Test Dataset"}
        )

        # Assert
        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]


class TestListDatasets:
    """Test dataset listing endpoint"""

    def test_list_datasets_success(self, authenticated_client, mock_db_session, sample_project):
        """
        Test successful dataset listing

        Expected: Returns list of datasets for the project
        """
        # Arrange - Create a real Dataset instance (not a Mock)
        from models.project import Dataset
        test_dataset = Dataset(
            id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            name="Test Dataset",
            project_id=sample_project.id,
            created_by_id="11111111-1111-1111-1111-111111111111"
        )
        test_dataset.created_at = datetime(2024, 1, 15, 10, 0, 0)
        test_dataset.images = []
        test_dataset.processing_status = "ready"
        test_dataset.total_files = 0
        test_dataset.processed_files = 0
        test_dataset.failed_files = 0
        test_dataset.processing_started_at = None
        test_dataset.processing_completed_at = None

        # Add dataset to project
        sample_project.datasets = [test_dataset]

        # Mock project lookup
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_project

        # Act
        response = authenticated_client.get(f"/api/v1/projects/{sample_project.id}/datasets")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Dataset"

    def test_list_datasets_empty(self, authenticated_client, mock_db_session, sample_project):
        """
        Test listing datasets when project has none

        Expected: Returns empty list
        """
        # Arrange - Project with no datasets
        sample_project.datasets = []
        mock_db_session.query.return_value.filter.return_value.first.return_value = sample_project

        # Act
        response = authenticated_client.get(f"/api/v1/projects/{sample_project.id}/datasets")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_list_datasets_project_not_found(self, authenticated_client, mock_db_session):
        """
        Test listing datasets when project doesn't exist

        Expected: 404 error with "Project not found" message
        """
        # Arrange
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act - Use valid UUID format
        response = authenticated_client.get("/api/v1/projects/cccccccc-cccc-cccc-cccc-cccccccccccc/datasets")

        # Assert
        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]


class TestDeleteDataset:
    """Test dataset deletion endpoint"""

    def test_delete_dataset_success(self, authenticated_client, mock_db_session, sample_project):
        """
        Test successful dataset deletion

        Expected: Dataset deleted with success message
        """
        # Arrange - Create mock dataset
        mock_dataset = Mock(spec=Dataset)
        mock_dataset.id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        mock_dataset.name = "Test Dataset"
        mock_dataset.project_id = sample_project.id
        mock_dataset.images = []

        # Configure mock to return dataset for first query, project for second
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            mock_dataset,  # First call: dataset lookup
            sample_project  # Second call: project lookup
        ]

        # Act
        with patch('api.v1.datasets.get_storage_provider') as mock_storage:
            mock_storage.return_value = AsyncMock()
            response = authenticated_client.delete(
                f"/api/v1/projects/{sample_project.id}/datasets/{mock_dataset.id}"
            )

        # Assert
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        mock_db_session.delete.assert_called_once_with(mock_dataset)
        mock_db_session.commit.assert_called_once()

    def test_delete_dataset_not_found(self, authenticated_client, mock_db_session):
        """
        Test deletion when dataset doesn't exist

        Expected: 404 error with "Dataset not found" message
        """
        # Arrange
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act - Use valid UUIDs
        response = authenticated_client.delete(
            "/api/v1/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/datasets/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        )

        # Assert
        assert response.status_code == 404
        assert "Dataset not found" in response.json()["detail"]

    def test_delete_dataset_project_not_found(self, authenticated_client, mock_db_session, sample_project):
        """
        Test deletion when project doesn't exist

        Expected: 404 error with "Project not found" message
        """
        # Arrange - Create mock dataset but no project
        mock_dataset = Mock(spec=Dataset)
        mock_dataset.id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        mock_dataset.name = "Test Dataset"
        mock_dataset.project_id = sample_project.id
        mock_dataset.images = []

        # First query returns dataset, second returns None (project not found)
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            mock_dataset,  # Dataset found
            None  # Project not found
        ]

        # Act
        response = authenticated_client.delete(
            f"/api/v1/projects/{sample_project.id}/datasets/{mock_dataset.id}"
        )

        # Assert
        assert response.status_code == 404
        assert "Project not found" in response.json()["detail"]


class TestDatasetAuthentication:
    """Test dataset endpoint authentication requirements"""

    def test_create_dataset_unauthenticated(self, client):
        """
        Test that unauthenticated users cannot create datasets

        Expected: 401 Unauthorized
        """
        response = client.post(
            "/api/v1/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/datasets",
            json={"name": "Test Dataset"}
        )
        assert response.status_code == 401

    def test_list_datasets_unauthenticated(self, client):
        """
        Test that unauthenticated users cannot list datasets

        Expected: 401 Unauthorized
        """
        response = client.get("/api/v1/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/datasets")
        assert response.status_code == 401

    def test_delete_dataset_unauthenticated(self, client):
        """
        Test that unauthenticated users cannot delete datasets

        Expected: 401 Unauthorized
        """
        response = client.delete("/api/v1/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/datasets/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        assert response.status_code == 401


# ============================================================================
# TODO: Add more dataset tests (Priority: HIGH)
# ============================================================================
#
# Add these tests to increase coverage:
#
# 1. test_create_dataset_viewer_forbidden()
#    - Viewers should get 403 when trying to create datasets
#
# 2. test_delete_dataset_viewer_forbidden()
#    - Viewers should get 403 when trying to delete datasets
#
# 3. test_delete_dataset_with_images()
#    - Test that images are also deleted when dataset is deleted
#
# 4. test_create_dataset_duplicate_name()
#    - Test behavior when creating dataset with same name
#
# See TESTING_GUIDE.md for examples and patterns to follow.
# ============================================================================
