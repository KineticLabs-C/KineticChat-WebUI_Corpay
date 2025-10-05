#!/usr/bin/env python3
"""
PHI Scrubber Unit Tests
Comprehensive tests for HIPAA compliance
"""

import sys
import os
import pytest

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import (
    PHIScrubber,
    scrub_text,
    scrub_dict,
    scrub_json,
    has_phi,
    safe_log
)

class TestPHIScrubber:
    """Test PHI scrubbing functionality"""
    
    def setup_method(self):
        """Set up test scrubber"""
        self.scrubber = PHIScrubber()
    
    def test_ssn_scrubbing(self):
        """Test SSN patterns are scrubbed"""
        test_cases = [
            "SSN: 123-45-6789",
            "Social Security: 123456789",
            "SSN 123 45 6789",
        ]
        
        for text in test_cases:
            result = scrub_text(text)
            assert "123" not in result
            assert "[REDACTED]" in result
            assert has_phi(text) == True
    
    def test_medical_record_scrubbing(self):
        """Test MRN patterns are scrubbed"""
        test_cases = [
            "MRN: 123456",
            "MR# 987654321",
            "Medical Record: ABC123456",
        ]
        
        for text in test_cases:
            result = scrub_text(text)
            assert "[REDACTED]" in result
            assert not any(char.isdigit() for char in result.replace("[REDACTED]", ""))
    
    def test_date_of_birth_scrubbing(self):
        """Test DOB patterns are scrubbed"""
        test_cases = [
            "DOB: 01/15/1980",
            "Date of Birth: 12-25-1975",
            "Born on 1990-06-30",
        ]
        
        for text in test_cases:
            result = scrub_text(text)
            assert "1980" not in result
            assert "1975" not in result
            assert "1990" not in result
            assert "[REDACTED]" in result
    
    def test_phone_scrubbing(self):
        """Test phone number patterns are scrubbed"""
        test_cases = [
            "Call me at 555-123-4567",
            "Phone: (555) 123-4567",
            "Mobile: +1 555-123-4567",
        ]
        
        for text in test_cases:
            result = scrub_text(text)
            assert "555" not in result
            assert "123" not in result
            assert "4567" not in result
            assert "[REDACTED]" in result
    
    def test_email_scrubbing(self):
        """Test email addresses are scrubbed"""
        test_cases = [
            "Email: john.doe@example.com",
            "Contact: patient@hospital.org",
            "Send to: user123@gmail.com",
        ]
        
        for text in test_cases:
            result = scrub_text(text)
            assert "@" not in result or "[REDACTED]" in result
            assert "example.com" not in result
    
    def test_credit_card_scrubbing(self):
        """Test credit card numbers are scrubbed"""
        test_cases = [
            "Card: 1234 5678 9012 3456",
            "CC: 1234-5678-9012-3456",
            "Payment: 1234567890123456",
        ]
        
        for text in test_cases:
            result = scrub_text(text)
            assert "1234" not in result
            assert "5678" not in result
            assert "[REDACTED]" in result
    
    def test_patient_name_scrubbing(self):
        """Test patient names are scrubbed when preceded by keywords"""
        test_cases = [
            "Patient John Doe needs medication",
            "Member Jane Smith called",
            "Dr. Robert Johnson prescribed",
        ]
        
        for text in test_cases:
            result = scrub_text(text)
            # Names should be scrubbed when preceded by patient keywords
            if "Patient" in text or "Member" in text or "Dr." in text:
                assert "[REDACTED]" in result
    
    def test_address_scrubbing(self):
        """Test address patterns are scrubbed"""
        test_cases = [
            "Address: 123 Main Street",
            "Lives at 456 Oak Avenue, Apt 5",
            "Suite 100, 789 Business Boulevard",
        ]
        
        for text in test_cases:
            result = scrub_text(text)
            assert "[REDACTED]" in result
    
    def test_prescription_scrubbing(self):
        """Test prescription numbers are scrubbed"""
        test_cases = [
            "RX: 123456789",
            "Prescription# 987654321",
            "Rx:9876543",
        ]
        
        for text in test_cases:
            result = scrub_text(text)
            assert not any(char.isdigit() for char in result.replace("[REDACTED]", "").replace(":", ""))
            assert "[REDACTED]" in result
    
    def test_dictionary_scrubbing(self):
        """Test dictionary PHI scrubbing"""
        test_dict = {
            "patient_name": "John Doe",
            "ssn": "123-45-6789",
            "dob": "01/15/1980",
            "phone": "555-123-4567",
            "email": "john@example.com",
            "safe_field": "This is safe data",
            "nested": {
                "patient_id": "12345",
                "message": "Patient needs refill"
            }
        }
        
        result = scrub_dict(test_dict)
        
        # Sensitive fields should be redacted
        assert result["patient_name"] == "[REDACTED-FIELD]"
        assert result["ssn"] == "[REDACTED-FIELD]"
        assert result["dob"] == "[REDACTED-FIELD]"
        assert result["phone"] == "[REDACTED-FIELD]"
        assert result["email"] == "[REDACTED-FIELD]"
        
        # Safe fields should remain
        assert result["safe_field"] == "This is safe data"
        
        # Nested dictionaries should be scrubbed
        assert isinstance(result["nested"], dict)
    
    def test_list_scrubbing(self):
        """Test list PHI scrubbing"""
        test_list = [
            "SSN: 123-45-6789",
            "Safe text",
            {"patient_name": "Jane Doe"},
            ["Phone: 555-123-4567", "More safe text"]
        ]
        
        result = self.scrubber.scrub_list(test_list)
        
        assert "[REDACTED]" in result[0]
        assert result[1] == "Safe text"
        assert result[2]["patient_name"] == "[REDACTED-FIELD]"
        assert "[REDACTED]" in result[3][0]
        assert result[3][1] == "More safe text"
    
    def test_json_scrubbing(self):
        """Test JSON string PHI scrubbing"""
        test_json = '{"patient_name": "John Doe", "ssn": "123-45-6789", "safe": "data"}'
        
        result = scrub_json(test_json)
        assert "John Doe" not in result
        assert "123-45-6789" not in result
        assert "[REDACTED-FIELD]" in result
        assert '"safe": "data"' in result or '"safe":"data"' in result
    
    def test_phi_detection(self):
        """Test PHI detection accuracy"""
        # Should detect PHI
        phi_texts = [
            "SSN: 123-45-6789",
            "Patient John Doe",
            "MRN: 123456",
            "DOB: 01/01/1990",
            "Call 555-123-4567",
            "patient diagnosis treatment medication symptom",  # Multiple keywords
        ]
        
        for text in phi_texts:
            assert has_phi(text) == True, f"Failed to detect PHI in: {text}"
        
        # Should NOT detect PHI
        safe_texts = [
            "This is safe text",
            "Product ID: 12345",
            "Version 1.2.3.4",
            "Error code 404",
            "Temperature is 98.6",
        ]
        
        for text in safe_texts:
            assert has_phi(text) == False, f"Incorrectly detected PHI in: {text}"
    
    def test_safe_log(self):
        """Test safe logging function"""
        # Test with PHI in message
        message = "Patient John Doe, SSN: 123-45-6789"
        result = safe_log(message)
        assert "123-45-6789" not in result
        assert "[REDACTED]" in result
        
        # Test with PHI in data
        data = {"patient_name": "Jane Doe", "safe": "value"}
        result = safe_log("Processing data", data)
        assert "Jane Doe" not in result
        assert "[REDACTED-FIELD]" in result
        assert "safe" in result
    
    def test_phi_summary(self):
        """Test PHI summary reporting"""
        text = """
        Patient John Doe
        SSN: 123-45-6789
        DOB: 01/15/1980
        Phone: 555-123-4567
        Email: john@example.com
        MRN: 123456
        """
        
        summary = self.scrubber.get_phi_summary(text)
        
        assert "ssn" in summary
        assert "dob" in summary
        assert "phone" in summary
        assert "email" in summary
        assert "mrn" in summary
        
        # Check counts are reasonable
        assert all(count > 0 for count in summary.values())
    
    def test_custom_patterns(self):
        """Test custom PHI patterns"""
        custom_patterns = {
            "employee_id": [r'\bEMP\d{6}\b'],
            "custom_id": [r'\bCUST-\d{4}-\d{4}\b']
        }
        
        custom_scrubber = PHIScrubber(custom_patterns=custom_patterns)
        
        text = "Employee EMP123456 and customer CUST-1234-5678"
        result = custom_scrubber.scrub_text(text)
        
        assert "EMP123456" not in result
        assert "CUST-1234-5678" not in result
        assert "[REDACTED]" in result

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])