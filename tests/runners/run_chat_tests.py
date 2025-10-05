#!/usr/bin/env python3
"""
Automated Chat Test Runner
Executes comprehensive test suite and generates detailed reports
"""

import sys
import os
import json
import asyncio
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_chat_responses import ChatTestRunner

def generate_html_report(results: dict, output_path: str = "tests/test_report.html"):
    """Generate an HTML report from test results"""
    
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KineticChat Test Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .header .subtitle {
            opacity: 0.9;
            margin-top: 10px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .summary-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .summary-card .label {
            color: #666;
            margin-top: 5px;
        }
        .category-section {
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .category-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }
        .category-title {
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
        }
        .test-table {
            width: 100%;
            border-collapse: collapse;
        }
        .test-table th {
            background: #f8f8f8;
            padding: 10px;
            text-align: left;
            border-bottom: 2px solid #e0e0e0;
        }
        .test-table td {
            padding: 10px;
            border-bottom: 1px solid #f0f0f0;
        }
        .test-passed {
            color: #22c55e;
            font-weight: bold;
        }
        .test-failed {
            color: #ef4444;
            font-weight: bold;
        }
        .performance-section {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-bar {
            display: flex;
            align-items: center;
            margin: 10px 0;
        }
        .metric-label {
            width: 150px;
            font-weight: 500;
        }
        .metric-value {
            background: #667eea;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            margin-left: 10px;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #666;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: bold;
        }
        .status-success {
            background: #dcfce7;
            color: #166534;
        }
        .status-warning {
            background: #fed7aa;
            color: #92400e;
        }
        .status-error {
            background: #fee2e2;
            color: #991b1b;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 KineticChat Test Report</h1>
        <div class="subtitle">Generated: {timestamp}</div>
        <div class="subtitle">Environment: {base_url}</div>
    </div>
    
    <div class="summary-grid">
        <div class="summary-card">
            <div class="value">{total_tests}</div>
            <div class="label">Total Tests</div>
        </div>
        <div class="summary-card">
            <div class="value" style="color: #22c55e">{total_passed}</div>
            <div class="label">Passed</div>
        </div>
        <div class="summary-card">
            <div class="value" style="color: #ef4444">{total_failed}</div>
            <div class="label">Failed</div>
        </div>
        <div class="summary-card">
            <div class="value">{success_rate:.1f}%</div>
            <div class="label">Success Rate</div>
        </div>
    </div>
    
    {category_sections}
    
    <div class="performance-section">
        <h2>⚡ Performance Metrics</h2>
        {performance_metrics}
    </div>
    
    <div class="footer">
        <p>KineticChat WebUI Test Suite v1.0</p>
        <p>Test Duration: {test_duration}s</p>
    </div>
</body>
</html>
    """
    
    # Generate category sections
    category_html = ""
    for category_name, category_data in results.get("categories", {}).items():
        status_class = "status-success" if category_data["success_rate"] >= 90 else "status-warning" if category_data["success_rate"] >= 70 else "status-error"
        
        test_rows = ""
        for test in category_data.get("tests", [])[:10]:  # Show first 10 tests
            status = "✅ PASS" if test["passed"] else "❌ FAIL"
            status_class_test = "test-passed" if test["passed"] else "test-failed"
            test_rows += f"""
            <tr>
                <td>{test['query'][:50]}...</td>
                <td>{test['language'].upper()}</td>
                <td class="{status_class_test}">{status}</td>
                <td>{test['response_time_ms']}ms</td>
                <td>{', '.join(test['found_keywords'][:3])}</td>
            </tr>
            """
        
        category_html += f"""
        <div class="category-section">
            <div class="category-header">
                <div class="category-title">{category_name.replace('_', ' ').title()}</div>
                <div>
                    <span class="status-badge {status_class}">{category_data['passed']}/{category_data['total_tests']} passed</span>
                    <span class="status-badge status-success">{category_data['avg_response_time_ms']}ms avg</span>
                </div>
            </div>
            <p>{category_data['description']}</p>
            <table class="test-table">
                <thead>
                    <tr>
                        <th>Query</th>
                        <th>Language</th>
                        <th>Status</th>
                        <th>Response Time</th>
                        <th>Keywords Found</th>
                    </tr>
                </thead>
                <tbody>
                    {test_rows}
                </tbody>
            </table>
        </div>
        """
    
    # Generate performance metrics
    perf = results.get("performance", {})
    performance_html = f"""
    <div class="metric-bar">
        <span class="metric-label">P50 Response Time:</span>
        <span class="metric-value">{perf.get('p50_response_time_ms', 0)}ms</span>
    </div>
    <div class="metric-bar">
        <span class="metric-label">P95 Response Time:</span>
        <span class="metric-value">{perf.get('p95_response_time_ms', 0)}ms</span>
    </div>
    <div class="metric-bar">
        <span class="metric-label">Max Response Time:</span>
        <span class="metric-value">{perf.get('max_response_time_ms', 0)}ms</span>
    </div>
    <div class="metric-bar">
        <span class="metric-label">Concurrent Users:</span>
        <span class="metric-value">{perf.get('total_requests', 0)}</span>
    </div>
    <div class="metric-bar">
        <span class="metric-label">Success Rate:</span>
        <span class="metric-value">{perf.get('success_rate', 0):.1f}%</span>
    </div>
    """
    
    # Fill in the template
    summary = results.get("summary", {})
    html_content = html_template.format(
        timestamp=results.get("timestamp", datetime.now(timezone.utc).isoformat()),
        base_url=results.get("base_url", "http://localhost:8000"),
        total_tests=summary.get("total_tests", 0),
        total_passed=summary.get("total_passed", 0),
        total_failed=summary.get("total_failed", 0),
        success_rate=summary.get("overall_success_rate", 0),
        category_sections=category_html,
        performance_metrics=performance_html,
        test_duration=summary.get("test_duration_seconds", 0)
    )
    
    # Write HTML report
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"[HTML] Report generated: {output_path}")


def generate_markdown_report(results: dict, output_path: str = "tests/TEST_REPORT.md"):
    """Generate a Markdown report from test results"""
    
    md_content = f"""# KineticChat WebUI Test Report

Generated: {results.get('timestamp', datetime.now(timezone.utc).isoformat())}
Environment: {results.get('base_url', 'http://localhost:8000')}

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | {results['summary']['total_tests']} |
| **Passed** | {results['summary']['total_passed']} ✅ |
| **Failed** | {results['summary']['total_failed']} ❌ |
| **Success Rate** | {results['summary']['overall_success_rate']:.1f}% |
| **Test Duration** | {results['summary']['test_duration_seconds']:.2f}s |

## 📋 Category Results

"""
    
    for category_name, category_data in results.get("categories", {}).items():
        md_content += f"""### {category_name.replace('_', ' ').title()}

**Description:** {category_data['description']}
**Results:** {category_data['passed']}/{category_data['total_tests']} passed ({category_data['success_rate']:.1f}%)
**Average Response Time:** {category_data['avg_response_time_ms']}ms

| Query | Language | Status | Response Time | Keywords Found |
|-------|----------|--------|---------------|----------------|
"""
        
        for test in category_data.get("tests", [])[:10]:
            status = "✅" if test["passed"] else "❌"
            keywords = ", ".join(test['found_keywords'][:3]) if test['found_keywords'] else "None"
            query_short = test['query'][:40] + "..." if len(test['query']) > 40 else test['query']
            md_content += f"| {query_short} | {test['language'].upper()} | {status} | {test['response_time_ms']}ms | {keywords} |\n"
        
        md_content += "\n"
    
    # Add performance section
    perf = results.get("performance", {})
    md_content += f"""## ⚡ Performance Metrics

| Metric | Value |
|--------|-------|
| **P50 Response Time** | {perf.get('p50_response_time_ms', 0)}ms |
| **P95 Response Time** | {perf.get('p95_response_time_ms', 0)}ms |
| **Max Response Time** | {perf.get('max_response_time_ms', 0)}ms |
| **Min Response Time** | {perf.get('min_response_time_ms', 0)}ms |
| **Average Response Time** | {perf.get('avg_response_time_ms', 0)}ms |
| **Concurrent Requests** | {perf.get('total_requests', 0)} |
| **Success Rate** | {perf.get('success_rate', 0):.1f}% |

## 🎯 Test Configuration

Tests were run using the configuration from `test_queries.json` which includes:
- Deterministic response tests
- RAG-powered query tests
- Spanish language tests
- Edge case handling
- Performance benchmarks

---
*KineticChat WebUI Test Suite v1.0*
"""
    
    # Write Markdown report
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print(f"[MD] Report generated: {output_path}")


async def main():
    """Main test runner"""
    
    parser = argparse.ArgumentParser(description="Run KineticChat WebUI tests")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the service")
    parser.add_argument("--config", default="tests/test_queries.json", help="Path to test configuration")
    parser.add_argument("--output-json", default="tests/test_results.json", help="Path for JSON output")
    parser.add_argument("--output-html", default="tests/test_report.html", help="Path for HTML report")
    parser.add_argument("--output-md", default="tests/TEST_REPORT.md", help="Path for Markdown report")
    parser.add_argument("--no-html", action="store_true", help="Skip HTML report generation")
    parser.add_argument("--no-md", action="store_true", help="Skip Markdown report generation")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("KineticChat WebUI Test Suite")
    print("=" * 60)
    print(f"Target: {args.url}")
    print(f"Config: {args.config}")
    print()
    
    # Check if service is running
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{args.url}/health") as response:
                if response.status != 200:
                    print(f"[ERROR] Service is not responding at {args.url}")
                    print("Please start the service with: uvicorn app.main:app --reload")
                    return 1
                print("[OK] Service is running and healthy")
    except Exception as e:
        print(f"[ERROR] Cannot connect to service: {e}")
        print("Please start the service with: uvicorn app.main:app --reload")
        return 1
    
    # Run tests
    runner = ChatTestRunner(base_url=args.url)
    results = await runner.run_all_tests(test_config_path=args.config)
    
    # Save JSON results
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[SAVED] JSON results saved: {args.output_json}")
    
    # Generate HTML report
    if not args.no_html:
        generate_html_report(results, args.output_html)
    
    # Generate Markdown report
    if not args.no_md:
        generate_markdown_report(results, args.output_md)
    
    # Print summary
    print("\n" + "=" * 60)
    runner.print_summary(results)
    
    # Determine exit code
    success_rate = results.get("summary", {}).get("overall_success_rate", 0)
    if success_rate >= 90:
        print("\n[PASSED] TEST SUITE PASSED - Excellent!")
        return 0
    elif success_rate >= 70:
        print("\n[WARNING] TEST SUITE PASSED WITH WARNINGS")
        return 0
    else:
        print("\n[FAILED] TEST SUITE FAILED - Needs attention")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)