"""
Real-time metrics collection for KineticChat WebUI
Tracks request counts, response times, and system health
"""

import time
from typing import Dict, Any
from datetime import datetime, timezone
from collections import deque
import asyncio

class MetricsCollector:
    """Collects and tracks application metrics"""
    
    def __init__(self):
        # Request counters
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        # Response time tracking (keep last 1000 for percentiles)
        self.response_times = deque(maxlen=1000)
        
        # Endpoint-specific counters
        self.endpoint_counts = {}
        
        # Language counters
        self.language_counts = {"en": 0, "es": 0, "other": 0}
        
        # Error tracking
        self.error_counts = {}
        
        # Start time for uptime calculation
        self.start_time = time.time()
        
        # Current active requests
        self.active_requests = 0
        
        # Rate limiting hits
        self.rate_limit_hits = 0
        
    def record_request_start(self) -> float:
        """Record the start of a request"""
        self.active_requests += 1
        return time.time()
    
    def record_request_end(self, start_time: float, endpoint: str, status_code: int, language: str = None):
        """Record the completion of a request"""
        # Calculate duration
        duration = (time.time() - start_time) * 1000  # Convert to ms
        self.response_times.append(duration)
        
        # Update counters
        self.total_requests += 1
        self.active_requests = max(0, self.active_requests - 1)
        
        if 200 <= status_code < 300:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            
        # Track endpoint usage
        if endpoint not in self.endpoint_counts:
            self.endpoint_counts[endpoint] = 0
        self.endpoint_counts[endpoint] += 1
        
        # Track language usage
        if language:
            if language in self.language_counts:
                self.language_counts[language] += 1
            else:
                self.language_counts["other"] += 1
    
    def record_error(self, error_type: str):
        """Record an error occurrence"""
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
    
    def record_rate_limit_hit(self):
        """Record a rate limit hit"""
        self.rate_limit_hits += 1
    
    def get_uptime_seconds(self) -> float:
        """Get uptime in seconds"""
        return time.time() - self.start_time
    
    def get_response_time_stats(self) -> Dict[str, float]:
        """Calculate response time statistics"""
        if not self.response_times:
            return {
                "avg": 0,
                "min": 0,
                "max": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0
            }
        
        sorted_times = sorted(self.response_times)
        count = len(sorted_times)
        
        return {
            "avg": sum(sorted_times) / count,
            "min": sorted_times[0],
            "max": sorted_times[-1],
            "p50": sorted_times[count // 2],
            "p95": sorted_times[int(count * 0.95)] if count > 20 else sorted_times[-1],
            "p99": sorted_times[int(count * 0.99)] if count > 100 else sorted_times[-1]
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        uptime = self.get_uptime_seconds()
        response_stats = self.get_response_time_stats()
        
        # Calculate rates
        requests_per_second = self.total_requests / uptime if uptime > 0 else 0
        success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 100
        
        return {
            "service": "kroger-health-chat",
            "version": "1.0.0",
            "uptime_seconds": round(uptime, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            
            # Request metrics
            "requests": {
                "total": self.total_requests,
                "successful": self.successful_requests,
                "failed": self.failed_requests,
                "active": self.active_requests,
                "rate_per_second": round(requests_per_second, 2),
                "success_rate": round(success_rate, 2)
            },
            
            # Response time metrics
            "response_times_ms": {
                "average": round(response_stats["avg"], 2),
                "min": round(response_stats["min"], 2),
                "max": round(response_stats["max"], 2),
                "p50": round(response_stats["p50"], 2),
                "p95": round(response_stats["p95"], 2),
                "p99": round(response_stats["p99"], 2)
            },
            
            # Endpoint usage
            "endpoints": self.endpoint_counts,
            
            # Language distribution
            "languages": self.language_counts,
            
            # Error tracking
            "errors": self.error_counts,
            
            # Rate limiting
            "rate_limits": {
                "hits": self.rate_limit_hits
            }
        }
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get health check metrics"""
        response_stats = self.get_response_time_stats()
        
        # Determine health status based on metrics
        status = "healthy"
        if self.active_requests > 100:
            status = "degraded"
        elif response_stats["p95"] > 5000:  # 5 seconds
            status = "degraded"
        elif self.failed_requests > self.successful_requests:
            status = "unhealthy"
        
        return {
            "status": status,
            "uptime_seconds": round(self.get_uptime_seconds(), 2),
            "active_requests": self.active_requests,
            "response_time_p95_ms": round(response_stats["p95"], 2),
            "success_rate": round(
                (self.successful_requests / self.total_requests * 100) 
                if self.total_requests > 0 else 100,
                2
            )
        }

# Global metrics instance
metrics = MetricsCollector()

# Middleware for automatic metrics collection
class MetricsMiddleware:
    """ASGI middleware for automatic metrics collection"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Record request start
            start_time = metrics.record_request_start()
            path = scope["path"]
            
            # Capture response status
            status_code = 200
            
            async def send_wrapper(message):
                nonlocal status_code
                if message["type"] == "http.response.start":
                    status_code = message.get("status", 200)
                await send(message)
            
            try:
                # Process request
                await self.app(scope, receive, send_wrapper)
            finally:
                # Record request completion
                # Extract language from path or default to 'en'
                language = "en"  # Default, could be extracted from headers/body
                metrics.record_request_end(start_time, path, status_code, language)
        else:
            await self.app(scope, receive, send)