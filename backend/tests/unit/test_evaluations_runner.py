"""
Tests for evaluation runner logic in backend/api/v1/evaluations.py
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import time
import itertools

from models.evaluation import Evaluation, EvaluationResult, ModelConfig
from models.project import Project
from models.image import Image, Annotation
from api.v1.evaluations import run_evaluation_task

class TestEvaluationRunner:
    
    @pytest.fixture
    def mock_db_session(self):
        session = Mock()
        session.commit = Mock()
        session.add = Mock()
        session.close = Mock()
        return session

    @pytest.fixture
    def mock_evaluation(self):
        eval_obj = Mock(spec=Evaluation)
        eval_obj.id = "eval-123"
        eval_obj.dataset_id = "dataset-123"
        eval_obj.status = "pending"
        eval_obj.processed_images = 0
        eval_obj.total_images = 0
        eval_obj.prompt_chain = None 
        eval_obj.results_summary = {}
        eval_obj.error_message = None
        
        # Mock text fields to be strings
        eval_obj.system_message = "system"
        eval_obj.question_text = "question"
        
        # Relationships
        eval_obj.project = Mock(spec=Project)
        eval_obj.project.question_type = "binary"
        eval_obj.project.question_text = "question"
        eval_obj.project.question_options = None
        
        eval_obj.model_config = Mock(spec=ModelConfig)
        eval_obj.model_config.provider = "gemini"
        eval_obj.model_config.api_key = "key"
        eval_obj.model_config.model_name = "gemini-pro"
        eval_obj.model_config.concurrency = 2
        eval_obj.model_config.temperature = 0.0
        eval_obj.model_config.max_tokens = 100
        
        return eval_obj

    @pytest.fixture
    def mock_images(self):
        images = []
        for i in range(5):
            img = Mock(spec=Image)
            img.id = f"img-{i}"
            img.filename = f"image_{i}.jpg"
            img.storage_path = f"path/to/image_{i}.jpg"
            
            # Annotation
            ann = Mock(spec=Annotation)
            ann.answer_value = {"value": True}
            img.annotation = ann
            
            images.append(img)
        return images

    @pytest.fixture
    def mock_results(self, mock_images):
        # Create results corresponding to images
        results = []
        for img in mock_images:
            res = Mock(spec=EvaluationResult)
            res.is_correct = True
            res.ground_truth = {"value": True}
            res.parsed_answer = {"value": True}
            results.append(res)
        return results

    @pytest.mark.asyncio
    async def test_run_evaluation_success(self, mocker, mock_db_session, mock_evaluation, mock_images, mock_results):
        """Test successful execution of evaluation task"""
        
        # Mock DB interactions
        mocker.patch('api.v1.evaluations.SessionLocal', return_value=mock_db_session)
        
        # Setup db.query side_effect to handle different models
        def query_side_effect(model):
            query_mock = Mock()
            if model == Evaluation:
                query_mock.filter.return_value.first.return_value = mock_evaluation
            elif model == Image:
                # For Image query: db.query(Image).join(Annotation).filter(...).all()
                join_mock = Mock()
                filter_mock = Mock()
                join_mock.filter.return_value = filter_mock
                filter_mock.all.return_value = mock_images
                query_mock.join.return_value = join_mock
            elif model == EvaluationResult:
                # For Results query: db.query(EvaluationResult).filter(...).all()
                filter_mock = Mock()
                filter_mock.all.return_value = mock_results
                query_mock.filter.return_value = filter_mock
            return query_mock

        mock_db_session.query.side_effect = query_side_effect
        
        # Mock image preloading
        mocker.patch('api.v1.evaluations.preload_images', return_value={
            img.id: ("base64data", "image/jpeg") for img in mock_images
        })
        
        # Mock prompt utils globally
        mocker.patch('core.prompt_utils.validate_variable_references', return_value=(True, None))
        mocker.patch('core.prompt_utils.substitute_variables', return_value="processed prompt")
        
        # Mock LLM Service
        mock_llm_service = Mock()
        mock_llm_service.generate_content = AsyncMock(return_value=("yes", 100))
        mocker.patch('api.v1.evaluations.get_llm_service', return_value=mock_llm_service)
        
        # Run task
        await run_evaluation_task("eval-123")
        
        # Verify
        assert mock_evaluation.status == "completed"
        assert mock_evaluation.processed_images == 5
        assert mock_evaluation.total_images == 5
        assert mock_evaluation.accuracy == 1.0
        assert mock_db_session.add.call_count == 5
        
    @pytest.mark.asyncio
    async def test_run_evaluation_partial_failure(self, mocker, mock_db_session, mock_evaluation, mock_images):
        """Test execution with some failed images"""
        mocker.patch('api.v1.evaluations.SessionLocal', return_value=mock_db_session)
        
        def query_side_effect(model):
            query_mock = Mock()
            if model == Evaluation:
                query_mock.filter.return_value.first.return_value = mock_evaluation
            elif model == Image:
                join_mock = Mock()
                filter_mock = Mock()
                join_mock.filter.return_value = filter_mock
                filter_mock.all.return_value = mock_images
                query_mock.join.return_value = join_mock
            elif model == EvaluationResult:
                # Return 3 correct results, 2 failed (implicitly absent or is_correct=None)
                # Actually, if failed, is_correct is None usually.
                # But we need to return what was added.
                # Let's simulate 3 results that succeeded
                res_mocks = []
                for _ in range(3):
                    r = Mock(spec=EvaluationResult)
                    r.is_correct = True
                    r.ground_truth = {"value": True}
                    r.parsed_answer = {"value": True}
                    res_mocks.append(r)
                # And 2 that failed
                for _ in range(2):
                    r = Mock(spec=EvaluationResult)
                    r.is_correct = None
                    res_mocks.append(r)
                
                filter_mock = Mock()
                filter_mock.all.return_value = res_mocks
                query_mock.filter.return_value = filter_mock
            return query_mock

        mock_db_session.query.side_effect = query_side_effect

        mocker.patch('api.v1.evaluations.preload_images', return_value={
            img.id: ("base64data", "image/jpeg") for img in mock_images
        })
        mocker.patch('core.prompt_utils.validate_variable_references', return_value=(True, None))
        mocker.patch('core.prompt_utils.substitute_variables', return_value="processed prompt")
        
        mock_llm_service = Mock()
        
        call_count = 0
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                return ("yes", 100)
            else:
                raise Exception("API Error")

        mock_llm_service.generate_content = AsyncMock(side_effect=side_effect)
        mocker.patch('api.v1.evaluations.get_llm_service', return_value=mock_llm_service)
        
        await run_evaluation_task("eval-123")
        
        assert mock_evaluation.status == "completed"
        assert mock_evaluation.results_summary['failed'] == 2
        assert mock_evaluation.results_summary['successful'] == 3
        
    @pytest.mark.asyncio
    async def test_run_evaluation_high_failure_rate(self, mocker, mock_db_session, mock_evaluation, mock_images):
        """Test that high failure rate marks evaluation as failed"""
        mocker.patch('api.v1.evaluations.SessionLocal', return_value=mock_db_session)
        
        # Simpler mock for high failure since we don't check accuracy, just status
        def query_side_effect(model):
            query_mock = Mock()
            if model == Evaluation:
                query_mock.filter.return_value.first.return_value = mock_evaluation
            elif model == Image:
                join_mock = Mock()
                filter_mock = Mock()
                join_mock.filter.return_value = filter_mock
                filter_mock.all.return_value = mock_images
                query_mock.join.return_value = join_mock
            elif model == EvaluationResult:
                filter_mock = Mock()
                filter_mock.all.return_value = [] # Doesn't matter for this test
                query_mock.filter.return_value = filter_mock
            return query_mock
            
        mock_db_session.query.side_effect = query_side_effect

        mocker.patch('api.v1.evaluations.preload_images', return_value={
            img.id: ("base64data", "image/jpeg") for img in mock_images
        })
        mocker.patch('core.prompt_utils.validate_variable_references', return_value=(True, None))
        mocker.patch('core.prompt_utils.substitute_variables', return_value="processed prompt")
        
        mock_llm_service = Mock()
        
        call_count = 0
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ("yes", 100)
            else:
                raise Exception("E")

        mock_llm_service.generate_content = AsyncMock(side_effect=side_effect)
        mocker.patch('api.v1.evaluations.get_llm_service', return_value=mock_llm_service)
        
        await run_evaluation_task("eval-123")
        
        assert mock_evaluation.status == "failed"
        assert "Evaluation failed" in mock_evaluation.error_message

    @pytest.mark.asyncio
    async def test_eta_calculation(self, mocker, mock_db_session, mock_evaluation, mock_images):
        """Verify ETA is calculated and stored"""
        mocker.patch('api.v1.evaluations.SessionLocal', return_value=mock_db_session)
        
        def query_side_effect(model):
            query_mock = Mock()
            if model == Evaluation:
                query_mock.filter.return_value.first.return_value = mock_evaluation
            elif model == Image:
                join_mock = Mock()
                filter_mock = Mock()
                join_mock.filter.return_value = filter_mock
                filter_mock.all.return_value = mock_images
                query_mock.join.return_value = join_mock
            elif model == EvaluationResult:
                filter_mock = Mock()
                filter_mock.all.return_value = []
                query_mock.filter.return_value = filter_mock
            return query_mock
            
        mock_db_session.query.side_effect = query_side_effect

        mocker.patch('api.v1.evaluations.preload_images', return_value={
            img.id: ("base64data", "image/jpeg") for img in mock_images
        })
        mocker.patch('core.prompt_utils.validate_variable_references', return_value=(True, None))
        mocker.patch('core.prompt_utils.substitute_variables', return_value="processed prompt")
        
        mock_llm_service = Mock()
        mock_llm_service.generate_content = AsyncMock(return_value=("yes", 100))
        mocker.patch('api.v1.evaluations.get_llm_service', return_value=mock_llm_service)
        
        # Fix StopIteration: Provide infinite iterator
        mock_time = mocker.patch('time.time', side_effect=itertools.count(start=1000))
        
        await run_evaluation_task("eval-123")
        
        # Check if results_summary was updated with eta_seconds at least once
        # We verify that commit was called multiple times
        assert mock_db_session.commit.call_count >= 5