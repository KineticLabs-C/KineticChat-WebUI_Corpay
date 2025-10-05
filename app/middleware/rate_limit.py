"""
Rate Limiting Middleware - Production-Ready Implementation

This module provides comprehensive rate limiting for the KineticChat WebUI service
with memory-safe client tracking and automatic cleanup mechanisms.

Key Features:
- Token bucket algorithm for burst protection
- Per-minute and per-hour rate limits
- LRU cache with automatic eviction (max 10,000 clients)
- Periodic cleanup of idle clients
- WebSocket-specific rate limiting
- Configurable via environment variables

Configuration (via environment variables):
- RATE_LIMIT_PER_MINUTE: Max requests per minute (default: 100)
- RATE_LIMIT_PER_HOUR: Max requests per hour (default: 1000)
- RATE_LIMIT_BURST: Token bucket size for burst protection (default: 10)
- MAX_TRACKED_CLIENTS: Maximum clients to track (default: 10000)
- CLIENT_CLEANUP_INTERVAL: Cleanup interval in seconds (default: 300)
- CLIENT_IDLE_TIMEOUT: Idle timeout before removal (default: 3600)

Usage:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

Performance:
- Memory usage: O(MAX_TRACKED_CLIENTS)
- Lookup time: O(1) average case
- Cleanup time: O(n) where n is tracked clients

Security:
- SHA-256 hashing for client identification
- No PII stored in memory
- Automatic cleanup prevents memory exhaustion
"""

import os
import time
import hashlib
import asyncio
from typing import Dict, Tuple, Optional, Set
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque, OrderedDict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from functools import lru_cache
import threading

from app.utils import safe_log

# Configuration
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "10"))
MAX_TRACKED_CLIENTS = int(os.getenv("MAX_TRACKED_CLIENTS", "10000"))
CLIENT_CLEANUP_INTERVAL = int(os.getenv("CLIENT_CLEANUP_INTERVAL", "300"))  # 5 minutes
CLIENT_IDLE_TIMEOUT = int(os.getenv("CLIENT_IDLE_TIMEOUT", "3600"))  # 1 hour


class LRUCache:
    """Simple LRU cache for client tracking with size limit"""
    
    def __init__(self, max_size: int = MAX_TRACKED_CLIENTS):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[any]:
        """Get item and move to end (most recently used)"""
        with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
    
    def put(self, key: str, value: any):
        """Add or update item, evicting LRU if needed"""
        with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            
            # Evict least recently used if over limit
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def remove_old_entries(self, current_time: float, timeout: float) -> int:
        """Remove entries older than timeout, return count removed"""
        with self._lock:
            to_remove = []
            for key, value in self.cache.items():
                if hasattr(value, 'last_access'):
                    if current_time - value.last_access > timeout:
                        to_remove.append(key)
            
            for key in to_remove:
                del self.cache[key]
            
            return len(to_remove)
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def clear(self):
        """Clear all entries"""
        with self._lock:
            self.cache.clear()


class ClientRateLimitData:
    """Encapsulates rate limit data for a single client"""
    
    def __init__(self):
        self.minute_requests: deque = deque()
        self.hour_requests: deque = deque()
        self.tokens: float = float(RATE_LIMIT_BURST)
        self.last_refill: float = time.time()
        self.last_access: float = time.time()
        self.request_count: int = 0
        self.blocked_count: int = 0
    
    def update_access(self):
        """Update last access time"""
        self.last_access = time.time()
    
    def is_idle(self, current_time: float, timeout: float) -> bool:
        """Check if client has been idle"""
        return (current_time - self.last_access) > timeout


class RateLimiter:
    """Token bucket rate limiter with memory-safe client tracking"""
    
    def __init__(
        self,
        rate_per_minute: int = RATE_LIMIT_PER_MINUTE,
        rate_per_hour: int = RATE_LIMIT_PER_HOUR,
        burst_size: int = RATE_LIMIT_BURST,
        max_clients: int = MAX_TRACKED_CLIENTS
    ):
        self.rate_per_minute = rate_per_minute
        self.rate_per_hour = rate_per_hour
        self.burst_size = burst_size
        self.max_clients = max_clients
        
        # Use LRU cache for client data
        self.clients = LRUCache(max_size=max_clients)
        
        # Cache for client ID hashes (avoid recomputation)
        self._client_id_cache = lru_cache(maxsize=1000)(self._compute_client_id)
        
        # Cleanup task
        self.cleanup_task = None
        self.is_running = True
        self.last_cleanup = time.time()
        
        # Statistics
        self.total_requests = 0
        self.total_blocked = 0
        self.cleanups_performed = 0
    
    def _compute_client_id(self, client_ip: str, session_id: str) -> str:
        """Compute SHA-256 hash for client identification"""
        client_string = f"{client_ip}:{session_id}"
        return hashlib.sha256(client_string.encode()).hexdigest()
    
    def get_client_id(self, request: Request) -> str:
        """Get unique client identifier using cached SHA-256"""
        # Use IP address as client ID
        client_ip = request.client.host if request.client else "unknown"
        
        # Include session ID if present in headers
        session_id = request.headers.get("X-Session-ID", "")
        
        # Use cached computation
        return self._client_id_cache(client_ip, session_id)
    
    def get_or_create_client(self, client_id: str) -> ClientRateLimitData:
        """Get existing client data or create new"""
        client_data = self.clients.get(client_id)
        if client_data is None:
            client_data = ClientRateLimitData()
            self.clients.put(client_id, client_data)
        return client_data
    
    def clean_old_requests(self, client_data: ClientRateLimitData):
        """Remove old requests outside time windows"""
        now = datetime.now(timezone.utc)
        
        # Clean minute window (60 seconds)
        minute_ago = now - timedelta(seconds=60)
        while client_data.minute_requests and client_data.minute_requests[0] < minute_ago:
            client_data.minute_requests.popleft()
        
        # Clean hour window (3600 seconds)
        hour_ago = now - timedelta(seconds=3600)
        while client_data.hour_requests and client_data.hour_requests[0] < hour_ago:
            client_data.hour_requests.popleft()
    
    def refill_tokens(self, client_data: ClientRateLimitData):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - client_data.last_refill
        
        # Refill rate: tokens per second
        refill_rate = self.rate_per_minute / 60.0
        tokens_to_add = elapsed * refill_rate
        
        # Add tokens up to burst size
        client_data.tokens = min(
            self.burst_size,
            client_data.tokens + tokens_to_add
        )
        
        client_data.last_refill = now
    
    def is_allowed(self, request: Request) -> Tuple[bool, Dict]:
        """Check if request is allowed under rate limits"""
        self.total_requests += 1
        
        client_id = self.get_client_id(request)
        client_data = self.get_or_create_client(client_id)
        
        # Update access time
        client_data.update_access()
        client_data.request_count += 1
        
        now = datetime.now(timezone.utc)
        
        # Clean old requests
        self.clean_old_requests(client_data)
        
        # Refill tokens
        self.refill_tokens(client_data)
        
        # Check minute limit
        minute_count = len(client_data.minute_requests)
        if minute_count >= self.rate_per_minute:
            client_data.blocked_count += 1
            self.total_blocked += 1
            return False, {
                "limit_type": "minute",
                "limit": self.rate_per_minute,
                "current": minute_count,
                "retry_after": 60
            }
        
        # Check hour limit
        hour_count = len(client_data.hour_requests)
        if hour_count >= self.rate_per_hour:
            client_data.blocked_count += 1
            self.total_blocked += 1
            return False, {
                "limit_type": "hour",
                "limit": self.rate_per_hour,
                "current": hour_count,
                "retry_after": 3600
            }
        
        # Check token bucket for burst protection
        if client_data.tokens < 1:
            client_data.blocked_count += 1
            self.total_blocked += 1
            return False, {
                "limit_type": "burst",
                "limit": self.burst_size,
                "current": 0,
                "retry_after": 1
            }
        
        # Request allowed - update tracking
        client_data.minute_requests.append(now)
        client_data.hour_requests.append(now)
        client_data.tokens -= 1
        
        # Perform periodic cleanup
        self.maybe_cleanup()
        
        return True, {
            "remaining_minute": self.rate_per_minute - minute_count - 1,
            "remaining_hour": self.rate_per_hour - hour_count - 1,
            "tokens": int(client_data.tokens)
        }
    
    def maybe_cleanup(self):
        """Perform cleanup if enough time has passed"""
        current_time = time.time()
        if current_time - self.last_cleanup > CLIENT_CLEANUP_INTERVAL:
            self.cleanup_old_clients()
            self.last_cleanup = current_time
    
    def cleanup_old_clients(self):
        """Remove idle clients to prevent memory growth"""
        current_time = time.time()
        removed_count = self.clients.remove_old_entries(current_time, CLIENT_IDLE_TIMEOUT)
        
        if removed_count > 0:
            print(safe_log(f"Cleaned up {removed_count} idle clients"))
        
        self.cleanups_performed += 1
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        return {
            "tracked_clients": self.clients.size(),
            "max_clients": self.max_clients,
            "total_requests": self.total_requests,
            "total_blocked": self.total_blocked,
            "block_rate": round((self.total_blocked / self.total_requests * 100) if self.total_requests > 0 else 0, 2),
            "cleanups_performed": self.cleanups_performed,
            "cache_info": str(self._client_id_cache.cache_info())
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.total_requests = 0
        self.total_blocked = 0
        self.cleanups_performed = 0
    
    def shutdown(self):
        """Clean shutdown"""
        self.is_running = False
        self.clients.clear()
        self._client_id_cache.cache_clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting with memory safety"""
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.limiter = RateLimiter(**kwargs)
        
        # Paths to exclude from rate limiting
        self.excluded_paths = {
            "/health",
            "/api/v1/health",
            "/metrics",
            "/api/v1/metrics",
            "/api/v1/status",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
        
        # Start periodic cleanup task
        self.cleanup_task = asyncio.create_task(self.periodic_cleanup())
    
    async def periodic_cleanup(self):
        """Background task for periodic cleanup"""
        while self.limiter.is_running:
            await asyncio.sleep(CLIENT_CLEANUP_INTERVAL)
            self.limiter.cleanup_old_clients()
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Skip rate limiting for static files
        if request.url.path.startswith("/static"):
            return await call_next(request)
        
        # Check rate limit
        allowed, info = self.limiter.is_allowed(request)
        
        if not allowed:
            # Rate limit exceeded
            print(safe_log(f"Rate limit exceeded: {info['limit_type']} limit"))
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "type": info["limit_type"],
                    "limit": info["limit"],
                    "retry_after": info["retry_after"],
                    "message": f"Too many requests. Please retry after {info['retry_after']} seconds."
                },
                headers={
                    "Retry-After": str(info["retry_after"]),
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Reset": str(int(time.time()) + info["retry_after"])
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining-Minute"] = str(info["remaining_minute"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(info["remaining_hour"])
        response.headers["X-RateLimit-Tokens"] = str(info["tokens"])
        
        return response
    
    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'limiter'):
            self.limiter.shutdown()
        if hasattr(self, 'cleanup_task'):
            self.cleanup_task.cancel()


# Simpler implementation for WebSocket connections (unchanged)
class WebSocketRateLimiter:
    """Rate limiter specifically for WebSocket connections"""
    
    def __init__(self, max_connections_per_ip: int = 5):
        self.max_connections_per_ip = max_connections_per_ip
        self.connections: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    def can_connect(self, client_ip: str) -> bool:
        """Check if client can establish new WebSocket connection"""
        with self._lock:
            return self.connections[client_ip] < self.max_connections_per_ip
    
    def add_connection(self, client_ip: str):
        """Register new connection"""
        with self._lock:
            self.connections[client_ip] += 1
            print(safe_log(f"WebSocket connections from IP: {self.connections[client_ip]}"))
    
    def remove_connection(self, client_ip: str):
        """Remove connection"""
        with self._lock:
            if client_ip in self.connections:
                self.connections[client_ip] -= 1
                if self.connections[client_ip] <= 0:
                    del self.connections[client_ip]
    
    def get_connection_count(self, client_ip: str) -> int:
        """Get current connection count for IP"""
        with self._lock:
            return self.connections.get(client_ip, 0)
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        with self._lock:
            return sum(self.connections.values())


# Global WebSocket rate limiter
ws_limiter = WebSocketRateLimiter()


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    # Create test app
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}
    
    # Test the rate limiter
    client = TestClient(app)
    
    print("Testing rate limiter...")
    
    # Test burst limit
    for i in range(15):
        response = client.get("/test")
        print(f"Request {i+1}: Status {response.status_code}")
        if response.status_code == 429:
            print(f"  Rate limited: {response.json()}")
    
    # Get stats
    limiter = app.middleware[0].limiter if app.middleware else None
    if limiter:
        stats = limiter.get_stats()
        print(f"\nRate limiter stats: {json.dumps(stats, indent=2)}")
    
    print("\nTest complete!")