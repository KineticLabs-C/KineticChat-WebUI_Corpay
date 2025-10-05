"""
PHI (Protected Health Information) Scrubbing Utility
HIPAA-compliant sanitization for logs and outputs
MUST be used before any logging or data storage
"""

import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import json

# PHI patterns to detect and scrub
PHI_PATTERNS = {
    # Social Security Numbers
    "ssn": [
        r'\b\d{3}-\d{2}-\d{4}\b',  # 123-45-6789
        r'\b\d{9}\b',  # 123456789
        r'\b\d{3}\s\d{2}\s\d{4}\b',  # 123 45 6789
    ],
    
    # Medical Record Numbers (MRN) - various formats
    "mrn": [
        r'\bMRN[\s:#]*[\w\d]{6,12}\b',  # MRN: 123456
        r'\bMR[\s:#]*[\w\d]{6,12}\b',  # MR# 123456
        r'\bRecord[\s:#]*[\w\d]{6,12}\b',  # Record: 123456
    ],
    
    # Date of Birth patterns
    "dob": [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or M/D/YY
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',  # YYYY-MM-DD
        r'\b(?:DOB|Date of Birth)[\s:]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
    ],
    
    # Phone numbers
    "phone": [
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 123-456-7890
        r'\b\(\d{3}\)\s?\d{3}[-.\s]?\d{4}\b',  # (123) 456-7890
        r'\b\+1\s?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # +1 123-456-7890
        r'Phone:\s*\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',  # Phone: (123) 456-7890
        r'Mobile:\s*\+?\d{1,3}\s?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # Mobile: +1 123-456-7890
    ],
    
    # Email addresses (may contain patient names)
    "email": [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    ],
    
    # Credit card numbers
    "credit_card": [
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # 1234 5678 9012 3456
    ],
    
    # Driver's license (generic pattern - varies by state)
    "drivers_license": [
        r'\bDL[\s:#]*[\w\d]{6,12}\b',
        r'\bLicense[\s:#]*[\w\d]{6,12}\b',
    ],
    
    # Patient names (when preceded by keywords)
    "patient_name": [
        r'\b(?:Patient|Member|Client)[\s:]+[A-Z][a-z]+\s+[A-Z][a-z]+\b',
        r'\b(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',
    ],
    
    # Address components
    "address": [
        r'\b\d{1,5}\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct)\b',
        r'\b(?:Apt|Suite|Unit)[\s#]*\d+\b',
    ],
    
    # Insurance IDs
    "insurance": [
        r'\b(?:Member ID|Insurance ID|Policy)[\s:#]*[\w\d]{8,15}\b',
        r'\b(?:Group)[\s:#]*[\w\d]{5,10}\b',
    ],
    
    # Prescription/RX numbers
    "prescription": [
        r'\bRX[\s:#]*\d{6,12}\b',
        r'\bRx[\s:#]*\d{6,12}\b',
        r'\bPrescription[\s:#]*\d{6,12}\b',
    ]
}

# Keywords that might indicate PHI context
PHI_CONTEXT_KEYWORDS = [
    "patient", "member", "client", "diagnosis", "medication", "prescription",
    "treatment", "medical", "health", "insurance", "claim", "provider",
    "doctor", "physician", "nurse", "hospital", "clinic", "appointment",
    "symptom", "condition", "disease", "allergy", "vaccine", "dose"
]

class PHIScrubber:
    """
    Scrubs Protected Health Information from text and data structures
    """
    
    def __init__(self, custom_patterns: Optional[Dict[str, List[str]]] = None):
        """
        Initialize PHI scrubber with optional custom patterns
        
        Args:
            custom_patterns: Additional patterns to scrub beyond defaults
        """
        self.patterns = PHI_PATTERNS.copy()
        if custom_patterns:
            self.patterns.update(custom_patterns)
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = {}
        for category, patterns in self.patterns.items():
            self.compiled_patterns[category] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def scrub_text(self, text: str, replacement: str = "[REDACTED]") -> str:
        """
        Scrub PHI from a text string
        
        Args:
            text: Input text potentially containing PHI
            replacement: String to replace PHI with
            
        Returns:
            Scrubbed text with PHI replaced
        """
        if not text:
            return text
        
        scrubbed = text
        
        # Apply all PHI patterns
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                # Use category-specific replacement for debugging
                category_replacement = f"[{category.upper()}-{replacement}]" if replacement == "[REDACTED]" else replacement
                scrubbed = pattern.sub(category_replacement, scrubbed)
        
        return scrubbed
    
    def scrub_dict(self, data: Dict[str, Any], sensitive_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Recursively scrub PHI from dictionary values
        
        Args:
            data: Dictionary potentially containing PHI
            sensitive_keys: Additional keys to fully redact
            
        Returns:
            Dictionary with PHI scrubbed from values
        """
        if not data:
            return data
        
        sensitive_keys = sensitive_keys or []
        sensitive_keys.extend([
            "ssn", "social_security", "mrn", "medical_record",
            "dob", "date_of_birth", "birth_date",
            "phone", "mobile", "cell", "fax",
            "email", "email_address",
            "address", "street", "city", "zip", "postal",
            "patient_name", "member_name", "name",
            "credit_card", "card_number",
            "insurance_id", "member_id", "policy_number"
        ])
        
        scrubbed_data = {}
        
        for key, value in data.items():
            # Check if key is sensitive
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                scrubbed_data[key] = "[REDACTED-FIELD]"
            elif isinstance(value, str):
                scrubbed_data[key] = self.scrub_text(value)
            elif isinstance(value, dict):
                scrubbed_data[key] = self.scrub_dict(value, sensitive_keys)
            elif isinstance(value, list):
                scrubbed_data[key] = self.scrub_list(value, sensitive_keys)
            else:
                scrubbed_data[key] = value
        
        return scrubbed_data
    
    def scrub_list(self, data: List[Any], sensitive_keys: Optional[List[str]] = None) -> List[Any]:
        """
        Scrub PHI from list elements
        
        Args:
            data: List potentially containing PHI
            sensitive_keys: Keys to consider sensitive in nested dicts
            
        Returns:
            List with PHI scrubbed
        """
        if not data:
            return data
        
        scrubbed_list = []
        
        for item in data:
            if isinstance(item, str):
                scrubbed_list.append(self.scrub_text(item))
            elif isinstance(item, dict):
                scrubbed_list.append(self.scrub_dict(item, sensitive_keys))
            elif isinstance(item, list):
                scrubbed_list.append(self.scrub_list(item, sensitive_keys))
            else:
                scrubbed_list.append(item)
        
        return scrubbed_list
    
    def scrub_json(self, json_str: str) -> str:
        """
        Scrub PHI from JSON string
        
        Args:
            json_str: JSON string potentially containing PHI
            
        Returns:
            JSON string with PHI scrubbed
        """
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                scrubbed = self.scrub_dict(data)
            elif isinstance(data, list):
                scrubbed = self.scrub_list(data)
            else:
                scrubbed = data
            return json.dumps(scrubbed)
        except json.JSONDecodeError:
            # If not valid JSON, treat as text
            return self.scrub_text(json_str)
    
    def has_phi(self, text: str) -> bool:
        """
        Check if text potentially contains PHI
        
        Args:
            text: Text to check
            
        Returns:
            True if PHI patterns detected
        """
        if not text:
            return False
        
        # Check for PHI patterns
        for patterns in self.compiled_patterns.values():
            for pattern in patterns:
                if pattern.search(text):
                    return True
        
        # Check for context keywords (lower confidence)
        text_lower = text.lower()
        keyword_count = sum(1 for keyword in PHI_CONTEXT_KEYWORDS if keyword in text_lower)
        if keyword_count >= 3:  # Multiple medical keywords suggest PHI context
            return True
        
        return False
    
    def get_phi_summary(self, text: str) -> Dict[str, int]:
        """
        Get summary of PHI types found in text (for debugging/auditing)
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with counts of each PHI type found
        """
        summary = {}
        
        for category, patterns in self.compiled_patterns.items():
            count = 0
            for pattern in patterns:
                matches = pattern.findall(text)
                count += len(matches)
            if count > 0:
                summary[category] = count
        
        return summary

# Global scrubber instance for convenience
_global_scrubber = PHIScrubber()

def scrub_text(text: str, replacement: str = "[REDACTED]") -> str:
    """
    Convenience function to scrub PHI from text
    
    Args:
        text: Input text
        replacement: Replacement string
        
    Returns:
        Scrubbed text
    """
    return _global_scrubber.scrub_text(text, replacement)

def scrub_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to scrub PHI from dictionary
    
    Args:
        data: Input dictionary
        
    Returns:
        Scrubbed dictionary
    """
    return _global_scrubber.scrub_dict(data)

def scrub_json(json_str: str) -> str:
    """
    Convenience function to scrub PHI from JSON
    
    Args:
        json_str: JSON string
        
    Returns:
        Scrubbed JSON string
    """
    return _global_scrubber.scrub_json(json_str)

def has_phi(text: str) -> bool:
    """
    Convenience function to check for PHI
    
    Args:
        text: Text to check
        
    Returns:
        True if PHI detected
    """
    return _global_scrubber.has_phi(text)

def safe_log(message: str, data: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a PHI-safe log message
    
    Args:
        message: Log message
        data: Optional data to include
        
    Returns:
        Safe log string with PHI scrubbed
    """
    safe_message = scrub_text(message)
    
    if data:
        safe_data = scrub_dict(data)
        return f"{safe_message} | Data: {json.dumps(safe_data)}"
    
    return safe_message

# Example usage and testing
if __name__ == "__main__":
    # Test PHI scrubbing
    test_cases = [
        "Patient John Doe, SSN: 123-45-6789, DOB: 01/15/1980",
        "MRN: 123456, Phone: (555) 123-4567",
        "Email: johndoe@example.com, Address: 123 Main Street",
        "Prescription RX:9876543, Insurance ID: ABC123456",
        {"patient_name": "Jane Smith", "ssn": "987-65-4321", "diagnosis": "Hypertension"},
        ["Patient: Bob Jones", "DOB: 12/25/1975", "Phone: 555-0123"]
    ]
    
    scrubber = PHIScrubber()
    
    print("PHI Scrubbing Tests:")
    print("-" * 50)
    
    for test in test_cases:
        if isinstance(test, str):
            print(f"Original: {test}")
            print(f"Scrubbed: {scrubber.scrub_text(test)}")
            print(f"Has PHI: {scrubber.has_phi(test)}")
            if scrubber.has_phi(test):
                print(f"PHI Types: {scrubber.get_phi_summary(test)}")
        elif isinstance(test, dict):
            print(f"Original Dict: {test}")
            print(f"Scrubbed Dict: {scrubber.scrub_dict(test)}")
        elif isinstance(test, list):
            print(f"Original List: {test}")
            print(f"Scrubbed List: {scrubber.scrub_list(test)}")
        print("-" * 50)