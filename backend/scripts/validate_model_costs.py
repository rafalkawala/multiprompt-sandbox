
import json
import os
import sys
import logging
from typing import Dict, Any

# Adjust path to include backend root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from infrastructure.llm.gemini import GeminiProvider
from infrastructure.llm.vertex import VertexAIProvider
from infrastructure.llm.openai import OpenAIProvider
from infrastructure.llm.anthropic import AnthropicProvider

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

PROVIDERS = {
    "gemini": GeminiProvider(),
    "vertex": VertexAIProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider()
}

def validate_model_costs(config_path: str):
    """
    Validates cost calculation for all models in the configuration file.
    """
    print("\n=== Validating Model Cost Configurations ===\n")

    if not os.path.exists(config_path):
        print(f"[ERROR] Config file not found: {config_path}")
        return

    with open(config_path, 'r') as f:
        try:
            models = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in config file: {e}")
            return

    print(f"Found {len(models)} models in configuration.\n")
    print(f"{'Model ID':<35} | {'Provider':<10} | {'Est. Cost (Text)':<15} | {'Status'}")
    print("-" * 80)

    # Test Data
    input_text = "This is a test prompt with roughly 50 tokens." * 5 # ~250 chars -> ~60 tokens
    output_est_text = "This is a predicted response." * 5 # ~60 tokens
    images = [] # No images for basic text test

    # Mock token counts for calculation verification (Providers use internal logic, but we pass raw text)
    # Gemini/Vertex: chars / 4
    # OpenAI/Anthropic: usually approximation or library calls.
    # Here we just want to ensure the estimate_cost function runs and returns a non-negative float.

    failed_count = 0

    for model in models:
        model_id = model.get("id", "UNKNOWN")
        provider_name = model.get("provider", "unknown")
        pricing_config = model.get("pricing_config")

        if not pricing_config:
            print(f"{model_id:<35} | {provider_name:<10} | {'N/A':<15} | [WARN] No pricing config")
            continue

        provider = PROVIDERS.get(provider_name)
        if not provider:
            print(f"{model_id:<35} | {provider_name:<10} | {'N/A':<15} | [FAIL] Unknown provider")
            failed_count += 1
            continue

        try:
            # Calculate Cost
            cost = provider.estimate_cost(
                input_text=input_text,
                output_est_text=output_est_text,
                images=images,
                pricing_config=pricing_config
            )

            # Formatting
            cost_str = f"${cost:.6f}"

            # Simple validation: Cost should be >= 0
            if cost < 0:
                status = "[FAIL] Negative Cost"
                failed_count += 1
            else:
                status = "[PASS]"

            print(f"{model_id:<35} | {provider_name:<10} | {cost_str:<15} | {status}")

        except Exception as e:
            print(f"{model_id:<35} | {provider_name:<10} | {'ERROR':<15} | [FAIL] {str(e)}")
            failed_count += 1

    print("-" * 80)
    if failed_count == 0:
        print("\n[SUCCESS] All model cost configurations validated successfully.")
    else:
        print(f"\n[FAILURE] {failed_count} models failed validation.")

if __name__ == "__main__":
    config_file = os.path.join(os.path.dirname(__file__), "..", "config", "models.json")
    validate_model_costs(config_file)
