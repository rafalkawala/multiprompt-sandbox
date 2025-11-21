# API Documentation

> **Last Updated**: 2025-11-21

Base URL: `http://localhost:8000` (development) or your production URL

## Interactive Documentation

API documentation is automatically generated and available at:
- **Swagger UI**: `/docs` - Interactive API testing
- **ReDoc**: `/redoc` - Clean, readable documentation
- **OpenAPI JSON**: `/openapi.json` - Machine-readable spec

## Current Implementation Status

**Working**:
- Image analysis endpoints
- Google OAuth authentication
- User management (CRUD)

**Disabled**: Agent execution endpoints (LangChain import issues)
**Planned**: Projects, datasets, experiments, results endpoints

## Authentication

**Current Status**: JWT-based authentication with Google OAuth

**Implemented**:
- JWT-based authentication (30 min token expiry)
- OAuth2 with Google Sign-In
- Role-based access control (Admin, User, Viewer)

**Planned**:
- API key authentication for programmatic access

## Endpoints

### Health Check

#### GET `/health`
Check if the API is running.

**Response:**
```json
{
  "status": "healthy",
  "environment": "development"
}
```

#### GET `/ready`
Kubernetes readiness probe.

**Response:**
```json
{
  "status": "ready"
}
```

### Authentication Endpoints

Base path: `/api/v1/auth`

#### GET `/api/v1/auth/google/login`
Get Google OAuth URL to initiate login.

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&response_type=code&scope=openid%20email%20profile"
}
```

#### GET `/api/v1/auth/google/callback`
Handle Google OAuth callback (redirects to frontend with JWT token).

**Query Parameters:**
- `code`: Authorization code from Google

**Response:** Redirects to `{FRONTEND_URL}/auth/callback?token={jwt_token}`

#### GET `/api/v1/auth/me`
Get current user info.

**Query Parameters:**
- `token`: JWT token

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "picture_url": "https://...",
  "role": "admin|user|viewer",
  "is_active": true,
  "created_at": "2025-11-21T10:00:00",
  "last_login_at": "2025-11-21T10:00:00"
}
```

#### POST `/api/v1/auth/logout`
Logout endpoint (client should discard token).

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

### User Management Endpoints (Admin Only)

Base path: `/api/v1/users`

All endpoints require `Authorization: Bearer {token}` header with admin role.

#### GET `/api/v1/users/`
List all users.

**Response:**
```json
[
  {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name",
    "picture_url": "https://...",
    "role": "user",
    "is_active": true,
    "created_at": "2025-11-21T10:00:00",
    "last_login_at": "2025-11-21T10:00:00"
  }
]
```

#### POST `/api/v1/users/`
Create a new user.

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "name": "New User",
  "role": "user"
}
```

#### GET `/api/v1/users/{user_id}`
Get user by ID.

#### PATCH `/api/v1/users/{user_id}`
Update user.

**Request Body:**
```json
{
  "name": "Updated Name",
  "role": "admin",
  "is_active": false
}
```

#### DELETE `/api/v1/users/{user_id}`
Delete user (cannot delete self).

### Agent Endpoints ⚠️ CURRENTLY DISABLED

Base path: `/api/v1/agents`

**Status**: These endpoints are currently **disabled** due to import issues with `langchain_community.tools`.

**Tracking**: The agent service code exists in `backend/app/services/agent_service.py` but the router is commented out in `backend/app/api/v1/__init__.py` (line ~23).

#### POST `/api/v1/agents/execute` (DISABLED)
Execute a LangChain agent with a given prompt.

**Planned Request Body:**
```json
{
  "prompt": "What is 25 * 4?",
  "context": {
    "user_id": "123",
    "session_id": "abc"
  },
  "max_iterations": 10
}
```

**Planned Response:**
```json
{
  "result": "The result of 25 * 4 is 100.",
  "intermediate_steps": [
    {
      "action": "Calculator",
      "input": "25 * 4",
      "output": "Result: 100"
    }
  ],
  "total_tokens": null
}
```

**Status Codes:**
- `200 OK`: Successful execution
- `400 Bad Request`: Invalid input
- `500 Internal Server Error`: Agent execution failed

#### GET `/api/v1/agents/health` (DISABLED)
Check agent service health.

**Planned Response:**
```json
{
  "status": "healthy",
  "service": "agents"
}
```

> **Note**: These endpoints will be re-enabled once the LangChain dependency issues are resolved or when the agent functionality is redesigned for the MLLM benchmarking use case.

### Image Analysis Endpoints

Base path: `/api/v1/images`

#### POST `/api/v1/images/analyze`
Analyze an image using Gemini Pro Vision.

**Content-Type:** `multipart/form-data`

**Form Data:**
- `file` (required): Image file (JPEG, PNG, GIF, WebP)
- `prompt` (optional): Custom analysis prompt (default: "Describe this image in detail")

**Example using cURL:**
```bash
curl -X POST "http://localhost:8000/api/v1/images/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@image.jpg" \
  -F "prompt=Describe this image in detail"
```

**Response:**
```json
{
  "description": "A beautiful sunset over the ocean with orange and pink hues in the sky. A silhouette of a person standing on the beach.",
  "labels": ["nature", "outdoor", "person"],
  "confidence": null
}
```

**Status Codes:**
- `200 OK`: Successful analysis
- `400 Bad Request`: Invalid file type or size
- `500 Internal Server Error`: Analysis failed

**Constraints:**
- Max file size: 10MB
- Allowed types: image/jpeg, image/png, image/gif, image/webp

#### GET `/api/v1/images/health`
Check image service health.

**Response:**
```json
{
  "status": "healthy",
  "service": "images"
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing or invalid auth |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

## Rate Limiting

(To be implemented)

Future versions will implement rate limiting:
- 100 requests per minute per IP
- 1000 requests per hour per user

## Pagination

(To be implemented)

Future endpoints returning lists will support pagination:

```
GET /api/v1/resource?page=1&limit=10
```

## Versioning

The API uses URL versioning (`/api/v1/`). When breaking changes are introduced, a new version will be created (`/api/v2/`).

## Client Libraries

(To be implemented)

Future releases will include:
- Python client
- TypeScript/JavaScript client
- OpenAPI-generated clients

## Testing the API

### Using Swagger UI

1. Navigate to `http://localhost:8000/docs`
2. Expand any endpoint
3. Click "Try it out"
4. Fill in parameters
5. Click "Execute"

### Using cURL

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Agent Execution:**
```bash
curl -X POST "http://localhost:8000/api/v1/agents/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Calculate 15 + 27",
    "max_iterations": 5
  }'
```

**Image Analysis:**
```bash
curl -X POST "http://localhost:8000/api/v1/images/analyze" \
  -F "file=@path/to/image.jpg" \
  -F "prompt=What objects are in this image?"
```

### Using Python

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Agent execution
response = requests.post(
    "http://localhost:8000/api/v1/agents/execute",
    json={"prompt": "What is 10 * 5?"}
)
print(response.json())

# Image analysis
with open("image.jpg", "rb") as f:
    files = {"file": f}
    data = {"prompt": "Describe this image"}
    response = requests.post(
        "http://localhost:8000/api/v1/images/analyze",
        files=files,
        data=data
    )
print(response.json())
```

## WebSocket Support

(To be implemented)

Future versions will support WebSocket connections for real-time agent streaming:

```
ws://localhost:8000/api/v1/agents/stream
```

## Changelog

### v0.2.0 (Current - 2025-11-21)
- Google OAuth authentication
- JWT token-based sessions
- User management CRUD endpoints
- Role-based access control (Admin, User, Viewer)
- Database migrations for user model

### v0.1.0 (2025-11-14)
- Initial API release
- Agent execution endpoint
- Image analysis endpoint
- Basic health checks
