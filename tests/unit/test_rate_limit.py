"""
Unit tests for rate limiting middleware
Tests token bucket algorithm, LRU cache, and cleanup mechanisms
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone, timedelta

# Import components to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.middleware.rate_limit import (
    RateLimiter, 
    LRUCache, 
    ClientRateLimitData,
    RateLimitMiddleware,
    WebSocketRateLimiter
)


class TestLRUCache:
    """Test LRU cache implementation"""
    
    def test_cache_initialization(self):
        """Test cache initializes with correct max size"""
        cache = LRUCache(max_size=100)
        assert cache.max_size == 100
        assert cache.size() == 0
    
    def test_put_and_get(self):
        """Test basic put and get operations"""
        cache = LRUCache(max_size=3)
        
        cache.put("client1", "data1")
        cache.put("client2", "data2")
        
        assert cache.get("client1") == "data1"
        assert cache.get("client2") == "data2"
        assert cache.get("client3") is None
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = LRUCache(max_size=3)
        
        # Fill cache
        cache.put("client1", "data1")
        cache.put("client2", "data2")
        cache.put("client3", "data3")
        
        # Access client1 to make it recently used
        cache.get("client1")
        
        # Add new item, should evict client2 (least recently used)
        cache.put("client4", "data4")
        
        assert cache.get("client1") == "data1"  # Still present
        assert cache.get("client2") is None      # Evicted
        assert cache.get("client3") == "data3"   # Still present
        assert cache.get("client4") == "data4"   # New item
    
    def test_remove_old_entries(self):
        """Test removal of old entries based on timeout"""
        cache = LRUCache(max_size=10)
        
        # Create mock client data with last_access times
        current_time = time.time()
        
        old_client = Mock()
        old_client.last_access = current_time - 7200  # 2 hours ago
        
        new_client = Mock()
        new_client.last_access = current_time - 1800  # 30 minutes ago
        
        cache.put("old", old_client)
        cache.put("new", new_client)
        
        # Remove entries older than 1 hour
        removed = cache.remove_old_entries(current_time, 3600)
        
        assert removed == 1
        assert cache.get("old") is None
        assert cache.get("new") == new_client
    
    def test_thread_safety(self):
        """Test thread-safe operations"""
        cache = LRUCache(max_size=1000)
        
        def concurrent_operations():
            for i in range(100):
                cache.put(f"key{i}", f"value{i}")
                cache.get(f"key{i}")
        
        # Run multiple threads
        import threading
        threads = [threading.Thread(target=concurrent_operations) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should complete without deadlock or errors
        assert cache.size() <= 1000


class TestClientRateLimitData:
    """Test client rate limit data structure"""
    
    def test_initialization(self):
        """Test client data initializes correctly"""
        client = ClientRateLimitData()
        
        assert len(client.minute_requests) == 0
        assert len(client.hour_requests) == 0
        assert client.tokens > 0
        assert client.request_count == 0
        assert client.blocked_count == 0
    
    def test_update_access(self):
        """Test access time update"""
        client = ClientRateLimitData()
        initial_time = client.last_access
        
        time.sleep(0.01)
        client.update_access()
        
        assert client.last_access > initial_time
    
    def test_is_idle(self):
        """Test idle detection"""
        client = ClientRateLimitData()
        current_time = time.time()
        
        # Not idle initially
        assert not client.is_idle(current_time, 3600)
        
        # Simulate old access time
        client.last_access = current_time - 7200  # 2 hours ago
        assert client.is_idle(current_time, 3600)  # 1 hour timeout


class TestRateLimiter:
    """Test main rate limiter functionality"""
    
    def test_initialization(self):
        """Test rate limiter initializes with correct parameters"""
        limiter = RateLimiter(
            rate_per_minute=60,
            rate_per_hour=600,
            burst_size=10,
            max_clients=1000
        )
        
        assert limiter.rate_per_minute == 60
        assert limiter.rate_per_hour == 600
        assert limiter.burst_size == 10
        assert limiter.max_clients == 1000
    
    def test_client_id_generation(self):
        """Test client ID generation from request"""
        limiter = RateLimiter()
        
        # Mock request
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.headers = {"X-Session-ID": "session123"}
        
        client_id = limiter.get_client_id(request)
        
        # Should be SHA-256 hash (64 characters)
        assert len(client_id) == 64
        assert all(c in "0123456789abcdef" for c in client_id)
    
    def test_token_refill(self):
        """Test token bucket refill mechanism"""
        limiter = RateLimiter(rate_per_minute=60, burst_size=10)
        client = ClientRateLimitData()
        
        # Deplete some tokens
        client.tokens = 5
        initial_time = time.time()
        client.last_refill = initial_time - 1  # 1 second ago
        
        limiter.refill_tokens(client)
        
        # Should have refilled ~1 token (60/60 = 1 per second)
        assert client.tokens > 5
        assert client.tokens <= 10  # Capped at burst size
    
    def test_minute_rate_limit(self):
        """Test per-minute rate limiting"""
        limiter = RateLimiter(rate_per_minute=5, rate_per_hour=100)
        
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.headers = {}
        
        # Should allow first 5 requests
        for i in range(5):
            allowed, info = limiter.is_allowed(request)
            assert allowed, f"Request {i+1} should be allowed"
        
        # 6th request should be blocked
        allowed, info = limiter.is_allowed(request)
        assert not allowed
        assert info["limit_type"] == "minute"
        assert info["limit"] == 5
    
    def test_hour_rate_limit(self):
        """Test per-hour rate limiting"""
        limiter = RateLimiter(rate_per_minute=100, rate_per_hour=10)
        
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.2"
        request.headers = {}
        
        # Fill up hour limit
        for i in range(10):
            allowed, info = limiter.is_allowed(request)
            assert allowed, f"Request {i+1} should be allowed"
        
        # 11th request should be blocked
        allowed, info = limiter.is_allowed(request)
        assert not allowed
        assert info["limit_type"] == "hour"
        assert info["limit"] == 10
    
    def test_burst_protection(self):
        """Test token bucket burst protection"""
        limiter = RateLimiter(
            rate_per_minute=100, 
            rate_per_hour=1000,
            burst_size=3
        )
        
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.3"
        request.headers = {}
        
        # Should allow burst_size requests quickly
        for i in range(3):
            allowed, info = limiter.is_allowed(request)
            assert allowed, f"Burst request {i+1} should be allowed"
        
        # 4th request immediately should be blocked (no tokens)
        allowed, info = limiter.is_allowed(request)
        assert not allowed
        assert info["limit_type"] == "burst"
    
    def test_cleanup_mechanism(self):
        """Test automatic cleanup of old clients"""
        limiter = RateLimiter(max_clients=10)
        
        # Add some clients
        for i in range(5):
            client_id = f"client_{i}"
            client_data = ClientRateLimitData()
            client_data.last_access = time.time() - 7200  # 2 hours ago
            limiter.clients.put(client_id, client_data)
        
        # Run cleanup
        limiter.cleanup_old_clients()
        
        # Old clients should be removed
        assert limiter.clients.size() == 0
    
    def test_stats_tracking(self):
        """Test statistics tracking"""
        limiter = RateLimiter(rate_per_minute=1)
        
        request = Mock()
        request.client = Mock()
        request.client.host = "192.168.1.4"
        request.headers = {}
        
        # Make some requests
        limiter.is_allowed(request)  # Allowed
        limiter.is_allowed(request)  # Blocked
        
        stats = limiter.get_stats()
        
        assert stats["total_requests"] == 2
        assert stats["total_blocked"] == 1
        assert stats["block_rate"] == 50.0
        assert stats["tracked_clients"] == 1


class TestWebSocketRateLimiter:
    """Test WebSocket-specific rate limiting"""
    
    def test_connection_limit(self):
        """Test WebSocket connection limiting per IP"""
        ws_limiter = WebSocketRateLimiter(max_connections_per_ip=2)
        
        # Should allow first 2 connections
        assert ws_limiter.can_connect("192.168.1.1")
        ws_limiter.add_connection("192.168.1.1")
        
        assert ws_limiter.can_connect("192.168.1.1")
        ws_limiter.add_connection("192.168.1.1")
        
        # 3rd connection should be blocked
        assert not ws_limiter.can_connect("192.168.1.1")
    
    def test_connection_removal(self):
        """Test connection removal"""
        ws_limiter = WebSocketRateLimiter(max_connections_per_ip=1)
        
        ws_limiter.add_connection("192.168.1.1")
        assert not ws_limiter.can_connect("192.168.1.1")
        
        ws_limiter.remove_connection("192.168.1.1")
        assert ws_limiter.can_connect("192.168.1.1")
    
    def test_connection_counting(self):
        """Test connection counting"""
        ws_limiter = WebSocketRateLimiter()
        
        ws_limiter.add_connection("192.168.1.1")
        ws_limiter.add_connection("192.168.1.1")
        ws_limiter.add_connection("192.168.1.2")
        
        assert ws_limiter.get_connection_count("192.168.1.1") == 2
        assert ws_limiter.get_connection_count("192.168.1.2") == 1
        assert ws_limiter.get_total_connections() == 3


@pytest.mark.asyncio
class TestRateLimitMiddleware:
    """Test FastAPI middleware integration"""
    
    async def test_middleware_initialization(self):
        """Test middleware initializes correctly"""
        app = Mock()
        middleware = RateLimitMiddleware(app)
        
        assert middleware.limiter is not None
        assert len(middleware.excluded_paths) > 0
    
    async def test_excluded_paths(self):
        """Test that excluded paths bypass rate limiting"""
        app = Mock()
        middleware = RateLimitMiddleware(app)
        
        # Mock request to excluded path
        request = Mock()
        request.url.path = "/health"
        
        call_next = Mock(return_value=Mock())
        
        # Should pass through without rate limiting
        response = await middleware.dispatch(request, call_next)
        
        # call_next should have been called
        call_next.assert_called_once()
    
    async def test_rate_limit_headers(self):
        """Test that rate limit headers are added to responses"""
        app = Mock()
        middleware = RateLimitMiddleware(app)
        
        # Mock request
        request = Mock()
        request.url.path = "/api/test"
        request.client = Mock()
        request.client.host = "192.168.1.1"
        request.headers = {}
        
        # Mock response
        mock_response = Mock()
        mock_response.headers = {}
        
        call_next = Mock(return_value=mock_response)
        
        # Process request
        response = await middleware.dispatch(request, call_next)
        
        # Should have rate limit headers
        assert "X-RateLimit-Remaining-Minute" in response.headers
        assert "X-RateLimit-Remaining-Hour" in response.headers
        assert "X-RateLimit-Tokens" in response.headers


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])