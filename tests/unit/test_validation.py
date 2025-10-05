"""
Unit tests for Pydantic validation models
Tests input validation, sanitization, and type safety
"""

import pytest
from pydantic import ValidationError
from datetime import datetime
import json

# Import components to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.validation import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    HealthResponse,
    MetricsResponse,
    MAX_MESSAGE_LENGTH,
    MIN_MESSAGE_LENGTH,
    MAX_SESSION_ID_LENGTH
)


class TestChatRequest:
    """Test ChatRequest validation model"""
    
    def test_valid_request_with_query(self):
        """Test valid request with query field"""
        request = ChatRequest(
            query="Hello, how are you?",
            session_id="session123",
            language="en"
        )
        
        assert request.query == "Hello, how are you?"
        assert request.session_id == "session123"
        assert request.language == "en"
    
    def test_valid_request_with_message(self):
        """Test valid request with legacy message field"""
        request = ChatRequest(
            message="Hello, how are you?",
            session_id="session123",
            language="es"
        )
        
        assert request.message == "Hello, how are you?"
        assert request.session_id == "session123"
        assert request.language == "es"
    
    def test_both_query_and_message(self):
        """Test request with both query and message fields"""
        request = ChatRequest(
            query="Query text",
            message="Message text",
            session_id="session123"
        )
        
        assert request.query == "Query text"
        assert request.message == "Message text"
    
    def test_empty_request_validation(self):
        """Test that at least one of query/message is required"""
        request = ChatRequest(
            session_id="session123"
        )
        
        # Request is valid but get_message should handle empty
        assert request.query is None
        assert request.message is None
    
    def test_message_length_validation(self):
        """Test message length constraints"""
        # Test minimum length
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(
                query="",  # Empty string
                session_id="session123"
            )
        
        # Test maximum length
        long_message = "x" * (MAX_MESSAGE_LENGTH + 1)
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(
                query=long_message,
                session_id="session123"
            )
    
    def test_session_id_validation(self):
        """Test session ID length constraint"""
        # Valid session ID
        request = ChatRequest(
            query="Hello",
            session_id="a" * MAX_SESSION_ID_LENGTH
        )
        assert len(request.session_id) == MAX_SESSION_ID_LENGTH
        
        # Session ID too long
        with pytest.raises(ValidationError):
            ChatRequest(
                query="Hello",
                session_id="a" * (MAX_SESSION_ID_LENGTH + 1)
            )
    
    def test_language_validation(self):
        """Test language field validation"""
        # Valid languages
        request_en = ChatRequest(
            query="Hello",
            session_id="session123",
            language="en"
        )
        assert request_en.language == "en"
        
        request_es = ChatRequest(
            query="Hola",
            session_id="session123",
            language="es"
        )
        assert request_es.language == "es"
        
        # Invalid language
        with pytest.raises(ValidationError):
            ChatRequest(
                query="Hello",
                session_id="session123",
                language="fr"  # Not supported
            )
    
    def test_html_sanitization(self):
        """Test HTML escaping in messages"""
        request = ChatRequest(
            query="<script>alert('xss')</script>",
            session_id="session123"
        )
        
        # Check sanitization was applied
        sanitized = request.sanitize_html(request.query)
        assert "<script>" not in sanitized
        assert "&lt;script&gt;" in sanitized
    
    def test_get_message_method(self):
        """Test get_message helper method"""
        # Query takes precedence
        request = ChatRequest(
            query="Query text",
            message="Message text",
            session_id="session123"
        )
        assert request.get_message() == "Query text"
        
        # Falls back to message
        request = ChatRequest(
            message="Message text",
            session_id="session123"
        )
        assert request.get_message() == "Message text"
        
        # Returns empty string if both None
        request = ChatRequest(
            session_id="session123"
        )
        assert request.get_message() == ""
    
    def test_metadata_validation(self):
        """Test metadata field validation"""
        # Valid metadata
        request = ChatRequest(
            query="Hello",
            session_id="session123",
            metadata={"key": "value", "count": 123}
        )
        assert request.metadata["key"] == "value"
        assert request.metadata["count"] == 123
    
    def test_timestamp_default(self):
        """Test timestamp is automatically set"""
        request = ChatRequest(
            query="Hello",
            session_id="session123"
        )
        
        assert request.timestamp is not None
        assert isinstance(request.timestamp, datetime)


class TestChatResponse:
    """Test ChatResponse validation model"""
    
    def test_valid_response(self):
        """Test valid chat response"""
        response = ChatResponse(
            response="Hello! How can I help you?",
            session_id="session123",
            language="en"
        )
        
        assert response.response == "Hello! How can I help you?"
        assert response.session_id == "session123"
        assert response.language == "en"
        assert response.status == "success"
    
    def test_error_response(self):
        """Test error response"""
        response = ChatResponse(
            response="",
            session_id="session123",
            language="en",
            status="error",
            error="Rate limit exceeded"
        )
        
        assert response.status == "error"
        assert response.error == "Rate limit exceeded"
    
    def test_response_with_metadata(self):
        """Test response with metadata"""
        response = ChatResponse(
            response="Answer",
            session_id="session123",
            language="en",
            metadata={
                "confidence": 0.95,
                "sources": ["doc1", "doc2"]
            }
        )
        
        assert response.metadata["confidence"] == 0.95
        assert len(response.metadata["sources"]) == 2
    
    def test_response_html_sanitization(self):
        """Test HTML is sanitized in responses"""
        response = ChatResponse(
            response="<b>Bold text</b>",
            session_id="session123",
            language="en"
        )
        
        # Check sanitization
        sanitized = response.sanitize_html(response.response)
        assert "&lt;b&gt;" in sanitized
    
    def test_response_length_validation(self):
        """Test response length constraints"""
        # Maximum length response
        long_response = "x" * 5000
        response = ChatResponse(
            response=long_response,
            session_id="session123",
            language="en"
        )
        assert len(response.response) == 5000
    
    def test_response_timestamp(self):
        """Test timestamp is set on response"""
        response = ChatResponse(
            response="Hello",
            session_id="session123",
            language="en"
        )
        
        assert response.timestamp is not None
        assert isinstance(response.timestamp, datetime)


class TestFeedbackRequest:
    """Test FeedbackRequest validation model"""
    
    def test_valid_feedback(self):
        """Test valid feedback request"""
        feedback = FeedbackRequest(
            session_id="session123",
            message_id="msg456",
            rating=5,
            feedback="Very helpful response!"
        )
        
        assert feedback.session_id == "session123"
        assert feedback.message_id == "msg456"
        assert feedback.rating == 5
        assert feedback.feedback == "Very helpful response!"
    
    def test_rating_validation(self):
        """Test rating constraints (1-5)"""
        # Valid ratings
        for rating in [1, 2, 3, 4, 5]:
            feedback = FeedbackRequest(
                session_id="session123",
                message_id="msg456",
                rating=rating
            )
            assert feedback.rating == rating
        
        # Invalid ratings
        for invalid_rating in [0, 6, -1, 10]:
            with pytest.raises(ValidationError):
                FeedbackRequest(
                    session_id="session123",
                    message_id="msg456",
                    rating=invalid_rating
                )
    
    def test_optional_feedback_text(self):
        """Test feedback text is optional"""
        feedback = FeedbackRequest(
            session_id="session123",
            message_id="msg456",
            rating=4
            # No feedback text
        )
        
        assert feedback.feedback is None
    
    def test_feedback_text_length(self):
        """Test feedback text length constraint"""
        # Maximum length (1000 chars)
        long_feedback = "x" * 1000
        feedback = FeedbackRequest(
            session_id="session123",
            message_id="msg456",
            rating=5,
            feedback=long_feedback
        )
        assert len(feedback.feedback) == 1000
        
        # Too long
        with pytest.raises(ValidationError):
            FeedbackRequest(
                session_id="session123",
                message_id="msg456",
                rating=5,
                feedback="x" * 1001
            )


class TestHealthResponse:
    """Test HealthResponse validation model"""
    
    def test_healthy_response(self):
        """Test healthy status response"""
        health = HealthResponse(
            status="healthy",
            version="1.0.0"
        )
        
        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert health.timestamp is not None
    
    def test_unhealthy_response(self):
        """Test unhealthy status with details"""
        health = HealthResponse(
            status="unhealthy",
            version="1.0.0",
            database="disconnected",
            rag="operational"
        )
        
        assert health.status == "unhealthy"
        assert health.database == "disconnected"
        assert health.rag == "operational"
    
    def test_uptime_calculation(self):
        """Test uptime is included in response"""
        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            uptime=3600  # 1 hour in seconds
        )
        
        assert health.uptime == 3600


class TestMetricsResponse:
    """Test MetricsResponse validation model"""
    
    def test_metrics_response(self):
        """Test metrics response structure"""
        metrics = MetricsResponse(
            total_requests=1000,
            total_errors=5,
            average_response_time=0.250,
            active_sessions=25,
            cache_hit_rate=0.85
        )
        
        assert metrics.total_requests == 1000
        assert metrics.total_errors == 5
        assert metrics.average_response_time == 0.250
        assert metrics.active_sessions == 25
        assert metrics.cache_hit_rate == 0.85
    
    def test_error_rate_calculation(self):
        """Test error rate is calculated correctly"""
        metrics = MetricsResponse(
            total_requests=1000,
            total_errors=50,
            average_response_time=0.250,
            active_sessions=10
        )
        
        # Error rate should be 5%
        assert metrics.error_rate == 0.05
    
    def test_metrics_with_details(self):
        """Test metrics with additional details"""
        metrics = MetricsResponse(
            total_requests=5000,
            total_errors=10,
            average_response_time=0.150,
            active_sessions=50,
            details={
                "endpoints": {
                    "/api/chat": 4000,
                    "/health": 1000
                },
                "languages": {
                    "en": 3500,
                    "es": 1500
                }
            }
        )
        
        assert metrics.details["endpoints"]["/api/chat"] == 4000
        assert metrics.details["languages"]["en"] == 3500
    
    def test_metrics_timestamp(self):
        """Test metrics include timestamp"""
        metrics = MetricsResponse(
            total_requests=100,
            total_errors=0,
            average_response_time=0.100,
            active_sessions=5
        )
        
        assert metrics.timestamp is not None
        assert isinstance(metrics.timestamp, datetime)


class TestValidationEdgeCases:
    """Test edge cases and special scenarios"""
    
    def test_unicode_handling(self):
        """Test Unicode characters in messages"""
        request = ChatRequest(
            query="Hello 你好 مرحبا שלום",
            session_id="session123"
        )
        
        assert "你好" in request.query
        assert "مرحبا" in request.query
    
    def test_emoji_handling(self):
        """Test emoji in messages"""
        request = ChatRequest(
            query="Hello! 😊 How are you? 🎉",
            session_id="session123"
        )
        
        assert "😊" in request.query
        assert "🎉" in request.query
    
    def test_json_serialization(self):
        """Test models can be serialized to JSON"""
        request = ChatRequest(
            query="Test message",
            session_id="session123",
            language="en"
        )
        
        # Should serialize without errors
        json_data = request.json()
        assert isinstance(json_data, str)
        
        # Should deserialize back
        parsed = json.loads(json_data)
        assert parsed["query"] == "Test message"
    
    def test_dict_conversion(self):
        """Test models can be converted to dict"""
        response = ChatResponse(
            response="Test response",
            session_id="session123",
            language="en"
        )
        
        response_dict = response.dict()
        assert response_dict["response"] == "Test response"
        assert response_dict["session_id"] == "session123"
    
    def test_field_aliasing(self):
        """Test field aliases work correctly"""
        # Test that both field names work
        data = {
            "query": "Test",
            "session_id": "123",
            "language": "en"
        }
        
        request = ChatRequest(**data)
        assert request.query == "Test"
    
    def test_extra_fields_forbidden(self):
        """Test that extra fields are rejected"""
        with pytest.raises(ValidationError):
            ChatRequest(
                query="Test",
                session_id="123",
                language="en",
                extra_field="not_allowed"  # Should fail
            )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])