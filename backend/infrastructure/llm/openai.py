import time
import httpx
import math
import tiktoken
import base64
import io
from PIL import Image as PILImage
from typing import Tuple, Optional, Dict, Any, List
from core.interfaces.llm import ILLMProvider
from core.http_client import HttpClient

class OpenAIProvider(ILLMProvider):
    def _get_encoding(self, model_name: str):
        try:
            return tiktoken.encoding_for_model(model_name)
        except KeyError:
            return tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str, model_name: str) -> int:
        if not text:
            return 0
        try:
            encoding = self._get_encoding(model_name)
            return len(encoding.encode(text))
        except Exception:
            return len(text) // 4

    def _calculate_image_tokens(self, width: int, height: int, detail: str = "high") -> int:
        """
        Calculate OpenAI image tokens based on "high" or "low" detail.
        Ref: https://openai.com/pricing
        """
        if detail == "low":
            return 85

        # High detail calculation
        # 1. Scale to fit within 2048x2048
        if width > 2048 or height > 2048:
            ratio = min(2048 / width, 2048 / height)
            width = int(width * ratio)
            height = int(height * ratio)

        # 2. Scale shortest side to 768px
        if width < height:
            if width > 768:
                ratio = 768 / width
                width = 768
                height = int(height * ratio)
        else:
            if height > 768:
                ratio = 768 / height
                height = 768
                width = int(width * ratio)

        # 3. Calculate 512px tiles
        h_tiles = math.ceil(width / 512)
        v_tiles = math.ceil(height / 512)
        total_tiles = h_tiles * v_tiles

        return (total_tiles * 170) + 85

    def estimate_cost(
        self,
        input_text: str,
        output_est_text: str,
        images: List[str],
        pricing_config: Dict[str, Any]
    ) -> float:
        input_price = float(pricing_config.get('input_price_per_1m', 0))
        output_price = float(pricing_config.get('output_price_per_1m', 0))
        model_name = "gpt-4o" # Default or passed? Ideally passed, but interface limits. 
                              # We'll use a standard encoding.

        # Text tokens
        input_tokens = self._count_tokens(input_text, model_name)
        output_tokens = self._count_tokens(output_est_text, model_name)

        # Image tokens
        image_tokens = 0
        for img_b64 in images:
            try:
                img_bytes = base64.b64decode(img_b64)
                with PILImage.open(io.BytesIO(img_bytes)) as img:
                    w, h = img.size
                image_tokens += self._calculate_image_tokens(w, h)
            except Exception:
                # Fallback
                image_tokens += 765

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
        # OpenAI includes image tokens in prompt_tokens, so logic is simple
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

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})

        content = []
        if image_data and mime_type:
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}})
        content.append({"type": "text", "text": prompt})

        messages.append({
            "role": "user",
            "content": content
        })

        client = HttpClient.get_client()
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )

        latency = int((time.time() - start_time) * 1000)

        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.text}")

        result = response.json()
        text = result.get('choices', [{}])[0].get('message', {}).get('content', '')

        # Extract usage metadata
        usage = result.get('usage', {})
        usage_metadata = {
            'prompt_tokens': usage.get('prompt_tokens', 0),
            'completion_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0)
        }

        return text, latency, usage_metadata
