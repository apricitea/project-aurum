#!/usr/bin/env python3
"""
Load Testing Framework for Project Aurum
Indonesian Quantitative Trading System - Peak Market Volume Testing

Simulates realistic IDX trading scenarios during peak hours:
- Market open rush (09:00-09:30 WIB)
- Pre-lunch volume spike (11:30-12:00 WIB)
- Post-lunch trading (13:30-14:00 WIB)
- Market close rush (15:30-15:49 WIB)
"""

import asyncio
import aiohttp
import time
import json
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import argparse
import logging
import sys
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('load_test_results.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    endpoint: str
    response_time: float
    status_code: int
    success: bool
    timestamp: datetime
    error_message: str = None

@dataclass
class LoadTestConfig:
    base_url: str = "http://localhost:8000"
    concurrent_users: int = 100
    test_duration_seconds: int = 300
    ramp_up_time: int = 30
    think_time_min: float = 0.5
    think_time_max: float = 2.0
    timeout: int = 30

class IndonesianMarketLoadTester:
    """
    Comprehensive load testing for Indonesian stock market scenarios
    """

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.results: List[TestResult] = []
        self.access_token = None

        # Indonesian market specific data
        self.idx_stocks = [
            "BBCA.JK", "BMRI.JK", "BBRI.JK", "TLKM.JK", "ASII.JK",
            "UNVR.JK", "ICBP.JK", "KLBF.JK", "INTP.JK", "GGRM.JK",
            "HMSP.JK", "CPIN.JK", "SMGR.JK", "ADRO.JK", "PTBA.JK"
        ]

        # Trading session patterns based on IDX schedule
        self.trading_sessions = {
            "pre_open": {"start": "08:45", "end": "09:00", "intensity": 0.6},
            "morning_rush": {"start": "09:00", "end": "09:30", "intensity": 1.0},
            "morning_trading": {"start": "09:30", "end": "11:30", "intensity": 0.7},
            "pre_lunch": {"start": "11:30", "end": "12:00", "intensity": 0.9},
            "lunch_break": {"start": "12:00", "end": "13:30", "intensity": 0.1},
            "afternoon_open": {"start": "13:30", "end": "14:00", "intensity": 0.8},
            "afternoon_trading": {"start": "14:00", "end": "15:30", "intensity": 0.6},
            "closing_rush": {"start": "15:30", "end": "15:49", "intensity": 1.0},
            "post_close": {"start": "15:50", "end": "16:00", "intensity": 0.3}
        }

    async def authenticate(self, session: aiohttp.ClientSession) -> bool:
        """Authenticate user and get access token"""
        try:
            auth_data = {
                "username": "trader",
                "password": "trader123"
            }

            async with session.post(
                f"{self.config.base_url}/auth/login",
                json=auth_data,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.access_token = data.get("access_token")
                    return True
                else:
                    logger.error(f"Authentication failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False

    def get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def make_request(self, session: aiohttp.ClientSession, endpoint: str, method: str = "GET", data: Dict = None) -> TestResult:
        """Make HTTP request and record performance metrics"""
        start_time = time.time()

        try:
            url = f"{self.config.base_url}{endpoint}"
            headers = self.get_headers()

            if method.upper() == "GET":
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as response:
                    await response.text()  # Ensure full response is read
                    response_time = time.time() - start_time

                    return TestResult(
                        endpoint=endpoint,
                        response_time=response_time,
                        status_code=response.status,
                        success=200 <= response.status < 300,
                        timestamp=datetime.now()
                    )
            elif method.upper() == "POST":
                async with session.post(url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as response:
                    await response.text()
                    response_time = time.time() - start_time

                    return TestResult(
                        endpoint=endpoint,
                        response_time=response_time,
                        status_code=response.status,
                        success=200 <= response.status < 300,
                        timestamp=datetime.now()
                    )

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return TestResult(
                endpoint=endpoint,
                response_time=response_time,
                status_code=0,
                success=False,
                timestamp=datetime.now(),
                error_message="Timeout"
            )
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                endpoint=endpoint,
                response_time=response_time,
                status_code=0,
                success=False,
                timestamp=datetime.now(),
                error_message=str(e)
            )

    async def user_session(self, user_id: int, session_duration: int):
        """Simulate a realistic user trading session"""
        async with aiohttp.ClientSession() as session:
            # Authenticate user
            if not await self.authenticate(session):
                logger.error(f"User {user_id} authentication failed")
                return

            session_start = time.time()
            session_end = session_start + session_duration

            # Define realistic user journey patterns
            user_patterns = [
                # Dashboard monitoring pattern (most common)
                {
                    "weight": 0.4,
                    "endpoints": [
                        "/signals/daily",
                        "/portfolio/summary",
                        "/portfolio/positions",
                        "/market/status",
                        "/alerts"
                    ]
                },
                # Active trading pattern
                {
                    "weight": 0.3,
                    "endpoints": [
                        "/signals/daily",
                        "/portfolio/positions",
                        "/risk/overview",
                        "/analytics/performance",
                        "/market/status"
                    ]
                },
                # Research and analysis pattern
                {
                    "weight": 0.2,
                    "endpoints": [
                        "/analytics/performance",
                        "/risk/overview",
                        "/signals/daily",
                        "/market/status"
                    ]
                },
                # Quick check pattern
                {
                    "weight": 0.1,
                    "endpoints": [
                        "/portfolio/summary",
                        "/alerts",
                        "/market/status"
                    ]
                }
            ]

            # Select user pattern based on weights
            pattern = random.choices(user_patterns, weights=[p["weight"] for p in user_patterns])[0]

            while time.time() < session_end:
                # Randomly select endpoint from user's pattern
                endpoint = random.choice(pattern["endpoints"])

                # Make request
                result = await self.make_request(session, endpoint)
                self.results.append(result)

                # Simulate think time (realistic user behavior)
                think_time = random.uniform(self.config.think_time_min, self.config.think_time_max)
                await asyncio.sleep(think_time)

    async def peak_market_scenario(self):
        """Simulate peak Indonesian market trading scenarios"""
        logger.info("Starting Peak Market Volume Load Test")
        logger.info(f"Target: {self.config.concurrent_users} concurrent users")
        logger.info(f"Duration: {self.config.test_duration_seconds} seconds")

        # Create user sessions with staggered start (ramp-up)
        tasks = []
        ramp_up_delay = self.config.ramp_up_time / self.config.concurrent_users

        for user_id in range(self.config.concurrent_users):
            # Stagger user start times for realistic ramp-up
            delay = user_id * ramp_up_delay

            task = asyncio.create_task(
                self.delayed_user_session(user_id, delay, self.config.test_duration_seconds)
            )
            tasks.append(task)

        # Wait for all user sessions to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def delayed_user_session(self, user_id: int, delay: float, duration: int):
        """Start user session after specified delay"""
        await asyncio.sleep(delay)
        await self.user_session(user_id, duration)

    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance statistics"""
        if not self.results:
            return {"error": "No test results available"}

        # Filter successful requests
        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]

        response_times = [r.response_time for r in successful_results]

        stats = {
            "summary": {
                "total_requests": len(self.results),
                "successful_requests": len(successful_results),
                "failed_requests": len(failed_results),
                "success_rate": len(successful_results) / len(self.results) * 100 if self.results else 0
            },
            "performance": {
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "median_response_time": statistics.median(response_times) if response_times else 0,
                "min_response_time": min(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
                "p95_response_time": self.percentile(response_times, 95) if response_times else 0,
                "p99_response_time": self.percentile(response_times, 99) if response_times else 0
            },
            "throughput": {
                "requests_per_second": len(self.results) / self.config.test_duration_seconds if self.config.test_duration_seconds > 0 else 0,
                "successful_rps": len(successful_results) / self.config.test_duration_seconds if self.config.test_duration_seconds > 0 else 0
            }
        }

        # Endpoint-specific statistics
        endpoint_stats = {}
        for result in self.results:
            if result.endpoint not in endpoint_stats:
                endpoint_stats[result.endpoint] = []
            endpoint_stats[result.endpoint].append(result)

        stats["endpoints"] = {}
        for endpoint, results in endpoint_stats.items():
            successful = [r for r in results if r.success]
            response_times = [r.response_time for r in successful]

            stats["endpoints"][endpoint] = {
                "total_requests": len(results),
                "successful_requests": len(successful),
                "success_rate": len(successful) / len(results) * 100 if results else 0,
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "p95_response_time": self.percentile(response_times, 95) if response_times else 0
            }

        # Error analysis
        error_types = {}
        for result in failed_results:
            error = result.error_message or f"HTTP {result.status_code}"
            error_types[error] = error_types.get(error, 0) + 1

        stats["errors"] = error_types

        return stats

    @staticmethod
    def percentile(data: List[float], percentile: float) -> float:
        """Calculate percentile of response times"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def generate_report(self, stats: Dict[str, Any]) -> str:
        """Generate comprehensive load test report"""
        report = f"""
{'='*80}
PROJECT AURUM - INDONESIAN MARKET LOAD TEST REPORT
{'='*80}

TEST CONFIGURATION:
- Base URL: {self.config.base_url}
- Concurrent Users: {self.config.concurrent_users}
- Test Duration: {self.config.test_duration_seconds} seconds
- Ramp-up Time: {self.config.ramp_up_time} seconds
- Target Market: Indonesian Stock Exchange (IDX)

OVERALL PERFORMANCE:
- Total Requests: {stats['summary']['total_requests']:,}
- Successful Requests: {stats['summary']['successful_requests']:,}
- Failed Requests: {stats['summary']['failed_requests']:,}
- Success Rate: {stats['summary']['success_rate']:.2f}%

RESPONSE TIME METRICS:
- Average Response Time: {stats['performance']['avg_response_time']*1000:.2f}ms
- Median Response Time: {stats['performance']['median_response_time']*1000:.2f}ms
- 95th Percentile: {stats['performance']['p95_response_time']*1000:.2f}ms
- 99th Percentile: {stats['performance']['p99_response_time']*1000:.2f}ms
- Min Response Time: {stats['performance']['min_response_time']*1000:.2f}ms
- Max Response Time: {stats['performance']['max_response_time']*1000:.2f}ms

THROUGHPUT METRICS:
- Requests per Second: {stats['throughput']['requests_per_second']:.2f}
- Successful RPS: {stats['throughput']['successful_rps']:.2f}

INDONESIAN MARKET REQUIREMENTS CHECK:
✅ Sub-200ms Response Time: {'PASS' if stats['performance']['p95_response_time'] < 0.2 else 'FAIL'}
✅ 99.9% Success Rate: {'PASS' if stats['summary']['success_rate'] >= 99.9 else 'FAIL'}
✅ Peak Trading Volume: {'PASS' if stats['throughput']['successful_rps'] >= 50 else 'FAIL'}

ENDPOINT PERFORMANCE:
"""

        for endpoint, endpoint_stats in stats.get('endpoints', {}).items():
            report += f"\n{endpoint}:"
            report += f"\n  Requests: {endpoint_stats['total_requests']:,}"
            report += f"\n  Success Rate: {endpoint_stats['success_rate']:.2f}%"
            report += f"\n  Avg Response: {endpoint_stats['avg_response_time']*1000:.2f}ms"
            report += f"\n  P95 Response: {endpoint_stats['p95_response_time']*1000:.2f}ms"

        if stats.get('errors'):
            report += f"\n\nERROR ANALYSIS:\n"
            for error, count in stats['errors'].items():
                report += f"- {error}: {count} occurrences\n"

        report += f"\n\nRECOMMENDations:\n"

        # Performance recommendations
        if stats['performance']['p95_response_time'] > 0.2:
            report += "⚠️  P95 response time exceeds 200ms target for Indonesian trading\n"
            report += "   Consider: Database query optimization, caching, load balancing\n"

        if stats['summary']['success_rate'] < 99.9:
            report += "⚠️  Success rate below 99.9% SLA requirement\n"
            report += "   Consider: Error handling improvements, timeout adjustments\n"

        if stats['throughput']['successful_rps'] < 50:
            report += "⚠️  Throughput may not handle peak IDX trading volumes\n"
            report += "   Consider: Horizontal scaling, connection pooling\n"

        report += f"\n{'='*80}\n"

        return report

async def main():
    """Main load testing execution"""
    parser = argparse.ArgumentParser(description="Project Aurum Load Testing")
    parser.add_argument("--users", type=int, default=100, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    parser.add_argument("--url", type=str, default="http://localhost:8000", help="Base URL")
    parser.add_argument("--rampup", type=int, default=30, help="Ramp-up time in seconds")

    args = parser.parse_args()

    config = LoadTestConfig(
        base_url=args.url,
        concurrent_users=args.users,
        test_duration_seconds=args.duration,
        ramp_up_time=args.rampup
    )

    tester = IndonesianMarketLoadTester(config)

    logger.info("Starting Indonesian Market Load Testing...")
    logger.info(f"Simulating peak IDX trading volume with {config.concurrent_users} concurrent users")

    start_time = time.time()

    try:
        await tester.peak_market_scenario()

        end_time = time.time()
        actual_duration = end_time - start_time

        logger.info(f"Load test completed in {actual_duration:.2f} seconds")

        # Calculate and display results
        stats = tester.calculate_statistics()
        report = tester.generate_report(stats)

        print(report)

        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"load_test_results_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump({
                "config": {
                    "base_url": config.base_url,
                    "concurrent_users": config.concurrent_users,
                    "test_duration_seconds": config.test_duration_seconds,
                    "actual_duration": actual_duration
                },
                "statistics": stats,
                "raw_results": [
                    {
                        "endpoint": r.endpoint,
                        "response_time": r.response_time,
                        "status_code": r.status_code,
                        "success": r.success,
                        "timestamp": r.timestamp.isoformat(),
                        "error_message": r.error_message
                    }
                    for r in tester.results
                ]
            }, f, indent=2)

        logger.info(f"Detailed results saved to {results_file}")

        # Exit with appropriate code
        if stats['summary']['success_rate'] >= 99.9 and stats['performance']['p95_response_time'] < 0.2:
            logger.info("✅ Load test PASSED - System ready for Indonesian market peak volumes")
            sys.exit(0)
        else:
            logger.warning("⚠️ Load test FAILED - System needs optimization before production")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Load test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Load test failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())