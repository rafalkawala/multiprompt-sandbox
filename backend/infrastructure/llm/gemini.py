import time
import os
import httpx
from typing import Tuple, Optional
from core.interfaces.llm import ILLMProvider
from core.http_client import HttpClient

class GeminiProvider(ILLMProvider):
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
            
        return text, latency

    async def _call_vertex(self, model_name: str, image_data: Optional[str], mime_type: Optional[str], prompt: str, temperature: float, max_tokens: int, start_time: float) -> Tuple[str, int]:
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
            
        return text, latency
