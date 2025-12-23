"""
Integration tests for Dataset API endpoints

These tests verify complete API request/response flows for dataset CRUD operations.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock

from models.project import Project, Dataset
from models.image import Image


class TestDatasetCreation:
    """Test dataset creation API endpoints"""

    def test_create_dataset_returns_201(self, integration_client, mock_db_session, test_project, admin_user):
        """
        Test that creating a dataset returns 201 Created

        Expected: 201 status with dataset data in response
        """
        # Arrange
        mock_db_session.query.return_value.filter.return_value.first.return_value = test_project

        def capture_add(dataset):
            dataset.id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
            dataset.created_at = datetime(2024, 1, 15, 10, 0, 0)

        mock_db_session.add.side_effect = capture_add

        # Act
        response = integration_client.post(
            f"/api/v1/projects/{test_project.id}/datasets",
            json={"name": "New Dataset"}
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Dataset"
        assert data["project_id"] == str(test_project.id)

    def test_create_dataset_project_not_found(self, integration_client, mock_db_session):
        """
        Test that creating dataset for non-existent project returns 404

        Expected: 404 Not Found
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = integration_client.post(
            "/api/v1/projects/ffffffff-ffff-ffff-ffff-ffffffffffff/datasets",
            json={"name": "New Dataset"}
        )

        assert response.status_code == 404

    def test_create_dataset_requires_name(self, integration_client, mock_db_session, test_project):
        """
        Test that name is required

        Expected: 422 Validation Error
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = test_project

        response = integration_client.post(
            f"/api/v1/projects/{test_project.id}/datasets",
            json={}
        )

        assert response.status_code == 422


class TestDatasetListing:
    """Test dataset listing API endpoints"""

    def test_list_datasets_returns_200(self, integration_client, mock_db_session, test_project, test_dataset):
        """
        Test that listing datasets returns 200 OK

        Expected: 200 status with list of datasets
        """
        test_project.datasets = [test_dataset]
        mock_db_session.query.return_value.filter.return_value.first.return_value = test_project

        response = integration_client.get(f"/api/v1/projects/{test_project.id}/datasets")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == test_dataset.name

    def test_list_datasets_returns_empty_list(self, integration_client, mock_db_session, test_project):
        """
        Test that empty dataset list returns empty array

        Expected: 200 status with empty array
        """
        test_project.datasets = []
        mock_db_session.query.return_value.filter.return_value.first.return_value = test_project

        response = integration_client.get(f"/api/v1/projects/{test_project.id}/datasets")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_datasets_project_not_found(self, integration_client, mock_db_session):
        """
        Test that listing datasets for non-existent project returns 404

        Expected: 404 Not Found
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = integration_client.get("/api/v1/projects/ffffffff-ffff-ffff-ffff-ffffffffffff/datasets")

        assert response.status_code == 404


class TestDatasetProcessingStatusEndpoint:
    """Test dataset processing status endpoint"""

    def test_get_processing_status_returns_200(self, integration_client, mock_db_session, test_project, test_dataset):
        """
        Test that getting processing status returns 200 OK

        Expected: 200 status with processing status data
        """
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            test_dataset,  # First call: dataset lookup
            test_project   # Second call: project lookup
        ]

        response = integration_client.get(
            f"/api/v1/projects/{test_project.id}/datasets/{test_dataset.id}/processing-status"
        )

        assert response.status_code == 200
        data = response.json()
        assert "processing_status" in data

    def test_get_processing_status_not_found(self, integration_client, mock_db_session):
        """
        Test that non-existent dataset returns 404

        Expected: 404 Not Found
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = integration_client.get(
            "/api/v1/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/datasets/ffffffff-ffff-ffff-ffff-ffffffffffff/processing-status"
        )

        assert response.status_code == 404


class TestDatasetDeletion:
    """Test dataset deletion endpoints"""

    def test_delete_dataset_returns_200(self, integration_client, mock_db_session, test_project, test_dataset):
        """
        Test that deleting a dataset returns 200 OK

        Expected: 200 status with success message
        """
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            test_dataset,  # First call: dataset lookup
            test_project   # Second call: project lookup
        ]

        with patch('api.v1.datasets.get_storage_provider') as mock_storage:
            mock_storage.return_value = AsyncMock()
            response = integration_client.delete(
                f"/api/v1/projects/{test_project.id}/datasets/{test_dataset.id}"
            )

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_delete_dataset_not_found(self, integration_client, mock_db_session):
        """
        Test that deleting non-existent dataset returns 404

        Expected: 404 Not Found
        """
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        response = integration_client.delete(
            "/api/v1/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/datasets/ffffffff-ffff-ffff-ffff-ffffffffffff"
        )

        assert response.status_code == 404


class TestDatasetAuthentication:
    """Test dataset endpoint authentication"""

    def test_list_datasets_requires_auth(self, unauthenticated_client):
        """
        Test that listing datasets requires authentication

        Expected: 401 Unauthorized
        """
        response = unauthenticated_client.get(
            "/api/v1/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/datasets"
        )

        assert response.status_code == 401

    def test_create_dataset_requires_auth(self, unauthenticated_client):
        """
        Test that creating datasets requires authentication

        Expected: 401 Unauthorized
        """
        response = unauthenticated_client.post(
            "/api/v1/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/datasets",
            json={"name": "Test Dataset"}
        )

        assert response.status_code == 401

    def test_delete_dataset_requires_auth(self, unauthenticated_client):
        """
        Test that deleting datasets requires authentication

        Expected: 401 Unauthorized
        """
        response = unauthenticated_client.delete(
            "/api/v1/projects/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/datasets/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        )

        assert response.status_code == 401


class TestDatasetPermissions:
    """Test dataset access permissions"""

    def test_viewer_can_list_datasets(self, viewer_client, mock_db_session, test_project, test_dataset):
        """
        Test that viewers can list datasets

        Expected: 200 OK
        """
        test_project.datasets = [test_dataset]
        mock_db_session.query.return_value.filter.return_value.first.return_value = test_project

        response = viewer_client.get(f"/api/v1/projects/{test_project.id}/datasets")

        assert response.status_code == 200

    def test_viewer_can_get_processing_status(self, viewer_client, mock_db_session, test_project, test_dataset):
        """
        Test that viewers can get processing status

        Expected: 200 OK
        """
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            test_dataset,
            test_project
        ]

        response = viewer_client.get(
            f"/api/v1/projects/{test_project.id}/datasets/{test_dataset.id}/processing-status"
        )

        assert response.status_code == 200
