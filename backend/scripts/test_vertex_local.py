
import asyncio
import os
import sys
import logging
import json
from google.auth import default
from google.auth.transport.requests import Request
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_vertex_connection():
    """
    Test connectivity to Vertex AI using local credentials (ADC).
    """
    print("\n=== Testing Vertex AI Local Connectivity ===\n")

    # 1. Check Credentials
    print("1. Checking Application Default Credentials (ADC)...")
    try:
        credentials, project_id = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])

        # Refresh if needed
        if not credentials.valid:
            auth_req = Request()
            credentials.refresh(auth_req)

        print(f"   [OK] Credentials found.")
        print(f"   [OK] Token obtained (starts with: {credentials.token[:10]}...)")

        # If project_id is not in ADC, check env var
        if not project_id:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID")

        if project_id:
            print(f"   [OK] Project ID: {project_id}")
        else:
            print("   [WARNING] Project ID not found in ADC or environment variables.")
            print("   Please run 'gcloud config set project <YOUR_PROJECT_ID>' or set GOOGLE_CLOUD_PROJECT env var.")
            return

    except Exception as e:
        print(f"   [FAIL] Failed to load credentials: {e}")
        print("   Run 'gcloud auth application-default login' to set up local credentials.")
        return

    # 2. Configure Request
    location = os.environ.get("GCP_LOCATION", "us-central1")
    model_name = "gemini-1.5-pro-preview-0409" # Or another available model

    # Use the regional endpoint structure
    endpoint = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model_name}:generateContent"

    print(f"\n2. Preparing Request...")
    print(f"   Endpoint: {endpoint}")

    request_body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "Hello, this is a test from the local environment. Please reply with 'Success'."}]
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 100
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {credentials.token}"
    }

    # 3. Send Request
    print(f"\n3. Sending Request to Vertex AI...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, headers=headers, json=request_body)

            if response.status_code == 200:
                print("   [SUCCESS] Response received!")
                data = response.json()
                try:
                    text = data['candidates'][0]['content']['parts'][0]['text']
                    print(f"   Response Text: {text.strip()}")
                except:
                    print(f"   Raw Response: {json.dumps(data, indent=2)}")
            else:
                print(f"   [FAIL] Status Code: {response.status_code}")
                print(f"   Error Response: {response.text}")

    except Exception as e:
        print(f"   [FAIL] Request failed: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_vertex_connection())
