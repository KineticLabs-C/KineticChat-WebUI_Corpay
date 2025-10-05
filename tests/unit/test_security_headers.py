"""
Unit tests for security headers middleware
Tests OWASP-compliant security header implementation
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

# Import components to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.middleware.security_headers import SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    """Test security headers middleware implementation"""
    
    @pytest.mark.asyncio
    async def test_middleware_initialization(self):
        """Test middleware initializes with correct defaults"""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app)
        
        assert middleware.enable_hsts is True
        assert middleware.hsts_max_age == 31536000  # 1 year
        assert middleware.enable_csp is True
        assert middleware.frame_options == "DENY"
    
    @pytest.mark.asyncio
    async def test_custom_initialization(self):
        """Test middleware with custom configuration"""
        app = Mock()
        middleware = SecurityHeadersMiddleware(
            app,
            enable_hsts=False,
            hsts_max_age=86400,
            enable_csp=False,
            frame_options="SAMEORIGIN"
        )
        
        assert middleware.enable_hsts is False
        assert middleware.hsts_max_age == 86400
        assert middleware.enable_csp is False
        assert middleware.frame_options == "SAMEORIGIN"
    
    @pytest.mark.asyncio
    async def test_hsts_header(self):
        """Test Strict-Transport-Security header"""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app, enable_hsts=True)
        
        # Mock request and response
        request = Mock()
        response = Mock()
        response.headers = {}
        
        # Mock call_next
        async def mock_call_next(req):
            return response
        
        # Process request
        result = await middleware.dispatch(request, mock_call_next)
        
        # Check HSTS header
        assert "Strict-Transport-Security" in result.headers
        assert "max-age=31536000" in result.headers["Strict-Transport-Security"]
        assert "includeSubDomains" in result.headers["Strict-Transport-Security"]
    
    @pytest.mark.asyncio
    async def test_hsts_disabled(self):
        """Test HSTS header when disabled"""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app, enable_hsts=False)
        
        # Mock request and response
        request = Mock()
        response = Mock()
        response.headers = {}
        
        # Mock call_next
        async def mock_call_next(req):
            return response
        
        # Process request
        result = await middleware.dispatch(request, mock_call_next)
        
        # HSTS should not be present
        assert "Strict-Transport-Security" not in result.headers
    
    @pytest.mark.asyncio
    async def test_security_headers_basic(self):
        """Test basic security headers are always added"""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app)
        
        # Mock request and response
        request = Mock()
        response = Mock()
        response.headers = {}
        
        # Mock call_next
        async def mock_call_next(req):
            return response
        
        # Process request
        result = await middleware.dispatch(request, mock_call_next)
        
        # Check basic security headers
        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.headers["X-Frame-Options"] == "DENY"
        assert result.headers["X-XSS-Protection"] == "1; mode=block"
        assert result.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    
    @pytest.mark.asyncio
    async def test_frame_options_variations(self):
        """Test different X-Frame-Options values"""
        app = Mock()
        
        # Test DENY
        middleware = SecurityHeadersMiddleware(app, frame_options="DENY")
        request = Mock()
        response = Mock()
        response.headers = {}
        
        async def mock_call_next(req):
            return response
        
        result = await middleware.dispatch(request, mock_call_next)
        assert result.headers["X-Frame-Options"] == "DENY"
        
        # Test SAMEORIGIN
        middleware = SecurityHeadersMiddleware(app, frame_options="SAMEORIGIN")
        response.headers = {}
        result = await middleware.dispatch(request, mock_call_next)
        assert result.headers["X-Frame-Options"] == "SAMEORIGIN"
    
    @pytest.mark.asyncio
    async def test_csp_header_basic(self):
        """Test Content-Security-Policy header"""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app, enable_csp=True)
        
        # Mock request and response
        request = Mock()
        response = Mock()
        response.headers = {}
        
        # Mock call_next
        async def mock_call_next(req):
            return response
        
        # Process request
        result = await middleware.dispatch(request, mock_call_next)
        
        # Check CSP header
        assert "Content-Security-Policy" in result.headers
        csp = result.headers["Content-Security-Policy"]
        
        # Verify key CSP directives
        assert "default-src 'self'" in csp
        assert "script-src" in csp
        assert "style-src" in csp
        assert "img-src" in csp
        assert "connect-src" in csp
    
    @pytest.mark.asyncio
    async def test_csp_disabled(self):
        """Test CSP header when disabled"""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app, enable_csp=False)
        
        # Mock request and response
        request = Mock()
        response = Mock()
        response.headers = {}
        
        # Mock call_next
        async def mock_call_next(req):
            return response
        
        # Process request
        result = await middleware.dispatch(request, mock_call_next)
        
        # CSP should not be present
        assert "Content-Security-Policy" not in result.headers
    
    @pytest.mark.asyncio
    async def test_custom_csp(self):
        """Test custom CSP policy"""
        app = Mock()
        custom_csp = "default-src 'none'; script-src 'self';"
        middleware = SecurityHeadersMiddleware(
            app, 
            enable_csp=True,
            custom_csp=custom_csp
        )
        
        # Mock request and response
        request = Mock()
        response = Mock()
        response.headers = {}
        
        # Mock call_next
        async def mock_call_next(req):
            return response
        
        # Process request
        result = await middleware.dispatch(request, mock_call_next)
        
        # Check custom CSP
        assert result.headers["Content-Security-Policy"] == custom_csp
    
    @pytest.mark.asyncio
    async def test_permissions_policy(self):
        """Test Permissions-Policy header"""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app)
        
        # Mock request and response
        request = Mock()
        response = Mock()
        response.headers = {}
        
        # Mock call_next
        async def mock_call_next(req):
            return response
        
        # Process request
        result = await middleware.dispatch(request, mock_call_next)
        
        # Check Permissions-Policy
        assert "Permissions-Policy" in result.headers
        policy = result.headers["Permissions-Policy"]
        
        # Verify dangerous features are disabled
        assert "geolocation=()" in policy
        assert "microphone=()" in policy
        assert "camera=()" in policy
        assert "payment=()" in policy
    
    @pytest.mark.asyncio
    async def test_all_headers_present(self):
        """Test all expected security headers are present"""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app)
        
        # Mock request and response
        request = Mock()
        response = Mock()
        response.headers = {}
        
        # Mock call_next
        async def mock_call_next(req):
            return response
        
        # Process request
        result = await middleware.dispatch(request, mock_call_next)
        
        # List of expected headers
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "Permissions-Policy",
            "Strict-Transport-Security",
            "Content-Security-Policy"
        ]
        
        for header in expected_headers:
            assert header in result.headers, f"Missing header: {header}"
    
    @pytest.mark.asyncio
    async def test_headers_not_overwritten(self):
        """Test that existing headers are not overwritten"""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app)
        
        # Mock request and response with existing header
        request = Mock()
        response = Mock()
        response.headers = {"X-Custom-Header": "custom-value"}
        
        # Mock call_next
        async def mock_call_next(req):
            return response
        
        # Process request
        result = await middleware.dispatch(request, mock_call_next)
        
        # Custom header should still be present
        assert result.headers["X-Custom-Header"] == "custom-value"
        # Security headers should also be present
        assert "X-Content-Type-Options" in result.headers
    
    @pytest.mark.asyncio
    async def test_environment_variable_configuration(self):
        """Test configuration via environment variables"""
        with patch.dict(os.environ, {
            "ENABLE_HSTS": "false",
            "HSTS_MAX_AGE": "86400",
            "ENABLE_CSP": "false",
            "FRAME_OPTIONS": "SAMEORIGIN"
        }):
            # Re-import to get new environment values
            from importlib import reload
            import app.middleware.security_headers as sec_headers
            reload(sec_headers)
            
            app = Mock()
            middleware = sec_headers.SecurityHeadersMiddleware(app)
            
            # Values should come from environment
            assert middleware.enable_hsts is False
            assert middleware.hsts_max_age == 86400
            assert middleware.enable_csp is False
            assert middleware.frame_options == "SAMEORIGIN"
    
    @pytest.mark.asyncio
    async def test_owasp_compliance(self):
        """Test that headers meet OWASP recommendations"""
        app = Mock()
        middleware = SecurityHeadersMiddleware(app)
        
        # Mock request and response
        request = Mock()
        response = Mock()
        response.headers = {}
        
        # Mock call_next
        async def mock_call_next(req):
            return response
        
        # Process request
        result = await middleware.dispatch(request, mock_call_next)
        
        # OWASP recommended values
        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]
        assert "Strict-Transport-Security" in result.headers
        assert "Content-Security-Policy" in result.headers
        assert result.headers["Referrer-Policy"] in [
            "no-referrer",
            "strict-origin",
            "strict-origin-when-cross-origin"
        ]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])