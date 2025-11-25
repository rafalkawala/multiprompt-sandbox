import time
import httpx
from typing import Tuple, Optional
from backend.core.interfaces.llm import ILLMProvider
from backend.core.http_client import HttpClient

class OpenAIProvider(ILLMProvider):
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
    ) -> Tuple[str, int]:
        
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
        return text, latency
