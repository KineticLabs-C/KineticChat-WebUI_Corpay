#!/usr/bin/env python3
"""
Comprehensive Test Report Generator for KineticChat WebUI
Generates detailed input/output reports with timing and pass/fail analysis
Based on intent_test_report format from prototype
"""

import sys
import os
import json
import time
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configuration
API_URL = "http://localhost:8000/api/kroger-chat"
REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")

# Test categories with comprehensive test cases
TEST_CATEGORIES = {
    "Greetings & Basic Interaction": [
        {"message": "hello", "language": "en", "intent": "Greeting"},
        {"message": "hi there", "language": "en", "intent": "Greeting"},
        {"message": "good morning", "language": "en", "intent": "Greeting"},
        {"message": "hola", "language": "es", "intent": "Spanish Greeting"},
        {"message": "buenos días", "language": "es", "intent": "Spanish Greeting"},
    ],
    
    "Pharmacy Services": [
        {"message": "What are your hours?", "language": "en", "intent": "Hours Query"},
        {"message": "When are you open?", "language": "en", "intent": "Hours Query"},
        {"message": "Where is the pharmacy located?", "language": "en", "intent": "Location"},
        {"message": "What's the pharmacy phone number?", "language": "en", "intent": "Phone Number"},
        {"message": "Do you deliver?", "language": "en", "intent": "Delivery Info"},
        {"message": "¿Cuáles son sus horarios?", "language": "es", "intent": "Spanish Hours"},
    ],
    
    "Vaccinations": [
        {"message": "Do you have COVID vaccines?", "language": "en", "intent": "COVID Vaccine"},
        {"message": "Can I get a flu shot?", "language": "en", "intent": "Flu Shot"},
        {"message": "What vaccines do you offer?", "language": "en", "intent": "Vaccine List"},
        {"message": "How do I schedule a vaccine?", "language": "en", "intent": "Vaccine Appointment"},
        {"message": "Are vaccines free?", "language": "en", "intent": "Vaccine Cost"},
        {"message": "¿Tienen vacunas contra el COVID?", "language": "es", "intent": "Spanish COVID Vaccine"},
    ],
    
    "Prescription & Refills": [
        {"message": "How do I refill my prescription?", "language": "en", "intent": "Refill Process"},
        {"message": "Can I refill online?", "language": "en", "intent": "Online Refill"},
        {"message": "What's the status of my refill?", "language": "en", "intent": "Refill Status"},
        {"message": "Is my prescription ready?", "language": "en", "intent": "Prescription Ready"},
        {"message": "Can you transfer my prescription?", "language": "en", "intent": "Transfer Prescription"},
        {"message": "¿Cómo puedo renovar mi receta?", "language": "es", "intent": "Spanish Refill"},
    ],
    
    "Health Services": [
        {"message": "What health services do you offer?", "language": "en", "intent": "Services List"},
        {"message": "Do you do blood pressure checks?", "language": "en", "intent": "BP Check"},
        {"message": "Can I get a diabetes screening?", "language": "en", "intent": "Diabetes Screening"},
        {"message": "Tell me about your wellness programs", "language": "en", "intent": "Wellness Programs"},
        {"message": "Do you have a dietitian?", "language": "en", "intent": "Dietitian Services"},
        {"message": "¿Qué servicios de salud ofrecen?", "language": "es", "intent": "Spanish Services"},
    ],
    
    "Insurance & Payment": [
        {"message": "Do you accept my insurance?", "language": "en", "intent": "Insurance Coverage"},
        {"message": "What insurance plans do you take?", "language": "en", "intent": "Insurance Plans"},
        {"message": "How much does it cost?", "language": "en", "intent": "Cost Inquiry"},
        {"message": "Do you have payment plans?", "language": "en", "intent": "Payment Plans"},
        {"message": "Can I pay online?", "language": "en", "intent": "Online Payment"},
        {"message": "¿Aceptan mi seguro?", "language": "es", "intent": "Spanish Insurance"},
    ],
    
    "Complex Queries": [
        {"message": "I have diabetes and need help managing my medications", "language": "en", "intent": "Complex Health Query"},
        {"message": "What wellness programs are available for seniors?", "language": "en", "intent": "Senior Programs"},
        {"message": "How can Kroger Health help with my chronic conditions?", "language": "en", "intent": "Chronic Care"},
        {"message": "I need to find affordable medications", "language": "en", "intent": "Affordable Meds"},
        {"message": "Tell me about your specialty pharmacy services", "language": "en", "intent": "Specialty Pharmacy"},
    ],
    
    "Edge Cases & Error Handling": [
        {"message": "", "language": "en", "intent": "Empty Message"},
        {"message": "   ", "language": "en", "intent": "Whitespace Only"},
        {"message": "asdfghjkl", "language": "en", "intent": "Gibberish"},
        {"message": "1234567890", "language": "en", "intent": "Numbers Only"},
        {"message": "?????", "language": "en", "intent": "Special Characters"},
        {"message": "A" * 500, "language": "en", "intent": "Very Long Message"},
    ]
}

class ComprehensiveTestReport:
    """Generates comprehensive test reports with detailed analysis"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    async def run_single_test(self, test_case: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Run a single test case and return results"""
        
        session_id = f"test_{int(time.time() * 1000)}"
        body = {
            "query": test_case["message"],
            "language": test_case["language"],
            "session_id": session_id
        }
        
        result = {
            "category": category,
            "intent": test_case["intent"],
            "message": test_case["message"][:100],  # Truncate for display
            "language": test_case["language"],
            "status": "FAIL",
            "response": None,
            "duration_ms": 0,
            "error": None
        }
        
        try:
            start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=body, timeout=10) as response:
                    duration_ms = (time.time() - start) * 1000
                    result["duration_ms"] = duration_ms
                    
                    if response.status == 200:
                        data = await response.json()
                        result["response"] = data.get("response", "")[:500]  # Truncate
                        result["status"] = "PASS"
                        
                        # Validate response quality
                        if not result["response"] or len(result["response"]) < 10:
                            result["status"] = "FAIL"
                            result["error"] = "Response too short or empty"
                        elif test_case["language"] == "es" and not any(
                            spanish_word in result["response"].lower() 
                            for spanish_word in ["hola", "gracias", "farmacia", "salud", "servicio", "ayuda"]
                        ):
                            result["status"] = "WARN"
                            result["error"] = "Spanish response may be in English"
                    else:
                        result["error"] = f"HTTP {response.status}"
                        
        except asyncio.TimeoutError:
            result["error"] = "Timeout (>10s)"
        except Exception as e:
            result["error"] = str(e)[:100]
        
        return result
    
    async def run_all_tests(self) -> None:
        """Run all test categories"""
        self.start_time = datetime.now(timezone.utc)
        
        print("Starting Comprehensive Test Report Generation...")
        print(f"Total categories: {len(TEST_CATEGORIES)}")
        print("=" * 80)
        
        for category, test_cases in TEST_CATEGORIES.items():
            print(f"\nTesting: {category}")
            print("-" * 40)
            
            for test_case in test_cases:
                self.total_tests += 1
                result = await self.run_single_test(test_case, category)
                self.results.append(result)
                
                if result["status"] == "PASS":
                    self.passed_tests += 1
                    status_symbol = "[PASS]"
                elif result["status"] == "WARN":
                    self.passed_tests += 1  # Count warnings as passes
                    status_symbol = "[WARN]"
                else:
                    self.failed_tests += 1
                    status_symbol = "[FAIL]"
                
                print(f"  {status_symbol} {result['intent']}: {result['duration_ms']:.0f}ms")
        
        self.end_time = datetime.now(timezone.utc)
        print("\n" + "=" * 80)
        print("Test execution complete!")
    
    def generate_report(self) -> str:
        """Generate formatted test report"""
        duration = (self.end_time - self.start_time).total_seconds()
        pass_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        report = []
        report.append("=" * 80)
        report.append("COMPREHENSIVE TEST REPORT - KINETICCHAT WEBUI")
        report.append("=" * 80)
        report.append(f"Generated: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        report.append(f"Duration: {duration:.2f} seconds")
        report.append(f"Total Tests: {self.total_tests}")
        report.append(f"Passed: {self.passed_tests} ({pass_rate:.1f}%)")
        report.append(f"Failed: {self.failed_tests} ({100-pass_rate:.1f}%)")
        report.append("")
        report.append("=" * 80)
        report.append("DETAILED RESULTS BY CATEGORY")
        report.append("=" * 80)
        
        # Group results by category
        current_category = None
        for result in self.results:
            if result["category"] != current_category:
                current_category = result["category"]
                report.append("")
                report.append(f"## {current_category}")
                report.append("-" * 60)
                report.append("")
            
            status = f"[{result['status']}]"
            report.append(f"Intent: {result['intent']}")
            report.append(f"Status: {status}")
            report.append(f"Message: {result['message']}")
            
            if result['response']:
                # Clean up response for display
                response_lines = result['response'].replace('\n', ' ').strip()
                if len(response_lines) > 200:
                    response_lines = response_lines[:200] + "..."
                report.append(f"Response: {response_lines}")
            elif result['error']:
                report.append(f"Error: {result['error']}")
            
            report.append(f"Duration: {result['duration_ms']:.2f}ms")
            report.append("")
        
        # Summary statistics
        report.append("=" * 80)
        report.append("PERFORMANCE ANALYSIS")
        report.append("=" * 80)
        
        if self.results:
            durations = [r["duration_ms"] for r in self.results if r["duration_ms"] > 0]
            if durations:
                avg_duration = sum(durations) / len(durations)
                min_duration = min(durations)
                max_duration = max(durations)
                
                # Calculate percentiles
                sorted_durations = sorted(durations)
                p50_idx = len(sorted_durations) // 2
                p95_idx = int(len(sorted_durations) * 0.95)
                p50 = sorted_durations[p50_idx]
                p95 = sorted_durations[p95_idx] if p95_idx < len(sorted_durations) else sorted_durations[-1]
                
                report.append(f"Average Response Time: {avg_duration:.2f}ms")
                report.append(f"Minimum Response Time: {min_duration:.2f}ms")
                report.append(f"Maximum Response Time: {max_duration:.2f}ms")
                report.append(f"P50 (Median): {p50:.2f}ms")
                report.append(f"P95: {p95:.2f}ms")
        
        # Category performance
        report.append("")
        report.append("Category Performance:")
        category_stats = {}
        for result in self.results:
            cat = result["category"]
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "passed": 0, "failed": 0}
            category_stats[cat]["total"] += 1
            if result["status"] in ["PASS", "WARN"]:
                category_stats[cat]["passed"] += 1
            else:
                category_stats[cat]["failed"] += 1
        
        for cat, stats in category_stats.items():
            cat_pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            report.append(f"  {cat}: {stats['passed']}/{stats['total']} ({cat_pass_rate:.1f}%)")
        
        # Final verdict
        report.append("")
        report.append("=" * 80)
        report.append("PRODUCTION READINESS ASSESSMENT")
        report.append("=" * 80)
        
        if pass_rate >= 95:
            report.append("Grade: A - PRODUCTION READY")
            report.append("System demonstrates excellent stability and response quality.")
        elif pass_rate >= 85:
            report.append("Grade: B - NEARLY READY")
            report.append("System is stable but has minor issues to address.")
        elif pass_rate >= 70:
            report.append("Grade: C - NEEDS WORK")
            report.append("System requires attention to failed test cases.")
        else:
            report.append("Grade: F - NOT READY")
            report.append("System has significant issues requiring immediate attention.")
        
        report.append("")
        report.append(f"Overall Pass Rate: {pass_rate:.1f}%")
        report.append(f"Total Execution Time: {duration:.2f} seconds")
        report.append("")
        report.append("=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_report(self, report_content: str) -> str:
        """Save report to file with timestamp"""
        os.makedirs(REPORT_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_test_report_{timestamp}.txt"
        filepath = os.path.join(REPORT_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # Also save as JSON for programmatic access
        json_filename = f"comprehensive_test_report_{timestamp}.json"
        json_filepath = os.path.join(REPORT_DIR, json_filename)
        
        json_data = {
            "timestamp": self.start_time.isoformat() if self.start_time else None,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0,
            "total_tests": self.total_tests,
            "passed": self.passed_tests,
            "failed": self.failed_tests,
            "pass_rate": (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0,
            "results": self.results
        }
        
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        
        return filepath

async def main():
    """Main entry point"""
    
    # Check if server is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health", timeout=2) as response:
                if response.status != 200:
                    print("ERROR: Server not responding on port 8000")
                    print("Start server with: uvicorn app.main:app --reload")
                    return
    except Exception:
        print("ERROR: Cannot connect to server at http://localhost:8000")
        print("Start server with: uvicorn app.main:app --reload")
        return
    
    # Run comprehensive tests
    tester = ComprehensiveTestReport()
    await tester.run_all_tests()
    
    # Generate and save report
    report = tester.generate_report()
    filepath = tester.save_report(report)
    
    # Display report
    print("\n" + report)
    print(f"\nReport saved to: {filepath}")
    
    # Exit with appropriate code
    if tester.failed_tests == 0:
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)
    else:
        print(f"\n[WARNING] {tester.failed_tests} tests failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())