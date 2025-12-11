import time
import httpx
import os
import logging
from typing import Tuple, Optional, Dict, Any, List
from core.interfaces.llm import ILLMProvider
from core.http_client import HttpClient
from core.config import settings
from google.auth import default
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

class VertexAIProvider(ILLMProvider):
    """
    Vertex AI provider for Gemini models.
    Supports both API key and Application Default Credentials (ADC).
    """

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

        if has_image:
            mode = pricing_config.get('image_price_mode', 'per_image')
            if mode == 'per_image':
                cost += float(pricing_config.get('image_price_val', 0))

        discount = float(pricing_config.get('discount_percent', 0))
        if discount > 0:
            cost = cost * (1 - (discount / 100))

        return round(cost, 6)

    async def _get_access_token(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get access token using Application Default Credentials (ADC).
        This works in both local dev (with gcloud auth) and GCP environments.
        Returns tuple of (token, project_id)
        """
        try:
            credentials, project = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])

            # Refresh token if needed
            if not credentials.valid:
                auth_req = Request()
                credentials.refresh(auth_req)

            return credentials.token, project
        except Exception as e:
            logger.warning(f"Failed to get ADC token: {e}")
            return None, None

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

        # Prepare request payload
        # Structure for Vertex AI Gemini API:
        # {
        #   "contents": [
        #     { "role": "user", "parts": [ { "text": "..." } ] }
        #   ],
        #   "systemInstruction": {
        #     "parts": [ { "text": "..." } ]
        #   },
        #   "generationConfig": { ... }
        # }

        parts = []
        if image_data and mime_type:
            parts.append({"inline_data": {"mime_type": mime_type, "data": image_data}})
        parts.append({"text": prompt})

        # Ensure types are correct to avoid 400 Bad Request
        request_body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": float(temperature),
                "maxOutputTokens": int(max_tokens)
            }
        }

        # Add system instruction if provided
        # NOTE: Do NOT add 'role': 'user' here, it can cause 400 errors.
        if system_message:
            request_body["systemInstruction"] = {
                "parts": [{"text": system_message}]
            }

        # Vertex AI requires ADC (Application Default Credentials)
        logger.info("Using ADC authentication for Vertex AI")
        access_token, project_id = await self._get_access_token()

        if not access_token:
            raise ValueError(
                "No valid credentials found for Vertex AI.\n"
                "Local development: Run 'gcloud auth application-default login'\n"
                "GCP production: Workload identity is configured automatically"
            )

        # Use project from settings if not detected from ADC, or override if needed
        if settings.GCP_PROJECT_ID:
            project_id = settings.GCP_PROJECT_ID

        if not project_id:
            raise ValueError("GCP Project ID not found. Please set GCP_PROJECT_ID in settings or ensure ADC provides it.")

        location = settings.GCP_LOCATION or "us-central1"

        # Build Vertex AI endpoint URL
        # Standard format: https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/publishers/google/models/{MODEL}:generateContent

        # Support for Global Endpoint (Dynamic Routing)
        # If location is explicitly set to 'global', use the global endpoint format.
        # Format: https://aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/global/publishers/google/models/{MODEL}:generateContent
        if location.lower() == 'global':
            endpoint = f"https://aiplatform.googleapis.com/v1/projects/{project_id}/locations/global/publishers/google/models/{model_name}:generateContent"
        else:
            # Regional endpoint (Standard/Default)
            # CRITICAL: The URL path MUST include 'projects/{id}/locations/{loc}' to work.
            endpoint = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model_name}:generateContent"

        client = HttpClient.get_client()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        # DEBUG: Log the exact request for troubleshooting 400 errors
        logger.info(f"=== VERTEX AI REQUEST DEBUG ===")
        logger.info(f"Endpoint: {endpoint}")
        # logger.info(f"Headers: {headers}") # Don't log headers with token
        logger.info(f"Request Body: {request_body}")
        logger.info(f"=== END DEBUG ===")

        response = await client.post(
            endpoint,
            headers=headers,
            json=request_body
        )

        latency = int((time.time() - start_time) * 1000)

        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"=== VERTEX AI ERROR DEBUG ===")
            logger.error(f"Status Code: {response.status_code}")
            logger.error(f"Response: {error_detail}")
            logger.error(f"Request was: {request_body}")
            logger.error(f"=== END ERROR DEBUG ===")
            raise Exception(f"Vertex AI API error (status {response.status_code}): {error_detail}")

        result = response.json()

        # Parse response
        try:
            candidates = result.get('candidates', [])
            if not candidates:
                # Handle blocked response (safety filters)
                if result.get('promptFeedback', {}).get('blockReason'):
                    block_reason = result.get('promptFeedback', {}).get('blockReason')
                    raise ValueError(f"Response blocked by safety filters: {block_reason}")
                raise ValueError("No candidates in response")

            content = candidates[0].get('content', {})
            parts = content.get('parts', [])

            if not parts:
                raise ValueError("No parts in response content")

            text = parts[0].get('text', '')
        except (IndexError, KeyError, AttributeError) as e:
            logger.error(f"Failed to parse Vertex AI response: {e}")
            logger.error(f"Response: {result}")
            text = ""

        # Extract usage metadata
        usage = result.get('usageMetadata', {})
        usage_metadata = {
            'prompt_tokens': usage.get('promptTokenCount', 0),
            'completion_tokens': usage.get('candidatesTokenCount', 0),
            'total_tokens': usage.get('totalTokenCount', 0)
        }

        return text, latency, usage_metadata
