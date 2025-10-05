#!/usr/bin/env python3
"""
Test Response Parity
Comprehensive tests to verify response consistency with original system
Tests: Location precedence, fuzzy matching, Spanish translation, RAG expansion, Sources
"""

import asyncio
import requests
import json
import time
from typing import Dict, Any, List

BASE_URL = "http://localhost:8000"

class ResponseParityTests:
    """Test suite for verifying response parity with original system"""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    def test_endpoint(self, query: str, language: str = "en") -> Dict[str, Any]:
        """Send test query to endpoint"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/kroger-chat",
                json={"query": query, "language": language},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("response", ""),
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
            else:
                return {
                    "success": False,
                    "error": f"Status {response.status_code}",
                    "status_code": response.status_code
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def run_test(self, test_name: str, query: str, language: str, 
                 expected_patterns: List[str], test_type: str = "deterministic"):
        """Run a single test and check for expected patterns"""
        print(f"\n[TEST] {test_name}")
        print(f"  Query: '{query}' (Language: {language})")
        
        result = self.test_endpoint(query, language)
        
        if not result["success"]:
            print(f"  [FAIL] Error: {result.get('error')}")
            self.failed += 1
            self.results.append({
                "test": test_name,
                "status": "FAILED",
                "error": result.get("error")
            })
            return False
        
        response = result["response"].lower()
        patterns_found = []
        patterns_missing = []
        
        for pattern in expected_patterns:
            if pattern.lower() in response:
                patterns_found.append(pattern)
            else:
                patterns_missing.append(pattern)
        
        if patterns_missing:
            print(f"  [FAIL] Missing patterns: {patterns_missing}")
            # Handle Unicode encoding for Windows console
            try:
                print(f"  Response preview: {response[:200]}...")
            except UnicodeEncodeError:
                safe_response = response.encode('ascii', 'ignore').decode('ascii')
                print(f"  Response preview: {safe_response[:200]}...")
            self.failed += 1
            self.results.append({
                "test": test_name,
                "status": "FAILED",
                "missing": patterns_missing,
                "response_preview": response[:200]
            })
            return False
        else:
            print(f"  [PASS] All patterns found")
            print(f"  Response time: {result['response_time']:.2f}s")
            self.passed += 1
            self.results.append({
                "test": test_name,
                "status": "PASSED",
                "response_time": result['response_time']
            })
            return True
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("=" * 80)
        print("RESPONSE PARITY TEST SUITE")
        print("=" * 80)
        
        # Test 1: Location queries handled FIRST (before RAG)
        print("\n[CATEGORY] Location Precedence Tests")
        self.run_test(
            "Location with 'pharmacy' keyword",
            "Where is the nearest pharmacy?",
            "en",
            ["kroger.com/stores/search", "2,200 locations"],
            "deterministic"
        )
        
        self.run_test(
            "Spanish location query",
            "Donde esta la farmacia mas cercana?",
            "es",
            ["kroger.com/stores/search", "2,200 ubicaciones"],
            "deterministic"
        )
        
        # Test 2: Fuzzy matching for typos
        print("\n[CATEGORY] Fuzzy Matching Tests")
        self.run_test(
            "Typo in 'where'",
            "wher is the nearst pharmacy",
            "en",
            ["kroger.com/stores/search"],
            "deterministic"
        )
        
        self.run_test(
            "Typo in hours query",
            "what r ur hors",
            "en",
            ["7 a.m. - Midnight EST", "Monday-Friday"],
            "deterministic"
        )
        
        # Test 3: Spanish accent normalization
        print("\n[CATEGORY] Spanish Accent Normalization")
        self.run_test(
            "Query without accents",
            "cual es el horario de atencion",
            "es",
            ["Lunes-Viernes", "7 a.m. - Medianoche"],
            "deterministic"
        )
        
        self.run_test(
            "Query with accents",
            "cuál es el horario de atención",
            "es",
            ["Lunes-Viernes", "7 a.m. - Medianoche"],
            "deterministic"
        )
        
        # Test 4: RAG queries with Sources section
        print("\n[CATEGORY] RAG Enhancement Tests")
        self.run_test(
            "Vaccine query (should use RAG)",
            "Tell me about COVID vaccines",
            "en",
            ["Sources:"],  # Should have sources section
            "rag"
        )
        
        self.run_test(
            "Spanish vaccine query",
            "Información sobre vacunas COVID",
            "es",
            ["Sources:"],  # Should have sources even in Spanish
            "rag"
        )
        
        # Test 5: Query expansion working
        print("\n[CATEGORY] Query Expansion Tests")
        self.run_test(
            "Query with 'medication'",
            "How do I manage my medications?",
            "en",
            ["Sources:"],  # RAG should find related content
            "rag"
        )
        
        # Test 6: Deterministic patterns that should NOT use RAG
        print("\n[CATEGORY] Non-RAG Deterministic Tests")
        self.run_test(
            "Simple greeting",
            "Hello",
            "en",
            ["Kroger Health Assistant", "How can I assist"],
            "deterministic"
        )
        
        self.run_test(
            "Phone number query",
            "What's your phone number?",
            "en",
            ["1-800-922-7538"],
            "deterministic"
        )
        
        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        
        # Print failed tests details
        if self.failed > 0:
            print("\n[FAILED TESTS DETAILS]")
            for result in self.results:
                if result["status"] == "FAILED":
                    print(f"- {result['test']}: {result.get('error') or result.get('missing')}")
        
        return self.passed, self.failed

def main():
    """Run the response parity test suite"""
    print("Starting Response Parity Tests...")
    print("Ensure the server is running at http://localhost:8000")
    print("-" * 80)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("[ERROR] Server health check failed")
            return
    except Exception as e:
        print(f"[ERROR] Cannot connect to server: {e}")
        print("Please start the server with: uvicorn app.main:app --reload")
        return
    
    # Run tests
    tester = ResponseParityTests()
    passed, failed = tester.run_all_tests()
    
    # Return exit code based on results
    exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()