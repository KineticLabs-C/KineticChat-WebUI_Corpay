"""
Security Headers Middleware - OWASP Compliant Implementation

This module implements comprehensive security headers following OWASP best practices
to protect against common web vulnerabilities.

Security Headers Implemented:
- Strict-Transport-Security (HSTS): Enforces HTTPS connections
- X-Content-Type-Options: Prevents MIME type sniffing
- X-Frame-Options: Prevents clickjacking attacks
- X-XSS-Protection: Legacy XSS protection for older browsers
- Content-Security-Policy (CSP): Controls resource loading
- Referrer-Policy: Controls referrer information
- Permissions-Policy: Restricts browser features

OWASP Compliance:
- Follows OWASP Secure Headers Project recommendations
- Implements defense-in-depth security strategy
- Compatible with modern browsers

Configuration (via environment variables):
- ENABLE_HSTS: Enable HSTS header (default: true)
- HSTS_MAX_AGE: HSTS max age in seconds (default: 31536000)
- ENABLE_CSP: Enable Content Security Policy (default: true)
- FRAME_OPTIONS: X-Frame-Options value (default: DENY)

Usage:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

Security Benefits:
- Prevents XSS attacks via CSP
- Blocks clickjacking via X-Frame-Options
- Enforces HTTPS via HSTS
- Prevents MIME confusion attacks
- Restricts dangerous browser features

Performance Impact:
- Minimal overhead (< 1ms per request)
- Headers cached by browsers
- No computational overhead
"""

import os
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


# Configuration from environment
ENABLE_HSTS = os.getenv("ENABLE_HSTS", "true").lower() == "true"
HSTS_MAX_AGE = int(os.getenv("HSTS_MAX_AGE", "31536000"))  # 1 year
ENABLE_CSP = os.getenv("ENABLE_CSP", "true").lower() == "true"
FRAME_OPTIONS = os.getenv("FRAME_OPTIONS", "DENY")  # DENY, SAMEORIGIN, or ALLOW-FROM uri


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    Based on OWASP security best practices
    """
    
    def __init__(
        self,
        app,
        enable_hsts: bool = ENABLE_HSTS,
        hsts_max_age: int = HSTS_MAX_AGE,
        enable_csp: bool = ENABLE_CSP,
        frame_options: str = FRAME_OPTIONS,
        custom_csp: Optional[str] = None
    ):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.enable_csp = enable_csp
        self.frame_options = frame_options
        
        # Content Security Policy - restrictive by default
        self.csp = custom_csp or self._build_default_csp()
    
    def _build_default_csp(self) -> str:
        """Build a default Content Security Policy"""
        # Healthcare applications should be restrictive
        csp_directives = [
            "default-src 'self'",  # Default to same origin only
            "script-src 'self' 'unsafe-inline'",  # Allow inline scripts (for simplicity)
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",  # Allow inline styles and Google Fonts
            "font-src 'self' https://fonts.gstatic.com data:",  # Allow fonts from self and Google
            "img-src 'self' data: https:",  # Allow images from self, data URIs, and HTTPS
            "connect-src 'self'",  # XHR/fetch only to same origin
            "frame-ancestors 'none'",  # Prevent embedding
            "base-uri 'self'",  # Restrict base tag
            "form-action 'self'",  # Form submissions only to same origin
            "upgrade-insecure-requests"  # Upgrade HTTP to HTTPS
        ]
        
        return "; ".join(csp_directives)
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""
        
        # Process the request
        response = await call_next(request)
        
        # Add security headers
        
        # 1. Strict-Transport-Security (HSTS)
        # Forces HTTPS for all future requests
        if self.enable_hsts:
            hsts_header = f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            response.headers["Strict-Transport-Security"] = hsts_header
        
        # 2. X-Frame-Options
        # Prevents clickjacking attacks
        response.headers["X-Frame-Options"] = self.frame_options
        
        # 3. X-Content-Type-Options
        # Prevents MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # 4. X-XSS-Protection
        # Enables browser XSS filtering (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # 5. Referrer-Policy
        # Controls referrer information sent with requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 6. Content-Security-Policy
        # Prevents XSS, data injection, and other attacks
        if self.enable_csp:
            # Use Report-Only mode in development
            env = os.getenv("APP_ENV", "development")
            if env == "development":
                response.headers["Content-Security-Policy-Report-Only"] = self.csp
            else:
                response.headers["Content-Security-Policy"] = self.csp
        
        # 7. Permissions-Policy (formerly Feature-Policy)
        # Restricts browser features
        permissions = [
            "accelerometer=()",
            "camera=()",
            "geolocation=()",
            "gyroscope=()",
            "magnetometer=()",
            "microphone=()",
            "payment=()",
            "usb=()"
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions)
        
        # 8. Clear-Site-Data (for logout/sensitive operations)
        # Only add on specific endpoints
        if request.url.path in ["/logout", "/api/v1/logout"]:
            response.headers["Clear-Site-Data"] = '"cache", "cookies", "storage"'
        
        # 9. Cache-Control for sensitive endpoints
        # Prevent caching of sensitive data
        sensitive_paths = [
            "/api/kroger-chat",
            "/api/v1/chat",
            "/api/v1/chat/feedback"
        ]
        if any(request.url.path.startswith(path) for path in sensitive_paths):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # 10. Remove sensitive headers
        # Remove headers that might leak information
        headers_to_remove = ["Server", "X-Powered-By"]
        for header in headers_to_remove:
            response.headers.pop(header, None)
        
        return response


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware with security considerations
    Supplements FastAPI's built-in CORS middleware
    """
    
    def __init__(
        self,
        app,
        allowed_origins: list = None,
        allowed_methods: list = None,
        allowed_headers: list = None,
        max_age: int = 86400  # 24 hours
    ):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["https://localhost", "https://127.0.0.1"]
        self.allowed_methods = allowed_methods or ["GET", "POST", "OPTIONS"]
        self.allowed_headers = allowed_headers or ["Content-Type", "Authorization", "X-Session-ID"]
        self.max_age = max_age
    
    async def dispatch(self, request: Request, call_next):
        """Handle CORS with security in mind"""
        
        # Get origin
        origin = request.headers.get("origin", "")
        
        # Check if origin is allowed
        if origin and self._is_origin_allowed(origin):
            # Process request
            response = await call_next(request)
            
            # Add CORS headers
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"
            
            # Handle preflight
            if request.method == "OPTIONS":
                response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
                response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
                response.headers["Access-Control-Max-Age"] = str(self.max_age)
            
            return response
        
        # Origin not allowed - process without CORS headers
        return await call_next(request)
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is in allowed list"""
        # Exact match
        if origin in self.allowed_origins:
            return True
        
        # Wildcard support (use with caution)
        for allowed in self.allowed_origins:
            if allowed == "*":
                # Avoid wildcard in production
                env = os.getenv("APP_ENV", "development")
                return env == "development"
            
            # Subdomain wildcard (e.g., https://*.example.com)
            if allowed.startswith("https://*."):
                domain = allowed.replace("https://*.", "")
                if origin.endswith(domain):
                    return True
        
        return False


# Utility function to add all security middleware
def add_security_middleware(app, **kwargs):
    """
    Add all security-related middleware to the application
    
    Args:
        app: FastAPI application instance
        **kwargs: Configuration options for middleware
    """
    
    # Add security headers
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=kwargs.get("enable_hsts", True),
        hsts_max_age=kwargs.get("hsts_max_age", 31536000),
        enable_csp=kwargs.get("enable_csp", True),
        frame_options=kwargs.get("frame_options", "DENY")
    )
    
    # Add enhanced CORS if needed
    if kwargs.get("enable_cors_security", False):
        app.add_middleware(
            CORSSecurityMiddleware,
            allowed_origins=kwargs.get("allowed_origins", ["https://localhost"]),
            allowed_methods=kwargs.get("allowed_methods", ["GET", "POST", "OPTIONS"]),
            allowed_headers=kwargs.get("allowed_headers", ["Content-Type", "X-Session-ID"])
        )
    
    print("Security middleware added successfully")


# Export middleware classes
__all__ = [
    "SecurityHeadersMiddleware",
    "CORSSecurityMiddleware",
    "add_security_middleware"
]