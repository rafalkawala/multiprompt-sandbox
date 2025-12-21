
import asyncio
import os
import sys
import json
import structlog
from google.auth import default
from google.auth.transport.requests import Request
import httpx

# Configure logging
logger = structlog.get_logger(__name__)

async def test_vertex_models():
    """
    Test all Vertex AI models from models.json configuration.
    """
    print("\n=== Testing Vertex AI Models from Configuration ===\n")

    # 1. Check Credentials
    print("1. Checking Application Default Credentials (ADC)...")
    try:
        credentials, project_id = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])

        # Refresh if needed
        if not credentials.valid:
            auth_req = Request()
            credentials.refresh(auth_req)

        print(f"   [OK] Credentials found.")
        print(f"   [OK] Token obtained")

        # If project_id is not in ADC, check env var
        if not project_id:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID")

        if project_id:
            print(f"   [OK] Project ID: {project_id}")
        else:
            print("   [ERROR] Project ID not found.")
            return

    except Exception as e:
        print(f"   [FAIL] Failed to load credentials: {e}")
        print("   Run 'gcloud auth application-default login'")
        return

    # 2. Load models.json
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "models.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        models = json.load(f)

    # Filter for Vertex AI models
    vertex_models = [m for m in models if m.get("provider") == "vertex"]

    print(f"\n2. Testing {len(vertex_models)} Vertex AI models...\n")

    location = os.environ.get("GCP_LOCATION", "us-central1")

    for model_config in vertex_models:
        model_id = model_config.get("id")
        model_name = model_config.get("model_name")
        display_name = model_config.get("display_name")

        print(f"--- {display_name} ---")
        print(f"   ID: {model_id}")
        print(f"   Model Name: {model_name}")

        endpoint = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model_name}:generateContent"

        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": "Say 'OK' only."}]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 5
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {credentials.token}"
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(endpoint, headers=headers, json=body)

                if response.status_code == 200:
                    result = response.json()
                    candidates = result.get('candidates', [])
                    if candidates:
                        content = candidates[0].get('content', {})
                        parts = content.get('parts', [])
                        if parts:
                            reply_text = parts[0].get('text', '')
                            print(f"   Status: [OK] WORKING")
                            print(f"   Reply: '{reply_text}'")
                        else:
                            print(f"   Status: [OK] Response OK but no reply")
                    else:
                        print(f"   Status: [OK] Response OK but no candidates")
                elif response.status_code == 404:
                    print(f"   Status: [FAIL] NOT FOUND (404) - Model not available in Vertex AI")
                else:
                    try:
                        err_json = response.json()
                        error_msg = err_json.get('error', {}).get('message', response.text[:100])
                        print(f"   Status: [FAIL] ERROR ({response.status_code}): {error_msg}")
                    except:
                        print(f"   Status: [FAIL] ERROR ({response.status_code})")
        except Exception as e:
            print(f"   Status: [FAIL] EXCEPTION: {str(e)[:80]}")

        print()

    print("=== Test Complete ===\n")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_vertex_models())
