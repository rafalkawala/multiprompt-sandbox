import time
import httpx
import math
import base64
import io
from PIL import Image as PILImage
from typing import Tuple, Optional, Dict, Any, List
from core.interfaces.llm import ILLMProvider
from core.http_client import HttpClient

class AnthropicProvider(ILLMProvider):
    def _count_tokens(self, text: str) -> int:
        if not text:
            return 0
        # Simple heuristic: 1 token ~= 4 chars
        return len(text) // 4

    def _calculate_image_tokens(self, width: int, height: int) -> int:
        """
        Calculate Anthropic image tokens.
        Ref: (width * height) / 750 tokens
        """
        return math.ceil((width * height) / 750)

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

        # Image tokens
        image_tokens = 0
        for img_b64 in images:
            try:
                img_bytes = base64.b64decode(img_b64)
                with PILImage.open(io.BytesIO(img_bytes)) as img:
                    w, h = img.size
                image_tokens += self._calculate_image_tokens(w, h)
            except Exception:
                # Fallback: ~1.15MP standard optimal size = 1600 tokens
                image_tokens += 1600

        # Total Calculation
        total_input_tokens = input_tokens + image_tokens
        
        cost = (total_input_tokens / 1_000_000 * input_price) + \
               (output_tokens / 1_000_000 * output_price)

        discount = float(pricing_config.get('discount_percent', 0))
        if discount > 0:
            cost = cost * (1 - (discount / 100))

        return cost

    def calculate_actual_cost(
        self,
        usage_metadata: Dict[str, Any],
        pricing_config: Dict[str, Any],
        has_image: bool = False
    ) -> float:
        # Anthropic includes image tokens in prompt_tokens
        p_tokens = usage_metadata.get('prompt_tokens', 0)
        c_tokens = usage_metadata.get('completion_tokens', 0)

        in_price = float(pricing_config.get('input_price_per_1m', 0))
        out_price = float(pricing_config.get('output_price_per_1m', 0))

        cost = (p_tokens / 1_000_000 * in_price) + (c_tokens / 1_000_000 * out_price)

        discount = float(pricing_config.get('discount_percent', 0))
        if discount > 0:
            cost = cost * (1 - (discount / 100))

        return round(cost, 6)

    async def generate_content(
        self,
        api_key: Optional[str],
        model_name: str,
        image_data: Optional[str],
        mime_type: Optional[str],
        prompt: str,
        system_message: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> Tuple[str, int, Dict[str, Any]]:

        start_time = time.time()

        content = []
        if image_data and mime_type:
            content.append({"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": image_data}})
        content.append({"type": "text", "text": prompt})

        request_body = {
            "model": model_name,
            "max_tokens": max_tokens,
            "messages": [{
                "role": "user",
                "content": content
            }]
        }

        if system_message:
            request_body["system"] = system_message

        client = HttpClient.get_client()
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json=request_body
        )

        latency = int((time.time() - start_time) * 1000)

        if response.status_code != 200:
            raise Exception(f"Anthropic API error: {response.text}")

        result = response.json()
        text = result.get('content', [{}])[0].get('text', '')

        # Extract usage metadata
        usage = result.get('usage', {})
        usage_metadata = {
            'prompt_tokens': usage.get('input_tokens', 0),
            'completion_tokens': usage.get('output_tokens', 0),
            'total_tokens': usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
        }

        return text, latency, usage_metadata
