import pytest
from services.cost_estimation_service import CostEstimationService

@pytest.fixture
def cost_service():
    return CostEstimationService()

def test_count_tokens_openai(cost_service):
    text = "Hello world"
    # OpenAI tiktoken should return small number
    tokens = cost_service.count_tokens(text, "openai", "gpt-4")
    assert tokens > 0 and tokens < 10

def test_count_tokens_heuristic(cost_service):
    text = "12345678" # 8 chars
    # Heuristic: 8/4 = 2
    tokens = cost_service.count_tokens(text, "gemini", "gemini-pro")
    assert tokens == 2

def test_calculate_actual_cost(cost_service):
    pricing = {
        "input_price_per_1m": 10.0,
        "output_price_per_1m": 30.0,
        "discount_percent": 0
    }
    usage = {
        "prompt_tokens": 1000000,
        "completion_tokens": 1000000
    }
    # 1M input * $10 + 1M output * $30 = $40
    cost = cost_service.calculate_actual_cost(usage, pricing)
    assert cost == 40.0

def test_calculate_actual_cost_with_discount(cost_service):
    pricing = {
        "input_price_per_1m": 10.0,
        "output_price_per_1m": 30.0,
        "discount_percent": 50 # 50% discount
    }
    usage = {
        "prompt_tokens": 1000000,
        "completion_tokens": 1000000
    }
    # $40 * 0.5 = $20
    cost = cost_service.calculate_actual_cost(usage, pricing)
    assert cost == 20.0
