"""
KineticChat WebUI Service - Main Application
A production-ready chat service with HIPAA-compliant real-time messaging
"""

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import sys
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Version and metadata
API_VERSION = "1.0.0"
SERVICE_NAME = "KineticChat WebUI"
SERVICE_START_TIME = datetime.now(timezone.utc)

# Environment configuration
ENVIRONMENT = os.getenv("APP_ENV", "development")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events
    """
    # Startup
    print(f"{SERVICE_NAME} v{API_VERSION} starting...")
    print(f"Environment: {ENVIRONMENT}")
    print(f"Started at: {SERVICE_START_TIME.isoformat()}")
    
    # Initialize RAG profile configuration
    from config.rag_profiles import get_active_profile
    from app.utils import safe_log

    # Load active RAG profile
    try:
        active_profile = get_active_profile()
        print(safe_log(f"RAG Profile loaded: {active_profile.company_name}"))
        print(safe_log(f"Collection: {active_profile.collection_name}"))
    except Exception as e:
        print(safe_log(f"WARNING: Could not load RAG profile: {e}"))

    # Pre-initialize the chat agent to avoid first-request delay
    from app.core.finance.agent import get_agent
    try:
        agent = await get_agent()
        print(safe_log("Chat agent pre-initialized successfully"))
    except Exception as e:
        print(safe_log(f"WARNING: Could not pre-initialize agent: {e}"))
    
    # TODO: Initialize Qdrant connection (Phase 3)
    # TODO: Load templates into memory
    
    yield
    
    # Shutdown
    print(f"{SERVICE_NAME} shutting down...")
    # TODO: Clean up other resources

# Create FastAPI application
app = FastAPI(
    title=SERVICE_NAME,
    version=API_VERSION,
    description="Standalone web chat service for healthcare interactions with HIPAA-compliant messaging",
    docs_url="/api/docs" if ENVIRONMENT == "development" else None,
    redoc_url="/api/redoc" if ENVIRONMENT == "development" else None,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Response-Time"]
)

# Add rate limiting middleware
from app.middleware.rate_limit import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# Add metrics collection middleware
from app.core.metrics import MetricsMiddleware, metrics
app.add_middleware(MetricsMiddleware)

# Add request size limit middleware (10MB max)
from starlette.middleware.base import BaseHTTPMiddleware

class ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent abuse"""
    def __init__(self, app, max_content_size: int = 10_000_000):  # 10MB default
        super().__init__(app)
        self.max_content_size = max_content_size
    
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > self.max_content_size:
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request entity too large", "max_size_mb": self.max_content_size / 1_000_000}
                )
        return await call_next(request)

app.add_middleware(ContentSizeLimitMiddleware, max_content_size=10_000_000)

# Request ID middleware for tracking
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for tracking and debugging"""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Response time middleware
@app.middleware("http")
async def add_response_time(request: Request, call_next):
    """Track and report response time"""
    import time
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Response-Time"] = f"{process_time:.3f}"
    return response

# ============================================================================
# HEALTH ENDPOINTS - Both Legacy and Versioned for Backward Compatibility
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check_legacy() -> Dict[str, Any]:
    """
    Legacy health check endpoint for backward compatibility
    """
    uptime_seconds = (datetime.now(timezone.utc) - SERVICE_START_TIME).total_seconds()
    
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": API_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "environment": ENVIRONMENT
    }

@app.get("/api/v1/health", tags=["Health"])
async def health_check_v1() -> Dict[str, Any]:
    """
    Versioned health check endpoint with extended information
    """
    uptime_seconds = (datetime.now(timezone.utc) - SERVICE_START_TIME).total_seconds()
    
    # Check RAG profile configuration
    rag_status = "unhealthy"
    try:
        from config.rag_profiles import get_active_profile
        active_profile = get_active_profile()
        rag_status = "healthy" if active_profile else "unhealthy"
    except Exception:
        rag_status = "unhealthy"
    
    # Check Qdrant connectivity
    qdrant_status = "unhealthy"
    try:
        from app.core.finance.agent import chat_agent
        if chat_agent.qdrant_client:
            # Try to get collection info as a health check
            collections = chat_agent.qdrant_client.get_collections()
            qdrant_status = "healthy" if collections else "unhealthy"
    except Exception:
        qdrant_status = "unhealthy"
    
    # Check OpenAI connectivity
    openai_status = "unhealthy"
    try:
        from app.core.finance.agent import chat_agent
        if chat_agent.openai_client:
            openai_status = "healthy"
    except Exception:
        openai_status = "unhealthy"
    
    # Overall status
    all_healthy = (rag_status == "healthy" and qdrant_status == "healthy" and openai_status == "healthy")

    health_status = {
        "status": "healthy" if all_healthy else "degraded",
        "service": SERVICE_NAME,
        "version": API_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "environment": ENVIRONMENT,
        "checks": {
            "api": "operational",
            "rag_config": rag_status,
            "openai": openai_status,
            "qdrant": qdrant_status
        }
    }
    
    return health_status

@app.get("/metrics", tags=["Monitoring"])
async def metrics_legacy() -> Dict[str, Any]:
    """
    Legacy metrics endpoint for monitoring
    """
    stats = metrics.get_response_time_stats()
    return {
        "service": SERVICE_NAME,
        "version": API_VERSION,
        "requests_total": metrics.total_requests,
        "active_connections": metrics.active_requests,
        "response_time_avg_ms": round(stats["avg"], 2),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/v1/metrics", tags=["Monitoring"])
async def metrics_v1() -> Dict[str, Any]:
    """
    Versioned metrics endpoint with detailed statistics
    """
    # Get comprehensive metrics from collector
    return metrics.get_metrics_summary()

@app.get("/api/v1/status", tags=["Monitoring"])
async def status_check() -> Dict[str, Any]:
    """
    Detailed status endpoint for comprehensive health monitoring
    """
    return {
        "service": SERVICE_NAME,
        "version": API_VERSION,
        "status": "operational",
        "components": {
            "api": {
                "status": "operational",
                "response_time_ms": 0
            },
            "rag_config": {
                "status": "operational",
                "profile": os.getenv("ACTIVE_RAG_PROFILE", "finance")
            },
            "websocket": {
                "status": "pending",
                "active_connections": 0
            },
            "rag_engine": {
                "status": "pending",
                "vector_db": "qdrant",
                "collection": os.getenv("QDRANT_COLLECTION_NAME", "kroger_health_rag_v3")
            }
        },
        "configuration": {
            "environment": ENVIRONMENT,
            "cors_enabled": True,
            "rate_limiting": f"{RATE_LIMIT_PER_MINUTE} req/min",
            "phi_scrubbing": "enabled"  # Always enabled from Phase 1
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint providing service information"""
    return {
        "service": SERVICE_NAME,
        "version": API_VERSION,
        "status": "operational",
        "documentation": "/api/docs" if ENVIRONMENT == "development" else None,
        "health": "/health",
        "health_v1": "/api/v1/health",
        "message": "KineticChat WebUI Service - Ready for healthcare communications"
    }

# ============================================================================
# CHAT ENDPOINTS (WebSocket and SSE)
# ============================================================================

# Import chat endpoints
# WebSocket and SSE removed - using HTTP POST only for enterprise compliance
# from app.api.websocket import websocket_endpoint, get_websocket_stats
# from app.api.sse import sse_chat_simple, sse_health_endpoint

# WebSocket and SSE endpoints removed - using HTTP POST only for enterprise compliance
# All chat functionality is now handled through the /api/kroger-chat HTTP POST endpoint

# # WebSocket endpoint for real-time chat (REMOVED)
# from fastapi import WebSocket
# @app.websocket("/api/v1/chat")
# async def chat_websocket(websocket: WebSocket, session_id: str = None, language: str = "en"):
#     """WebSocket endpoint for real-time chat"""
#     await websocket_endpoint(websocket, session_id, language)

# # SSE endpoint as fallback (REMOVED)
# @app.get("/api/v1/chat/sse", tags=["Chat"])
# async def chat_sse(request: Request, message: str, session_id: str = None, language: str = "en"):
#     """Server-Sent Events endpoint for chat (WebSocket fallback)"""
#     return await sse_chat_simple(request, message, session_id, language)

# SSE health check (kept for compatibility)
@app.get("/api/v1/chat/sse/health", tags=["Chat"])
async def sse_health():
    """SSE connection health check (SSE disabled)"""
    return {"status": "disabled", "message": "SSE is disabled in favor of HTTP POST for enterprise compliance"}

# WebSocket stats endpoint (kept for compatibility)
@app.get("/api/v1/chat/stats", tags=["Chat"])
async def websocket_stats():
    """Get WebSocket connection statistics (WebSocket disabled)"""
    return {"status": "disabled", "active_connections": 0, "message": "WebSocket is disabled"}

# ============================================================================
# LEGACY ENDPOINT COMPATIBILITY
# ============================================================================

# Legacy chat endpoint for backward compatibility with existing frontend
@app.post("/api/kroger-chat", tags=["Chat", "Legacy"])
async def legacy_chat_endpoint(request: Request):
    """
    Legacy chat endpoint - redirects to modern WebSocket/SSE endpoints
    Maintains compatibility with existing frontend code
    
    Note: This is a compatibility layer. New implementations should use:
    - WebSocket: /api/v1/chat
    - SSE: /api/v1/chat/sse
    """
    # Parse request body (matching original API format)
    try:
        body = await request.json()
        # Accept both 'query' (original) and 'message' (new) for compatibility
        message = body.get("query") or body.get("message") or ""
        session_id = body.get("session_id", None)
        language = body.get("language", "en")
        
        # Validate message is not empty
        if not message.strip():
            return JSONResponse(
                status_code=400,
                content={"error": "No message provided", "status": "error"}
            )
    except:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid request format", "status": "error"}
        )
    
    # For HTTP POST, use SSE-style response
    from app.core.finance.agent import get_agent
    agent = await get_agent()
    
    # Generate response synchronously
    response_parts = []
    async for chunk in agent.process_message(message, session_id or "legacy", language):
        response_parts.append(chunk)
    
    full_response = "".join(response_parts)
    
    return JSONResponse(
        content={
            "response": full_response,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"  # Add for compatibility
        }
    )

@app.post("/api/corpay-chat", tags=["Chat", "Financial"])
async def corpay_chat_endpoint(request: Request):
    """
    Corpay Financial chat endpoint - primary chat interface for financial services
    Handles corporate payment, card, and financial solution queries
    """
    # Parse request body (matching original API format)
    try:
        body = await request.json()
        # Accept both 'query' (original) and 'message' (new) for compatibility
        message = body.get("query") or body.get("message") or ""
        session_id = body.get("session_id", None)
        language = body.get("language", "en")
        
        # Validate message is not empty
        if not message.strip():
            return JSONResponse(
                status_code=400,
                content={"error": "No message provided", "status": "error"}
            )
    except:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid request format", "status": "error"}
        )
    
    # For HTTP POST, use SSE-style response
    from app.core.finance.agent import get_agent
    agent = await get_agent()
    
    # Generate response synchronously
    response_parts = []
    async for chunk in agent.process_message(message, session_id or "corpay", language):
        response_parts.append(chunk)
    
    full_response = "".join(response_parts)
    
    return JSONResponse(
        content={
            "response": full_response,
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }
    )

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"The requested resource {request.url.path} was not found",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler with PHI-safe error messages"""
    # Note: Never log actual error details that might contain PHI
    request_id = getattr(request.state, "request_id", "unknown")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An internal error occurred. Please try again later.",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

# ============================================================================
# STATIC FILE SERVING
# ============================================================================

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================================
# FUTURE ENDPOINTS
# ============================================================================

# Chat feedback endpoint (Phase 4)
@app.post("/api/v1/chat/feedback", tags=["Chat"])
async def chat_feedback(request: Request):
    """
    Accept user feedback on chat responses
    Used for quality improvement and HIPAA audit trail
    """
    try:
        body = await request.json()
        feedback = {
            "session_id": body.get("session_id"),
            "message_id": body.get("message_id"),
            "rating": body.get("rating"),
            "comment": body.get("comment"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        # TODO: Store feedback in external system (not implemented yet)
        session_str = str(feedback.get('session_id', 'unknown'))
        print(safe_log(f"Feedback received for session {session_str[:8]}..."))
        return JSONResponse({"status": "accepted", "feedback_id": str(uuid.uuid4())})
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid feedback format"}
        )

# TODO: Phase 4 - Legacy API compatibility endpoints

if __name__ == "__main__":
    import uvicorn
    
    # Development server configuration
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=ENVIRONMENT == "development",
        log_level="info" if ENVIRONMENT == "production" else "debug"
    )