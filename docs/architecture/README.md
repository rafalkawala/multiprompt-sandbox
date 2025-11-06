# Architecture Documentation

## System Overview

MultiPrompt Sandbox is a full-stack application that combines:
- **Frontend**: Angular 17+ with TypeScript
- **Backend**: Python FastAPI with LangChain agents
- **AI Services**: Google Gemini Pro for image recognition
- **Infrastructure**: Kubernetes (GKE) on Google Cloud Platform

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        Users                             │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Google Cloud Load Balancer                  │
│                     (Ingress)                            │
└─────────────────────┬───────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
┌──────────────────┐    ┌──────────────────┐
│   Frontend Pod   │    │   Backend Pod    │
│   (Angular)      │    │   (FastAPI)      │
│   - Nginx        │────│   - LangChain    │
│   - Static Files │    │   - Agents       │
└──────────────────┘    └────────┬─────────┘
                                 │
                    ┌────────────┼────────────┐
                    │                         │
                    ▼                         ▼
         ┌─────────────────┐      ┌─────────────────┐
         │  Gemini Pro API │      │  LangChain Hub  │
         │  (Image Recog)  │      │  (Prompts)      │
         └─────────────────┘      └─────────────────┘
```

## Component Architecture

### Frontend (Angular)

```
src/
├── app/
│   ├── core/              # Singleton services, guards
│   ├── shared/            # Shared components, pipes, directives
│   ├── features/          # Feature modules
│   │   ├── home/
│   │   ├── image-analysis/
│   │   └── agent-chat/
│   └── models/            # TypeScript interfaces
```

**Key Features:**
- Standalone components (Angular 17+)
- Lazy loading for features
- RxJS for reactive state management
- HTTP interceptors for API communication

### Backend (FastAPI)

```
app/
├── api/                   # API endpoints
│   └── v1/
│       └── endpoints/     # Route handlers
├── core/                  # Core functionality
│   └── config.py          # Settings
├── services/              # Business logic
│   ├── agent_service.py   # LangChain agents
│   └── gemini_service.py  # Gemini integration
├── models/                # Database models (if needed)
└── schemas/               # Pydantic schemas
```

**Key Features:**
- Async/await for I/O operations
- Pydantic for data validation
- Dependency injection
- OpenAPI documentation

### LangChain Agent System

```python
Agent Workflow:
1. User prompt → Agent Executor
2. Agent analyzes task → Selects tools
3. Tool execution → Results
4. Agent synthesis → Response
5. Return to user
```

**Available Tools:**
- Search tool (placeholder for web search)
- Calculator tool
- Custom tools (extensible)

### Gemini Integration

```python
Image Analysis Flow:
1. User uploads image
2. FastAPI receives file
3. Validate format & size
4. Send to Gemini Pro Vision
5. Receive analysis
6. Extract labels & description
7. Return structured response
```

## Data Flow

### Image Analysis Request
```
User → Frontend → Backend API → Gemini Pro → Backend → Frontend → User
```

### Agent Execution Request
```
User → Frontend → Backend API → LangChain Agent → Tools → Agent → Backend → Frontend → User
```

## Security Considerations

1. **API Security**
   - CORS configuration
   - API key management (secrets)
   - Rate limiting (to be implemented)

2. **Data Validation**
   - Input sanitization
   - File type validation
   - Size limits

3. **Authentication** (to be implemented)
   - JWT tokens
   - OAuth2 integration

## Scalability

- **Horizontal Scaling**: Multiple pod replicas
- **Auto-scaling**: HPA based on CPU/memory
- **Load Balancing**: GKE ingress
- **Caching**: To be implemented

## Monitoring & Logging

(To be implemented)
- Application logs
- Performance metrics
- Error tracking
- Distributed tracing

## Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | Angular 17, TypeScript, RxJS |
| Backend | Python 3.11, FastAPI, Uvicorn |
| AI Framework | LangChain, LangGraph |
| AI Model | Google Gemini Pro |
| Container | Docker |
| Orchestration | Kubernetes (GKE) |
| CI/CD | GitHub Actions |
| Cloud | Google Cloud Platform |

## Future Enhancements

1. Add PostgreSQL database
2. Implement Redis caching
3. Add authentication system
4. Implement WebSocket for real-time updates
5. Add monitoring stack (Prometheus, Grafana)
6. Implement logging aggregation (ELK/EFK)
