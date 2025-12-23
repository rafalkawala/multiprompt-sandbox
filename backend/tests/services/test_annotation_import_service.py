import pytest
from unittest.mock import MagicMock
import pandas as pd
from backend.services.annotation_import_service import AnnotationImportService
# Remove the real model import to mock it completely and avoid DB conflicts
# from backend.models.import_job import AnnotationImportJob

# Create mock classes instead of importing real models to avoid SQLAlchemy Metadata conflicts
class MockProject:
    def __init__(self):
        self.question_type = 'binary'
        self.question_options = []

class MockDataset:
    def __init__(self):
        self.id = 'dataset-123'
        self.name = 'Test Dataset'

class MockImage:
    def __init__(self):
        self.id = 'img-1'
        self.filename = 'test.jpg'
        self.annotation = None
        self.dataset_id = 'dataset-123'

class MockAnnotation:
    def __init__(self):
        self.id = 'ann-1'
        self.image_id = 'img-1'
        self.answer_value = None
        self.annotator_id = None

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_project():
    return MockProject()

@pytest.fixture
def mock_dataset():
    return MockDataset()

def test_normalize_binary_valid(mock_db, mock_project, mock_dataset):
    service = AnnotationImportService(mock_project, mock_dataset, mock_db)

    assert service.normalize_binary('yes') is True
    assert service.normalize_binary('Y') is True
    assert service.normalize_binary('True') is True
    assert service.normalize_binary('1') is True

    assert service.normalize_binary('no') is False
    assert service.normalize_binary('N') is False
    assert service.normalize_binary('False') is False
    assert service.normalize_binary('0') is False

    assert service.normalize_binary(None) is None
    assert service.normalize_binary('') is None

def test_normalize_binary_invalid(mock_db, mock_project, mock_dataset):
    service = AnnotationImportService(mock_project, mock_dataset, mock_db)

    with pytest.raises(ValueError):
        service.normalize_binary('maybe')

def test_validate_value_multiple_choice(mock_db, mock_project, mock_dataset):
    mock_project.question_type = 'multiple_choice'
    mock_project.question_options = ['Option A', 'Option B']
    service = AnnotationImportService(mock_project, mock_dataset, mock_db)

    assert service.validate_value('Option A', 'multiple_choice', ['Option A', 'Option B']) == 'Option A'
    assert service.validate_value('option a', 'multiple_choice', ['Option A', 'Option B']) == 'Option A'

    with pytest.raises(ValueError):
        service.validate_value('Option C', 'multiple_choice', ['Option A', 'Option B'])

def test_process_chunk_success(mock_db, mock_project, mock_dataset):
    service = AnnotationImportService(mock_project, mock_dataset, mock_db)

    # Mock DB query for images
    mock_image = MockImage()

    # Setup query return
    query_mock = mock_db.query.return_value
    options_mock = query_mock.options.return_value
    filter_mock = options_mock.filter.return_value
    filter_mock.all.return_value = [mock_image]

    # Create DataFrame
    df = pd.DataFrame([
        {'image_filename': 'test.jpg', 'annotation_value': 'yes'}
    ])

    # Run
    stats = service.process_chunk(df, 0, 'user-1')

    assert stats['created'] == 1
    assert stats['updated'] == 0
    assert len(stats['errors']) == 0
    assert mock_db.add.called

def test_process_chunk_image_not_found(mock_db, mock_project, mock_dataset):
    service = AnnotationImportService(mock_project, mock_dataset, mock_db)

    # Mock DB returns empty
    query_mock = mock_db.query.return_value
    options_mock = query_mock.options.return_value
    filter_mock = options_mock.filter.return_value
    filter_mock.all.return_value = []

    df = pd.DataFrame([
        {'image_filename': 'missing.jpg', 'annotation_value': 'yes'}
    ])

    stats = service.process_chunk(df, 0, 'user-1')

    assert stats['created'] == 0
    assert len(stats['errors']) == 1
    assert "Image not found" in stats['errors'][0]['error']
