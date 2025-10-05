# KineticChat WebUI Service - DEMO VERSION

**⚠️ DEMO CONFIGURATION**: This instance is configured for testing with a lighter, faster embedding model (all-MiniLM-L6-v2) and generalized pharmacy content. Not for production use.

A standalone, production-ready web chat service for healthcare interactions with HIPAA-compliant real-time messaging, bilingual support, and RAG-powered responses.

## Features

- 🔒 **HIPAA Compliant**: PHI scrubbing, secure logging, no PII storage
- 💬 **Real-time Chat**: WebSocket with SSE fallback for universal compatibility
- 🌐 **Bilingual**: English/Spanish auto-detection and switching
- 🤖 **AI-Powered**: RAG-based responses using OpenAI and Qdrant
- ⚡ **High Performance**: Handles 100+ concurrent users
- 🔄 **Backward Compatible**: Preserves all legacy endpoints

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (via Supabase) - Database schema will auto-create on first run
- Qdrant Vector Database with pre-populated collection (see RAG Data Setup below)
- OpenAI API Key for chat completions

#### RAG Data Setup

**IMPORTANT**: This service requires a pre-populated Qdrant collection with healthcare content. The RAG functionality expects:

- **Collection Name**: `kroger_health_rag_v3` (configurable via `QDRANT_COLLECTION_NAME`)
- **Vector Dimensions**: Must match the embedding model (384 for `all-mpnet-base-v2`)
- **Required Content**: Healthcare FAQs, service information, pharmacy details

If you don't have an existing Qdrant instance with this data:
1. Use an existing shared instance provided by your organization, OR
2. Set up your own Qdrant instance and populate it with relevant healthcare content
3. The data ingestion pipeline is a separate concern not included in this WebUI service

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd KineticChat_WebUI
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the application:
```bash
uvicorn app.main:app --reload
```

The service will be available at `http://localhost:8000`

## Project Structure

```
KineticChat_WebUI/
├── app/               # Application code
│   ├── api/          # API endpoints
│   ├── core/         # Core business logic
│   ├── models/       # Data models
│   └── utils/        # Utilities (PHI scrubbing, etc.)
├── static/           # Frontend assets (HTML, CSS, JS)
├── templates/        # SMS notification templates (reserved for future SMS service)
├── database/         # Database schema
├── tests/            # Test files
└── docs/            # Documentation
```

**Note**: The `templates/` directory contains SMS notification templates (en.json, es.json) that are preserved for the future KineticChat SMS service. The WebUI service uses the DeterministicHandler and RAG for chat responses, not these templates.

## API Endpoints

### Legacy Endpoints (Backward Compatibility)
- `GET /health` - Health check
- `GET /metrics` - Service metrics
- `GET /static/{file}` - Static file serving

### Versioned Endpoints
- `GET /api/v1/health` - Health check
- `GET /api/v1/metrics` - Service metrics
- `GET /api/v1/status` - Detailed status
- `WS /api/v1/chat` - WebSocket chat
- `GET /api/v1/chat/sse` - SSE fallback
- `POST /api/v1/chat/feedback` - Submit feedback

## Configuration

All configuration is done through environment variables. See `.env.example` for required variables.

### Required Environment Variables

- `OPENAI_API_KEY` - OpenAI API key for chat completions
- `QDRANT_URL` - Qdrant instance URL
- `QDRANT_API_KEY` - Qdrant API key
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase anonymous key

## Development

### Running Tests

```bash
# Run smoke tests (MVP)
pytest tests/test_smoke.py

# Run with coverage (post-MVP)
pytest --cov=app tests/
```

### Load Testing

```bash
python scripts/load_test.py --connections 100
```

### PHI Compliance Check

```bash
# Check logs for PHI/PII
grep -E "(SSN|DOB|MRN|patient)" logs/*.log
```

## Deployment

### Manual Deployment to Render.com

1. Create a new Web Service on Render.com
2. Connect your GitHub repository
3. Set environment variables in Render dashboard
4. Deploy with the following settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Production Checklist

- [ ] All environment variables set
- [ ] Database connection verified
- [ ] Health endpoints responding
- [ ] WebSocket and SSE endpoints working
- [ ] Language switching functional
- [ ] Rate limiting active
- [ ] PHI scrubbing verified

## Security

This application implements multiple security measures:

- **PHI Scrubbing**: All logs are sanitized before writing
- **Rate Limiting**: 100 requests/minute per IP

## Troubleshooting

### Common Issues and Solutions

#### Database Connection Fails
- **Issue**: "Database initialization failed"
- **Solution**: 
  1. Verify Supabase credentials in `.env`
  2. Check network connectivity to Supabase
  3. Ensure database schema exists (will auto-create on first run)

#### RAG Responses Not Working
- **Issue**: Empty or generic responses from chat
- **Solution**:
  1. Verify Qdrant connection settings
  2. Confirm collection `kroger_health_rag_v3` exists
  3. Check collection has healthcare content vectors
  4. Verify OpenAI API key is valid

#### Frontend Not Loading
- **Issue**: Blank page or 404 errors
- **Solution**:
  1. Ensure server is running on correct port
  2. Check static files exist in `static/` directory
  3. Clear browser cache (add `?v=X` to URLs during development)

#### Language Switching Issues
- **Issue**: Responses always in English
- **Solution**:
  1. Check language parameter is being sent ('en' or 'es')
  2. Verify DeterministicHandler has both language mappings
  3. Ensure frontend is setting language correctly

#### High Response Times
- **Issue**: Responses take > 3 seconds
- **Solution**:
  1. Check OpenAI API latency
  2. Verify Qdrant query performance
  3. Consider using deterministic responses for common queries
  4. Note: First request after cold start will be slower

## Additional Security Features

- **Input Validation**: Pydantic models for all inputs
- **CORS**: Configured for specific origins only
- **No Authentication**: Stateless/anonymous operation
- **HIPAA Compliant**: Full compliance from Phase 1

## Contributing

This is a clean room implementation. Do not copy code directly from the original prototype.

## License

[License information here]

## Support

For issues or questions, please contact [contact information].

---
*Built with FastAPI, OpenAI, and Qdrant for secure healthcare communications.*