import time
import httpx
import base64
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

        # Combine system message with prompt
        full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt

        # Use Vertex AI if no API key (service account auth in Cloud Run)
        if not api_key:
            return await self._call_vertex(model_name, image_data, mime_type, full_prompt, temperature, max_tokens, start_time)

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

    async def _call_vertex(self, model_name: str, image_data: Optional[str], mime_type: Optional[str], prompt: str, temperature: float, max_tokens: int, start_time: float) -> Tuple[str, int, Dict[str, Any]]:
        """Call Gemini via Vertex AI using service account credentials (ADC)"""
        import google.auth
        import google.auth.transport.requests
        import logging

        logger = logging.getLogger(__name__)

        try:
            # Get credentials and project from ADC
            credentials, project = google.auth.default()
            logger.info(f"Loaded credentials for project: {project}")
        except Exception as e:
            logger.error(f"Failed to load default credentials: {str(e)}")
            raise Exception(f"Failed to load Google Cloud credentials. Ensure service account is properly configured. Error: {str(e)}")

        # Get project from environment if not in credentials
        if not project:
            project = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('GCP_PROJECT') or os.environ.get('GCP_PROJECT_ID')
            logger.info(f"Using project from environment: {project}")

        if not project:
            raise Exception("No GCP project found. Set GOOGLE_CLOUD_PROJECT environment variable.")

        # Refresh credentials to get access token
        try:
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            logger.info("Successfully refreshed credentials")
        except Exception as e:
            logger.error(f"Failed to refresh credentials: {str(e)}")
            raise Exception(f"Failed to refresh Google Cloud credentials. Ensure the service account has aiplatform.endpoints.predict permission. Error: {str(e)}")

        # Vertex AI endpoint
        location = os.environ.get('VERTEX_AI_LOCATION', 'us-central1')
        endpoint = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/{model_name}:generateContent"

        parts = []
        if image_data and mime_type:
            parts.append({"inline_data": {"mime_type": mime_type, "data": image_data}})
        parts.append({"text": prompt})

        client = HttpClient.get_client()
        response = await client.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json"
            },
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": parts
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens
                }
            }
        )

        latency = int((time.time() - start_time) * 1000)

        if response.status_code != 200:
            raise Exception(f"Vertex AI error: {response.text}")

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
