"""
Comprehensive Chat Response Test Suite
Tests deterministic responses, RAG functionality, language support, and edge cases
"""

import json
import time
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class TestResult:
    """Represents a single test result"""
    test_name: str
    category: str
    query: str
    language: str
    passed: bool
    response_time_ms: float
    response_text: str
    expected_keywords: List[str]
    found_keywords: List[str]
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "category": self.category,
            "query": self.query,
            "language": self.language,
            "passed": self.passed,
            "response_time_ms": round(self.response_time_ms, 2),
            "response_length": len(self.response_text),
            "expected_keywords": self.expected_keywords,
            "found_keywords": self.found_keywords,
            "error": self.error
        }

class ChatTestRunner:
    """Runs comprehensive chat tests against the API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_endpoint = f"{base_url}/api/kroger-chat"
        self.results: List[TestResult] = []
        self.session_id = f"test_session_{int(time.time())}"
        
    async def test_single_query(
        self, 
        query: str, 
        expected_keywords: List[str],
        language: str = "en",
        test_name: str = "",
        category: str = ""
    ) -> TestResult:
        """Test a single query against the API"""
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "query": query,
                    "session_id": self.session_id,
                    "language": language
                }
                
                async with session.post(self.api_endpoint, json=payload) as response:
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    if response.status != 200:
                        return TestResult(
                            test_name=test_name or query[:30],
                            category=category,
                            query=query,
                            language=language,
                            passed=False,
                            response_time_ms=response_time_ms,
                            response_text="",
                            expected_keywords=expected_keywords,
                            found_keywords=[],
                            error=f"HTTP {response.status}"
                        )
                    
                    data = await response.json()
                    response_text = data.get("response", data.get("answer", ""))
                    
                    # Check for expected keywords
                    response_lower = response_text.lower()
                    found_keywords = [kw for kw in expected_keywords if kw.lower() in response_lower]
                    
                    # Determine if test passed
                    passed = len(found_keywords) > 0 if expected_keywords else len(response_text) > 0
                    
                    return TestResult(
                        test_name=test_name or query[:30],
                        category=category,
                        query=query,
                        language=language,
                        passed=passed,
                        response_time_ms=response_time_ms,
                        response_text=response_text,
                        expected_keywords=expected_keywords,
                        found_keywords=found_keywords
                    )
                    
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_name=test_name or query[:30],
                category=category,
                query=query,
                language=language,
                passed=False,
                response_time_ms=response_time_ms,
                response_text="",
                expected_keywords=expected_keywords,
                found_keywords=[],
                error=str(e)
            )
    
    async def run_category_tests(self, category: str, tests: Dict[str, List[Dict]]) -> List[TestResult]:
        """Run all tests in a category"""
        category_results = []
        
        for test_type, test_cases in tests.items():
            for test_case in test_cases:
                if isinstance(test_case, dict):
                    query = test_case.get("query", "")
                    expected_keywords = test_case.get("expected_keywords", [])
                    language = test_case.get("language", "en")
                    expected_behavior = test_case.get("expected_behavior", None)
                    
                    # Handle special expected behaviors
                    if expected_behavior == "error_message":
                        expected_keywords = ["error", "invalid", "please"]
                    elif expected_behavior == "help_message":
                        expected_keywords = ["help", "assist", "service", "kroger"]
                    
                    result = await self.test_single_query(
                        query=query,
                        expected_keywords=expected_keywords,
                        language=language,
                        test_name=f"{test_type}_{len(category_results)}",
                        category=f"{category}/{test_type}"
                    )
                    
                    category_results.append(result)
                    self.results.append(result)
                    
                    # Small delay to avoid overwhelming the server
                    await asyncio.sleep(0.1)
        
        return category_results
    
    async def run_performance_tests(self, num_concurrent: int = 10) -> Dict[str, Any]:
        """Run performance tests with concurrent queries"""
        
        test_queries = [
            "what are your hours",
            "vaccine information",
            "pharmacy services",
            "insurance coverage",
            "medication refills"
        ]
        
        # Test concurrent requests
        start_time = time.time()
        tasks = []
        
        for i in range(num_concurrent):
            query = test_queries[i % len(test_queries)]
            task = self.test_single_query(
                query=query,
                expected_keywords=[],
                test_name=f"concurrent_{i}",
                category="performance"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000
        
        response_times = [r.response_time_ms for r in results if r.response_time_ms > 0]
        response_times.sort()
        
        return {
            "total_requests": num_concurrent,
            "total_time_ms": round(total_time, 2),
            "avg_response_time_ms": round(sum(response_times) / len(response_times), 2) if response_times else 0,
            "p50_response_time_ms": round(response_times[len(response_times) // 2], 2) if response_times else 0,
            "p95_response_time_ms": round(response_times[int(len(response_times) * 0.95)], 2) if response_times else 0,
            "max_response_time_ms": round(max(response_times), 2) if response_times else 0,
            "min_response_time_ms": round(min(response_times), 2) if response_times else 0,
            "success_rate": sum(1 for r in results if r.passed) / len(results) * 100 if results else 0
        }
    
    async def run_all_tests(self, test_config_path: str = "tests/test_queries.json") -> Dict[str, Any]:
        """Run all tests from configuration file"""
        
        # Load test configuration
        with open(test_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        test_categories = config.get("test_categories", {})
        
        print("Starting Comprehensive Chat Tests")
        print("=" * 60)
        
        all_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "base_url": self.base_url,
            "categories": {},
            "performance": {},
            "summary": {}
        }
        
        # Run tests for each category
        for category_name, category_data in test_categories.items():
            if category_name == "performance":
                continue  # Handle separately
                
            print(f"\nTesting {category_name}: {category_data.get('description', '')}")
            print("-" * 40)
            
            category_tests = category_data.get("tests", {})
            category_results = await self.run_category_tests(category_name, category_tests)
            
            # Calculate category statistics
            total_tests = len(category_results)
            passed_tests = sum(1 for r in category_results if r.passed)
            avg_response_time = sum(r.response_time_ms for r in category_results) / total_tests if total_tests > 0 else 0
            
            all_results["categories"][category_name] = {
                "description": category_data.get("description", ""),
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "avg_response_time_ms": round(avg_response_time, 2),
                "tests": [r.to_dict() for r in category_results]
            }
            
            print(f"[PASS] Passed: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
            print(f"[TIME] Avg Response Time: {avg_response_time:.2f}ms")
        
        # Run performance tests
        print(f"\nRunning Performance Tests")
        print("-" * 40)
        
        perf_requirements = test_categories.get("performance", {}).get("requirements", {})
        concurrent_users = perf_requirements.get("concurrent_users", 10)
        
        perf_results = await self.run_performance_tests(concurrent_users)
        all_results["performance"] = perf_results
        
        print(f"[OK] Concurrent Requests: {perf_results['total_requests']}")
        print(f"[P50] Response Time: {perf_results['p50_response_time_ms']}ms")
        print(f"[P95] Response Time: {perf_results['p95_response_time_ms']}ms")
        
        # Calculate overall summary
        total_tests = len(self.results)
        total_passed = sum(1 for r in self.results if r.passed)
        
        all_results["summary"] = {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_tests - total_passed,
            "overall_success_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0,
            "test_duration_seconds": round(sum(r.response_time_ms for r in self.results) / 1000, 2)
        }
        
        return all_results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of test results"""
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        summary = results.get("summary", {})
        print(f"Total Tests: {summary.get('total_tests', 0)}")
        print(f"Passed: {summary.get('total_passed', 0)}")
        print(f"Failed: {summary.get('total_failed', 0)}")
        print(f"Success Rate: {summary.get('overall_success_rate', 0):.1f}%")
        print(f"Total Duration: {summary.get('test_duration_seconds', 0):.2f}s")
        
        print("\nCategory Breakdown:")
        for category_name, category_data in results.get("categories", {}).items():
            print(f"  {category_name}: {category_data['passed']}/{category_data['total_tests']} passed ({category_data['success_rate']:.1f}%)")
        
        print("\nPerformance Metrics:")
        perf = results.get("performance", {})
        print(f"  P50 Response Time: {perf.get('p50_response_time_ms', 0)}ms")
        print(f"  P95 Response Time: {perf.get('p95_response_time_ms', 0)}ms")
        print(f"  Max Response Time: {perf.get('max_response_time_ms', 0)}ms")
        print(f"  Success Rate: {perf.get('success_rate', 0):.1f}%")


async def main():
    """Main test execution"""
    runner = ChatTestRunner()
    results = await runner.run_all_tests()
    
    # Save results to file
    with open("tests/test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Print summary
    runner.print_summary(results)
    
    # Return exit code based on success
    success_rate = results.get("summary", {}).get("overall_success_rate", 0)
    return 0 if success_rate >= 80 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)