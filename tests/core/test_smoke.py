#!/usr/bin/env python3
"""
Smoke Tests for KineticChat WebUI
Quick tests to verify basic functionality
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment to use mock database for testing
os.environ["USE_MOCK_DATABASE"] = "true"

from app.main import app

client = TestClient(app)

class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns service info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert data["status"] == "operational"
    
    def test_legacy_health(self):
        """Test legacy health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data
        assert "uptime_seconds" in data
    
    def test_versioned_health(self):
        """Test versioned health endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert data["checks"]["api"] == "operational"
    
    def test_legacy_metrics(self):
        """Test legacy metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "requests_total" in data
    
    def test_versioned_metrics(self):
        """Test versioned metrics endpoint"""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "performance" in data
        assert "resources" in data
    
    def test_status_endpoint(self):
        """Test detailed status endpoint"""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "components" in data
        assert "configuration" in data
        assert data["configuration"]["phi_scrubbing"] == "enabled"

class TestStaticFiles:
    """Test static file serving"""
    
    def test_index_html(self):
        """Test index.html is served"""
        response = client.get("/static/index.html")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_app_js(self):
        """Test app.js is served"""
        response = client.get("/static/app.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]
    
    def test_styles_css(self):
        """Test styles.css is served"""
        response = client.get("/static/styles.css")
        assert response.status_code == 200
        assert "css" in response.headers["content-type"]
    
    def test_barcode_image(self):
        """Test barcode.PNG is served"""
        response = client.get("/static/barcode.PNG")
        assert response.status_code == 200
        assert "image" in response.headers["content-type"]

class TestErrorHandlers:
    """Test error handling"""
    
    def test_404_handler(self):
        """Test 404 error handler"""
        response = client.get("/nonexistent/endpoint")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "Not Found"
        assert "message" in data
        assert "timestamp" in data

class TestMiddleware:
    """Test middleware functionality"""
    
    def test_cors_headers(self):
        """Test CORS headers are present"""
        # Test with GET request instead of OPTIONS
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        # CORS headers should be present
        assert any("access-control" in h.lower() for h in response.headers)
    
    def test_request_id_header(self):
        """Test request ID is added to response"""
        response = client.get("/health")
        assert "x-request-id" in response.headers
    
    def test_response_time_header(self):
        """Test response time is tracked"""
        response = client.get("/health")
        assert "x-response-time" in response.headers

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])