import time
import httpx
import base64
import os
from typing import Tuple, Optional, Dict, Any, List
from core.interfaces.llm import ILLMProvider
from core.http_client import HttpClient

class GeminiProvider(ILLMProvider):
    def _count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(text) // 4

    def estimate_cost(
        self,
        input_text: str,
        output_est_text: str,
        images: List[str],
        pricing_config: Dict[str, Any]
    ) -> float:
        input_price = float(pricing_config.get('input_price_per_1m', 0))
        output_price = float(pricing_config.get('output_price_per_1m', 0))

        # Text tokens
        input_tokens = self._count_tokens(input_text)
        output_tokens = self._count_tokens(output_est_text)

        text_cost = (input_tokens / 1_000_000 * input_price) + \
                    (output_tokens / 1_000_000 * output_price)

        # Image Cost
        image_cost = 0.0
        mode = pricing_config.get('image_price_mode', 'per_image')

        for _ in images:
            if mode == 'per_image':
                val = float(pricing_config.get('image_price_val', 0))
                image_cost += val
            else:
                # Fallback to token based (approx 258 tokens per image)
                tokens = 258
                image_cost += (tokens / 1_000_000) * input_price

        total_cost = text_cost + image_cost

        discount = float(pricing_config.get('discount_percent', 0))
        if discount > 0:
            total_cost = total_cost * (1 - (discount / 100))

        return total_cost

    def calculate_actual_cost(
        self,
        usage_metadata: Dict[str, Any],
        pricing_config: Dict[str, Any],
        has_image: bool = False
    ) -> float:
        p_tokens = usage_metadata.get('prompt_tokens', 0)
        c_tokens = usage_metadata.get('completion_tokens', 0)

        in_price = float(pricing_config.get('input_price_per_1m', 0))
        out_price = float(pricing_config.get('output_price_per_1m', 0))

        cost = (p_tokens / 1_000_000 * in_price) + (c_tokens / 1_000_000 * out_price)

        # Add per-image fixed cost if applicable
        # (Assuming Gemini token counts might NOT include the image "tokens" if billed per-image)
        if has_image:
            mode = pricing_config.get('image_price_mode', 'per_image')
            if mode == 'per_image':
                # We don't know exact image count from metadata usually,
                # but if has_image is True, we assume at least 1?
                # Ideally calculate_actual_cost should take image_count if variable.
                # For now, assuming 1 image if has_image=True for single request context.
                # This limits accuracy for multi-image requests if only boolean passed.
                # NOTE: To fix this, we'd need to pass image_count to this method.
                # Given interface 'has_image' boolean, we assume 1.
                cost += float(pricing_config.get('image_price_val', 0))

        discount = float(pricing_config.get('discount_percent', 0))
        if discount > 0:
            cost = cost * (1 - (discount / 100))

        return cost

    async def generate_content(
        self,
        api_key: Optional[str],
        auth_type: Optional[str],
        model_name: str,
        image_data: Optional[str],
        mime_type: Optional[str],
        prompt: str,
        system_message: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> Tuple[str, int, Dict[str, Any]]:
        
        start_time = time.time()

        if not api_key or api_key == "sk-placeholder":
             raise ValueError("Gemini API Key is required. Please set GEMINI_API_KEY environment variable.")

        # Combine system message with prompt
        full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt

        # Prepare parts
        parts = []
        if image_data and mime_type:
            parts.append({"inline_data": {"mime_type": mime_type, "data": image_data}})
        parts.append({"text": full_prompt})

        # Use Google AI API with API key (local development)
        client = HttpClient.get_client()
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
            params={"key": api_key},
            json={
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens
                }
            }
        )

        latency = int((time.time() - start_time) * 1000)

        if response.status_code != 200:
            raise Exception(f"Gemini API error: {response.text}")

        result = response.json()
        try:
            text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        except (IndexError, AttributeError):
            text = ""

        # Extract usage metadata
        usage = result.get('usageMetadata', {})
        usage_metadata = {
            'prompt_tokens': usage.get('promptTokenCount', 0),
            'completion_tokens': usage.get('candidatesTokenCount', 0),
            'total_tokens': usage.get('totalTokenCount', 0)
        }

        return text, latency, usage_metadata
