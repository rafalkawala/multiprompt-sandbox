import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from services.evaluation_service import EvaluationService
from models.evaluation import Evaluation
from models.project import Project
from models.project import Dataset
from models.evaluation import ModelConfig

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def evaluation_service(mock_db):
    return EvaluationService(mock_db)

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = "user1"
    return user

def test_list_evaluations(evaluation_service, mock_db, mock_user):
    # Chain: query(Eval) -> filter(user) -> filter(proj) -> order_by -> all()
    mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [Evaluation(name="Test Eval")]
    evals = evaluation_service.list_evaluations("proj1", mock_user)
    assert len(evals) == 1
    assert evals[0].name == "Test Eval"

def test_get_evaluation_not_found(evaluation_service, mock_db, mock_user):
    # Chain: query(Eval) -> filter(id) -> filter(user) -> first()
    # Mocking: query().filter().filter().first()
    # Note: SQLAlchemy filters are chained. mock.filter().filter() is what we need.
    query_mock = mock_db.query.return_value
    filter1_mock = query_mock.filter.return_value
    filter2_mock = filter1_mock.filter.return_value
    filter2_mock.first.return_value = None

    with pytest.raises(HTTPException) as exc:
        evaluation_service.get_evaluation("eval1", mock_user)
    assert exc.value.status_code == 404

def test_delete_evaluation_success(evaluation_service, mock_db, mock_user):
    mock_eval = Evaluation(id="eval1", created_by_id="user1")
    # Chain: query(Eval) -> filter(id) -> filter(user) -> first()
    query_mock = mock_db.query.return_value
    filter1_mock = query_mock.filter.return_value
    filter2_mock = filter1_mock.filter.return_value
    filter2_mock.first.return_value = mock_eval

    msg = evaluation_service.delete_evaluation("eval1", mock_user)

    assert msg == "Evaluation deleted"
    mock_db.delete.assert_called_once_with(mock_eval)
    mock_db.commit.assert_called_once()

@patch('threading.Thread')
def test_create_evaluation(mock_thread, evaluation_service, mock_db, mock_user):
    # Setup dependencies
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        Project(id="p1"), # Project found
        Dataset(id="d1"), # Dataset found
        ModelConfig(id="m1") # Model Config found
    ]

    class MockData:
        name = "New Eval"
        project_id = "p1"
        dataset_id = "d1"
        model_config_id = "m1"
        system_message = "sys"
        question_text = "q"
        prompt_chain = None
        selection_config = None

    eval_obj = evaluation_service.create_evaluation(MockData(), mock_user)

    assert eval_obj.name == "New Eval"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_thread.return_value.start.assert_called_once()
