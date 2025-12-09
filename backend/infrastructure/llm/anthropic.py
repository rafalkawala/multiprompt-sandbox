import time
import httpx
from typing import Tuple, Optional, Dict, Any
from core.interfaces.llm import ILLMProvider
from core.http_client import HttpClient

class AnthropicProvider(ILLMProvider):
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
