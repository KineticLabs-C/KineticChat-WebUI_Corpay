# Technical Specification - KineticChat WebUI Service

## Executive Summary
This specification defines the technical architecture for extracting and refactoring the web-based chat interface from RXRefillCampaign_Alt1 into a standalone, production-ready service. The approach prioritizes feature parity, simplicity, and maintainability while establishing a foundation for future multi-client expansion. The service will be fully isolated with no dependencies on the original prototype, deployable on Render.com, and completed within Weeks 1-2.

## Architecture Overview

### System Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    Client Browser                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │           Static Assets (HTML/CSS/JS)             │  │
│  │              - index.html                         │  │
│  │              - app.js (Chat Logic)                │  │
│  │              - styles.css                         │  │
│  └───────────────────┬───────────────────────────────┘  │
└──────────────────────┼───────────────────────────────────┘
                       │ WebSocket/HTTPS
┌──────────────────────▼───────────────────────────────────┐
│                 KineticChat_WebUI                         │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              FastAPI Application                     │ │
│  │  ┌──────────────────────────────────────────────┐   │ │
│  │  │           API Routes Layer                   │   │ │
│  │  │  - /api/chat (WebSocket)                    │   │ │
│  │  │  - /api/health                              │   │ │
│  │  │  - /api/metrics                             │   │ │
│  │  └────────────────┬─────────────────────────────┘   │ │
│  │                   │                                  │ │
│  │  ┌────────────────▼─────────────────────────────┐   │ │
│  │  │          Business Logic Layer                │   │ │
│  │  │  - Chat Agent (kroger_chat_agent.py)        │   │ │
│  │  │  - Deterministic Handler                    │   │ │
│  │  │  - Language Detection                        │   │ │
│  │  └────────────────┬─────────────────────────────┘   │ │
│  │                   │                                  │ │
│  │  ┌────────────────▼─────────────────────────────┐   │ │
│  │  │           Data Access Layer                  │   │ │
│  │  │  - Conversation Store (In-Memory)            │   │ │
│  │  │  - RAG Client (Qdrant)                      │   │ │
│  │  │  - Metrics Store                            │   │ │
│  │  └──────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
                       │
           External Services
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
    ▼                  ▼                  ▼
┌─────────┐     ┌─────────┐        ┌──────────┐
│ OpenAI  │     │ Qdrant  │        │ Postgres │
│   API   │     │ Vector  │        │(Optional)│
└─────────┘     └─────────┘        └──────────┘
```

### Architecture Pattern
- **Selected**: Monolithic with modular components
- **Rationale**: 
  - Simplicity aligns with MVP requirements
  - Faster development within 2-week timeline
  - Easier deployment on Render.com
  - Lower operational complexity
- **Trade-offs**: 
  - Gain: Rapid development, simple deployment, easier debugging
  - Lose: Independent scaling of components (acceptable for MVP)

## Technology Stack

### Backend
- **Language**: Python 3.11
- **Framework**: FastAPI 0.116.1
- **Key Libraries**:
  - WebSocket: Built-in FastAPI WebSocket support
  - Validation: Pydantic 2.11.7
  - Async: asyncio with uvicorn 0.35.0
  - Environment: python-dotenv 1.1.1
  - HTTP Client: httpx 0.28.1
  - File handling: aiofiles 23.2.1

### AI/ML Stack
- **LLM**: OpenAI GPT-4o-mini (via openai 1.97.0)
- **Embeddings**: sentence-transformers 2.0.0
- **Vector DB**: Qdrant (qdrant-client 1.0.0)
- **Model**: all-mpnet-base-v2 for embeddings

### Database
- **Primary Database**: PostgreSQL via Supabase (REQUIRED for production)
- **Development Database**: In-memory SQLite for local testing only
- **Vector Store**: Qdrant Cloud (existing instance)
- **Schema Design**: Copy existing schema to `database/` folder, include relevant tables

### Infrastructure
- **Hosting**: Render.com (Web Service)
- **Container**: None (direct Python deployment)
- **CI/CD**: GitHub Actions
- **Monitoring**: Built-in health endpoints

## API Design

### API Architecture
- **Style**: REST + WebSocket (primary) + SSE (fallback) for real-time chat
- **Version Strategy**: URL-based (/api/v1/)
- **Documentation**: Auto-generated via FastAPI/OpenAPI

### Endpoint Structure

#### WebSocket Endpoints
```
WS   /api/v1/chat                 # Real-time chat communication
```

#### REST Endpoints
```
# Legacy endpoints (preserve for compatibility)
GET  /health                     # Service health check
GET  /metrics                    # Service metrics
GET  /static/{file}              # Serve static assets

# New versioned endpoints
GET  /api/v1/health              # Service health check
GET  /api/v1/metrics             # Service metrics
GET  /api/v1/status              # Detailed status info
POST /api/v1/chat/feedback       # Submit chat feedback
```

### Data Models

#### Chat Message Model
```json
{
  "id": "uuid",
  "conversationId": "uuid",
  "role": "user|assistant|system",
  "content": "string",
  "language": "en|es",
  "timestamp": "iso8601",
  "metadata": {
    "responseTime": "float",
    "sources": ["string"],
    "intent": "string"
  }
}
```

#### WebSocket Message Protocol
```json
// Client -> Server
{
  "type": "message|typing|language_change",
  "content": "string",
  "conversationId": "uuid",
  "language": "en|es"
}

// Server -> Client
{
  "type": "message|typing|error|status",
  "content": "string",
  "conversationId": "uuid",
  "metadata": {}
}
```

#### Conversation State Model
```json
{
  "conversationId": "uuid",
  "startTime": "iso8601",
  "lastActivity": "iso8601",
  "language": "en|es",
  "messages": ["Message[]"],
  "context": {
    "detectedIntents": ["string"],
    "ragSources": ["string"]
  }
}
```

## Security Architecture

### Authentication & Authorization
- **Method**: Stateless/Anonymous (no authentication required)
- **Session Management**: Correlation IDs for conversation tracking
- **Rate Limiting**: Per-IP rate limiting

### Security Measures
- Input validation: Pydantic models with strict validation
- Prompt injection prevention: Input sanitization and role boundaries
- Rate limiting: 100 requests/minute per IP
- XSS prevention: Content Security Policy headers
- CORS: Configured for specific origins
- PHI handling: No storage of personal health information
- PHI scrubbing: All logs PHI-scrubbed BEFORE writing (Phase 1 requirement)
- Audit logging: All interactions logged without PHI/PII
- HIPAA compliance: Full compliance from Phase 1, not deferred

## Component Details

### Core Components

#### 1. Chat Agent (kroger_chat_agent.py)
- Enhanced RAG-powered agent from prototype
- Query expansion for better recall
- Multi-query retrieval
- Anti-hallucination measures
- Language detection and switching

#### 2. Deterministic Handler
- Pattern matching for common queries
- Vaccine information responses
- Policy and compliance responses
- Emergency contact routing

#### 3. Static Asset Server
- Serves index.html, app.js, styles.css
- CDN-ready with cache headers
- Compression enabled

#### 4. WebSocket Manager
- Connection lifecycle management
- Message queuing
- Error recovery
- Heartbeat/ping-pong

#### 5. Metrics Collector
- Response time tracking
- Error rate monitoring
- Conversation analytics
- Language usage statistics

## Development Plan

### Week 1: Foundation & Core Services

#### Day 1-2: Project Setup
- Initialize KineticChat_WebUI directory structure
- Set up FastAPI application skeleton
- Configure environment variables
- Implement basic health/status endpoints

#### Day 3-4: Static Assets & UI
- Extract and refactor static files from prototype
- Update WebSocket connection logic
- Test browser compatibility
- Implement language switching UI

#### Day 5: Chat Agent Integration
- Re-implement equivalent chat agent logic (clean room implementation)
- Do NOT import/copy directly from RXRefillCampaign_Alt1
- Set up Qdrant client connection
- Configure OpenAI API integration
- Test RAG retrieval pipeline

### Week 2: WebSocket & Production Readiness

#### Day 6-7: WebSocket Implementation
- Implement WebSocket endpoint
- Add message queuing and delivery
- Handle connection lifecycle
- Test with multiple concurrent connections

#### Day 8-9: Testing & Optimization
- Create comprehensive test suite
- Performance testing with 100+ concurrent users
- Optimize response times
- Fix identified bugs

#### Day 10: Deployment
- Configure Render.com deployment
- Set up GitHub Actions CI/CD
- Deploy to staging environment
- Production deployment and verification

## Deployment Architecture

### Directory Structure
```
KineticChat_WebUI/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   ├── __init__.py
│   │   ├── chat.py            # WebSocket endpoint
│   │   ├── health.py          # Health/metrics endpoints
│   │   └── static.py          # Static file serving
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py           # Chat agent logic
│   │   ├── deterministic.py   # Pattern matching
│   │   └── language.py        # Language detection
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic models
│   └── utils/
│       ├── __init__.py
│       ├── logging.py         # Structured logging
│       └── metrics.py         # Metrics collection
├── static/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   └── barcode.PNG
├── tests/
│   ├── __init__.py
│   ├── test_chat.py
│   ├── test_agent.py
│   └── test_websocket.py
├── scripts/
│   ├── setup.sh
│   └── test_load.py
├── requirements.txt
├── .env.example
├── README.md
└── render.yaml                # Render deployment config
```

### Environments
- **Development**: Local with hot reload
- **Staging**: Render.com free tier
- **Production**: Render.com paid tier with autoscaling

### Environment Variables
```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...

# Qdrant Configuration  
QDRANT_URL=https://...
QDRANT_API_KEY=...
QDRANT_COLLECTION_NAME=kroger_health_rag_v3  # Do not hardcode
EMBEDDING_MODEL=all-mpnet-base-v2  # Do not hardcode

# Application Settings
APP_ENV=production
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourdomain.com
RATE_LIMIT_PER_MINUTE=100

# Optional Database (for persistence)
DATABASE_URL=postgresql://...
```

## Performance Considerations

### Optimization Targets (SLIs with percentiles)
- WebSocket connection time: p50 < 100ms, p95 < 500ms (after warmup)
- Chat response time: p50 < 2s, p95 < 4s  
- RAG retrieval: p50 < 500ms, p95 < 1s
- Concurrent users: 100+ without degradation
- Memory usage: < 512MB per instance
- Note: Cold starts on Render.com may exceed targets initially

### Caching Strategy
- Static assets: Browser cache with versioning
- RAG results: 15-minute in-memory cache
- Common queries: Deterministic handler bypass

### Scaling Strategy
- Initial: Single Render.com instance
- Growth: Horizontal scaling with Render autoscale
- Future: WebSocket sticky sessions via load balancer

## Monitoring & Observability

### Logging
- Application logs: Structured JSON with correlation IDs
- Error tracking: Captured with stack traces
- Performance logs: Response times per endpoint

### Metrics
- Chat response times (p50, p95, p99)
- WebSocket connection count
- Error rates by type
- Language distribution
- RAG retrieval performance

### Health Checks
```json
GET /api/v1/health
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600,
  "checks": {
    "openai": "ok",
    "qdrant": "ok",
    "memory": "ok"
  }
}
```

## Cost Analysis

### Initial Deployment (Render.com Free Tier)
- Hosting: $0/month (with limitations)
- OpenAI API: ~$20/month (estimated)
- Qdrant: Using existing instance
- **Total**: ~$20/month

### Production Scale (100+ concurrent users)
- Render.com Starter: $7/month
- OpenAI API: ~$100/month
- Qdrant: Existing instance
- **Total**: ~$107/month

## Risk Mitigation

### Technical Risks
1. **Risk**: WebSocket connection drops
   - **Mitigation**: Automatic reconnection with exponential backoff

2. **Risk**: OpenAI API rate limits
   - **Mitigation**: Request queuing and caching layer

3. **Risk**: Memory leaks from long-running connections
   - **Mitigation**: Connection timeout and cleanup routines

### Operational Risks
1. **Risk**: Render.com free tier limitations
   - **Mitigation**: Clear upgrade path to paid tier

2. **Risk**: RAG quality degradation
   - **Mitigation**: Regular testing of retrieval accuracy

## MVP Scope Boundaries

### In Scope
- All existing chat functionality from static/ folder
- English/Spanish language support
- WebSocket real-time communication
- Deterministic responses for common queries
- RAG-based responses
- Basic health monitoring

### Out of Scope (Deferred to Phase 3+)
- User authentication
- Conversation persistence
- Advanced analytics
- Multi-tenant support
- Custom branding
- Mobile app
- SMS integration

## Testing Strategy

### Test Coverage Requirements
- Unit tests: Core business logic (80% coverage)
- Integration tests: API endpoints
- WebSocket tests: Connection and messaging
- Load tests: 100 concurrent users
- Language tests: EN/ES switching

### Test Data
- Mock Qdrant responses for unit tests
- Synthetic chat conversations
- Performance test scripts

## Next Steps
After review and approval:
1. Run `/sanity` command to verify this design is practical
2. Begin implementation following the development plan
3. Set up GitHub repository and CI/CD pipeline
4. Start with Week 1, Day 1-2 tasks