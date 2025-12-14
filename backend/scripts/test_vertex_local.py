
import asyncio
import os
import sys
import structlog
import json
from google.auth import default
from google.auth.transport.requests import Request
import httpx

# Configure logging
logger = structlog.get_logger(__name__)

async def test_vertex_connection():
    """
    Test connectivity to Vertex AI using local credentials (ADC).
    """
    print("\n=== Testing Vertex AI Local Connectivity & Diagnostics ===\n")

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
    # Use a real model for the "Valid" test
    valid_model_name = "gemini-2.5-flash-lite"
    # Use the model name likely in the user's config to test if THAT is the cause
    config_model_name = "gemini-3-pro-preview"


    # --- Helper to send request ---
    async def run_test(name, model, payload_modifier=None):
        print(f"\n--- TEST: {name} ---")
        endpoint = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model}:generateContent"

        # Base valid payload
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": "Hello, reply with 'OK'."}]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 10
            }
        }

        # Print the prompt being sent
        prompt_text = body["contents"][0]["parts"][0]["text"]
        print(f"   Prompt: \"{prompt_text}\"")
        print(f"   Model: {model}")

        if payload_modifier:
            body = payload_modifier(body)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {credentials.token}"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(endpoint, headers=headers, json=body)

                print(f"   Status Code: {response.status_code}")
                if response.status_code != 200:
                    try:
                        err_json = response.json()
                        print(f"   Error JSON: {json.dumps(err_json, indent=2)}")
                    except:
                        print(f"   Error Text: {response.text}")
                else:
                    print("   [SUCCESS] Request worked.")
                    try:
                        result = response.json()
                        # Extract and print the response text
                        candidates = result.get('candidates', [])
                        if candidates:
                            content = candidates[0].get('content', {})
                            parts = content.get('parts', [])
                            if parts:
                                reply_text = parts[0].get('text', '')
                                print(f"   Reply: \"{reply_text}\"")
                            else:
                                print("   [WARNING] No parts in response")
                        else:
                            print("   [WARNING] No candidates in response")
                    except Exception as e:
                        print(f"   Could not parse response: {e}")

        except Exception as e:
            print(f"   [FAIL] Exception: {e}")

    # TEST A: Happy Path (Valid Model, Valid Payload)
    await run_test("Happy Path - Valid Request", valid_model_name)

    # TEST B: Invalid Payload - System Instruction with Role (The fix I made)
    def add_bad_system_instruction(body):
        body["systemInstruction"] = {
            "role": "user", # <--- THIS IS THE BUG
            "parts": [{"text": "Be helpful."}]
        }
        return body

    await run_test("Diagnostic: Bad Payload (System Role)", valid_model_name, add_bad_system_instruction)

    # TEST C: Invalid Payload - Wrong Types (String instead of Float)
    def add_bad_types(body):
        body["generationConfig"]["temperature"] = "0.5" # String!
        return body

    await run_test("Diagnostic: Bad Payload (String Types)", valid_model_name, add_bad_types)

    # TEST D: Invalid Model Name (What's in their config)
    await run_test("Diagnostic: Invalid Model Name", config_model_name)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_vertex_connection())
