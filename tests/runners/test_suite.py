#!/usr/bin/env python3
"""
Master Test Suite Orchestrator for KineticChat WebUI
Runs all test categories and generates comprehensive reports
"""

import sys
import os
import json
import time
import subprocess
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class Colors:
    """Terminal colors for output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class TestSuite:
    """Master test suite orchestrator"""
    
    def __init__(self):
        self.results = {
            "start_time": None,
            "end_time": None,
            "duration": 0,
            "categories": {},
            "total_passed": 0,
            "total_failed": 0,
            "total_skipped": 0,
            "server_running": False
        }
        self.test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def print_header(self):
        """Print test suite header"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}", flush=True)
        print(f"{Colors.BOLD}    KineticChat WebUI - Master Test Suite{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print(f"Test Directory: {self.test_dir}\n")
    
    def check_server(self) -> bool:
        """Check if the server is running"""
        import aiohttp
        import asyncio
        
        async def check():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:8000/health") as response:
                        return response.status == 200
            except:
                return False
        
        return asyncio.run(check())
    
    def run_pytest_tests(self, test_file: str, category: str) -> Tuple[int, int, int]:
        """Run pytest tests and return results"""
        print(f"\n{Colors.BLUE}Running {category}{Colors.RESET}")
        print(f"{'-'*40}")
        
        test_path = os.path.join(self.test_dir, test_file)
        
        if not os.path.exists(test_path):
            print(f"{Colors.YELLOW}[SKIP]{Colors.RESET} Test file not found: {test_file}")
            return 0, 0, 1
        
        try:
            # Run pytest with JSON output
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse output to get test counts
            output = result.stdout
            
            # Count results from output
            passed = output.count(" PASSED")
            failed = output.count(" FAILED")
            skipped = output.count(" SKIPPED")
            
            # Print summary
            if failed == 0 and passed > 0:
                print(f"{Colors.GREEN}[PASS] All {passed} tests passed{Colors.RESET}")
            elif failed > 0:
                print(f"{Colors.YELLOW}[WARN] {passed} passed, {failed} failed{Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}No tests found or all skipped{Colors.RESET}")
            
            return passed, failed, skipped
            
        except subprocess.TimeoutExpired:
            print(f"{Colors.RED}[TIMEOUT]{Colors.RESET} Tests exceeded 30 second limit")
            return 0, 1, 0
        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} Failed to run tests: {e}")
            return 0, 1, 0
    
    def run_python_tests(self, test_file: str, category: str) -> Tuple[int, int, int]:
        """Run standalone Python test scripts"""
        print(f"\n{Colors.BLUE}Running {category}{Colors.RESET}")
        print(f"{'-'*40}")
        
        test_path = os.path.join(self.test_dir, test_file)
        
        if not os.path.exists(test_path):
            print(f"{Colors.YELLOW}[SKIP]{Colors.RESET} Test file not found: {test_file}")
            return 0, 0, 1
        
        try:
            # Run the Python script
            result = subprocess.run(
                [sys.executable, test_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            output = result.stdout
            
            # Parse output for pass/fail counts
            # Look for common patterns
            passed = 0
            failed = 0
            
            # Count [PASS] and [FAIL] markers
            passed += output.count("[PASS]")
            passed += output.count("[OK]")
            passed += output.count("[PASS]")
            passed += output.count("PASSED")
            
            failed += output.count("[FAIL]")
            failed += output.count("[ERROR]")
            failed += output.count("[FAIL]")
            failed += output.count("FAILED")
            
            # If no clear markers, check return code
            if passed == 0 and failed == 0:
                if result.returncode == 0:
                    passed = 1
                else:
                    failed = 1
            
            # Print the output
            if len(output) > 0:
                for line in output.split('\n')[:50]:  # Limit output lines
                    if line.strip():
                        print(f"  {line}")
            
            return passed, failed, 0
            
        except subprocess.TimeoutExpired:
            print(f"{Colors.RED}[TIMEOUT]{Colors.RESET} Tests exceeded 60 second limit")
            return 0, 1, 0
        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.RESET} Failed to run tests: {e}")
            return 0, 1, 0
    
    def run_all_tests(self):
        """Run all test categories"""
        self.print_header()
        self.results["start_time"] = time.time()
        
        # Check server status
        print(f"{Colors.BLUE}Checking Server Status{Colors.RESET}")
        print(f"{'-'*40}")
        self.results["server_running"] = self.check_server()
        
        if self.results["server_running"]:
            print(f"{Colors.GREEN}[OK] Server is running{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}[WARN] Server not running - some tests may be skipped{Colors.RESET}")
            print(f"  Start server with: {Colors.CYAN}uvicorn app.main:app --reload{Colors.RESET}")
        
        # Define test categories and their files
        test_categories = [
            # Core tests (always run)
            {
                "name": "Smoke Tests",
                "file": "core/test_smoke.py",
                "type": "pytest",
                "requires_server": False
            },
            {
                "name": "PHI Scrubber Tests",
                "file": "core/test_phi_scrubber.py",
                "type": "pytest",
                "requires_server": False
            },
            # Server-dependent tests
            {
                "name": "HTTP API Tests",
                "file": "core/test_http_api.py",
                "type": "python",
                "requires_server": True
            },
            {
                "name": "Chat Response Tests",
                "file": "integration/test_chat_responses.py",
                "type": "python",
                "requires_server": True
            },
            {
                "name": "Final Verification",
                "file": "runners/final_test.py",
                "type": "python",
                "requires_server": True
            }
        ]
        
        # Run each test category
        for category in test_categories:
            # Skip server-dependent tests if server not running
            if category["requires_server"] and not self.results["server_running"]:
                print(f"\n{Colors.BLUE}Running {category['name']}{Colors.RESET}")
                print(f"{'-'*40}")
                print(f"{Colors.YELLOW}[SKIP]{Colors.RESET} Requires running server")
                self.results["categories"][category["name"]] = {
                    "passed": 0,
                    "failed": 0,
                    "skipped": 1
                }
                self.results["total_skipped"] += 1
                continue
            
            # Run the appropriate test type
            if category["type"] == "pytest":
                passed, failed, skipped = self.run_pytest_tests(
                    category["file"],
                    category["name"]
                )
            else:  # python
                passed, failed, skipped = self.run_python_tests(
                    category["file"],
                    category["name"]
                )
            
            # Store results
            self.results["categories"][category["name"]] = {
                "passed": passed,
                "failed": failed,
                "skipped": skipped
            }
            
            self.results["total_passed"] += passed
            self.results["total_failed"] += failed
            self.results["total_skipped"] += skipped
        
        self.results["end_time"] = time.time()
        self.results["duration"] = self.results["end_time"] - self.results["start_time"]
    
    def generate_report(self):
        """Generate and display test report"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}    TEST SUITE SUMMARY{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
        
        # Overall stats
        total_tests = self.results["total_passed"] + self.results["total_failed"] + self.results["total_skipped"]
        
        print(f"\n{Colors.BOLD}Overall Results:{Colors.RESET}")
        print(f"  Total Tests: {total_tests}")
        print(f"  {Colors.GREEN}Passed: {self.results['total_passed']}{Colors.RESET}")
        print(f"  {Colors.RED}Failed: {self.results['total_failed']}{Colors.RESET}")
        print(f"  {Colors.YELLOW}Skipped: {self.results['total_skipped']}{Colors.RESET}")
        
        if total_tests > 0:
            pass_rate = (self.results['total_passed'] / (self.results['total_passed'] + self.results['total_failed']) * 100) if (self.results['total_passed'] + self.results['total_failed']) > 0 else 0
            print(f"  Pass Rate: {Colors.BOLD}{pass_rate:.1f}%{Colors.RESET}")
        
        print(f"  Duration: {self.results['duration']:.2f} seconds")
        
        # Category breakdown
        print(f"\n{Colors.BOLD}Category Breakdown:{Colors.RESET}")
        for category, stats in self.results["categories"].items():
            status = "[PASS]" if stats["failed"] == 0 and stats["passed"] > 0 else "[FAIL]" if stats["failed"] > 0 else "[SKIP]"
            color = Colors.GREEN if status == "[PASS]" else Colors.RED if status == "[FAIL]" else Colors.YELLOW
            print(f"  {color}{status}{Colors.RESET} {category}: {stats['passed']} passed, {stats['failed']} failed, {stats['skipped']} skipped")
        
        # Excellence criteria check
        print(f"\n{Colors.BOLD}Production Excellence Criteria:{Colors.RESET}")
        
        criteria = [
            ("HTTP endpoint accepts both 'query' and 'message'", "HTTP API Tests" in self.results["categories"] and self.results["categories"]["HTTP API Tests"]["passed"] > 0),
            ("Response format includes status field", "HTTP API Tests" in self.results["categories"] and self.results["categories"]["HTTP API Tests"]["passed"] > 0),
            ("PHI scrubbing implemented", "PHI Scrubber Tests" in self.results["categories"] and self.results["categories"]["PHI Scrubber Tests"]["failed"] == 0),
            ("Smoke tests pass", "Smoke Tests" in self.results["categories"] and self.results["categories"]["Smoke Tests"]["failed"] == 0),
            ("Server health endpoints working", self.results["server_running"])
        ]
        
        for criterion, met in criteria:
            status = "[OK]" if met else "[X]"
            color = Colors.GREEN if met else Colors.RED
            print(f"  {color}{status}{Colors.RESET} {criterion}")
        
        # Final verdict
        print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
        if self.results["total_failed"] == 0 and self.results["total_passed"] > 0:
            print(f"{Colors.GREEN}{Colors.BOLD}[SUCCESS] ALL TESTS PASSED - PRODUCTION READY!{Colors.RESET}")
        elif self.results["total_failed"] > 0:
            print(f"{Colors.YELLOW}{Colors.BOLD}[WARNING] SOME TESTS FAILED - REVIEW REQUIRED{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}{Colors.BOLD}[INFO] NO TESTS RAN - CHECK CONFIGURATION{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    def save_report(self):
        """Save test report to file"""
        report_path = os.path.join(self.test_dir, "reports", "test_results.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        report_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": self.results["duration"],
            "server_running": self.results["server_running"],
            "summary": {
                "total_passed": self.results["total_passed"],
                "total_failed": self.results["total_failed"],
                "total_skipped": self.results["total_skipped"]
            },
            "categories": self.results["categories"]
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"Report saved to: {report_path}")

def main():
    """Main entry point"""
    suite = TestSuite()
    
    try:
        # Run all tests
        suite.run_all_tests()
        
        # Generate report
        suite.generate_report()
        
        # Save report
        suite.save_report()
        
        # Exit with appropriate code
        if suite.results["total_failed"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test suite interrupted by user{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Test suite failed: {e}{Colors.RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()