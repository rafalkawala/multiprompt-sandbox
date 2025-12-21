import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime

from services.annotation_import_service import AnnotationImportService
from models.project import Project, Dataset
from models.image import Image, Annotation
from models.import_job import AnnotationImportJob, ImportJobStatus

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_project():
    project = MagicMock(spec=Project)
    project.question_type = "binary"
    project.question_options = None
    return project

@pytest.fixture
def mock_dataset():
    dataset = MagicMock(spec=Dataset)
    dataset.id = "dataset-uuid"
    dataset.project_id = "project-uuid"
    return dataset

@pytest.fixture
def service(mock_project, mock_dataset, mock_db):
    return AnnotationImportService(mock_project, mock_dataset, mock_db)

def test_validate_value_binary(service):
    assert service.validate_value("yes", "binary") is True
    assert service.validate_value("no", "binary") is False
    assert service.validate_value("TRUE", "binary") is True
    assert service.validate_value("0", "binary") is False
    
    with pytest.raises(ValueError):
        service.validate_value("maybe", "binary")

def test_validate_value_multiple_choice(service):
    options = ["Cat", "Dog"]
    assert service.validate_value("Cat", "multiple_choice", options) == "Cat"
    assert service.validate_value("dog", "multiple_choice", options) == "Dog"  # case insensitive
    
    with pytest.raises(ValueError):
        service.validate_value("Bird", "multiple_choice", options)

def test_process_chunk_missing_columns(service):
    df = pd.DataFrame([{"wrong_col": "val"}])
    result = service.process_chunk(df, 1, "user-id")
    assert len(result['errors']) > 0
    assert "Missing columns" in result['errors'][0]['error']

def test_process_chunk_image_not_found(service, mock_db):
    # Setup mock image query to return empty
    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = []
    
    df = pd.DataFrame([{
        "image_filename": "missing.jpg",
        "annotation_value": "yes"
    }])
    
    result = service.process_chunk(df, 1, "user-id")
    
    assert len(result['errors']) == 1
    assert "Image not found" in result['errors'][0]['error']
    assert result['created'] == 0

def test_process_chunk_success_create(service, mock_db):
    # Setup mock image
    mock_image = MagicMock(spec=Image)
    mock_image.filename = "test.jpg"
    mock_image.id = "img-uuid"
    mock_image.annotation = None  # No existing annotation
    
    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [mock_image]
    
    df = pd.DataFrame([{
        "image_filename": "test.jpg",
        "annotation_value": "yes"
    }])
    
    result = service.process_chunk(df, 1, "user-id")
    
    assert result['created'] == 1
    assert result['updated'] == 0
    assert len(result['errors']) == 0
    # Verify DB add was called
    mock_db.add.assert_called_once()

def test_process_chunk_success_update(service, mock_db):
    # Setup mock image with annotation
    mock_annotation = MagicMock(spec=Annotation)
    mock_image = MagicMock(spec=Image)
    mock_image.filename = "test.jpg"
    mock_image.id = "img-uuid"
    mock_image.annotation = mock_annotation
    
    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [mock_image]
    
    df = pd.DataFrame([{
        "image_filename": "test.jpg",
        "annotation_value": "no"
    }])
    
    result = service.process_chunk(df, 1, "user-id")
    
    assert result['created'] == 0
    assert result['updated'] == 1
    assert len(result['errors']) == 0
    # Verify annotation was updated
    assert mock_annotation.answer_value == {'value': False}

