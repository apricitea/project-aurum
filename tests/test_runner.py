"""
Test runner and configuration for Project Aurum test suite
"""

import pytest
import sys
import os
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import argparse


class TestRunner:
    """Main test runner for Project Aurum"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_dir = self.project_root / "tests"
        self.coverage_threshold = 80

    def run_unit_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run unit tests"""
        print("Running unit tests...")

        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir / "unit"),
            "-v" if verbose else "-q",
            "--tb=short",
            "--cov=src",
            "--cov=feature_engineering",
            "--cov=model_ensemble",
            "--cov=signal_generator",
            "--cov=main_pipeline",
            f"--cov-fail-under={self.coverage_threshold}",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/unit",
            "--cov-report=xml:coverage_unit.xml",
            "-m", "unit"
        ]

        result = self._run_pytest_command(cmd)
        return {
            "test_type": "unit",
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr,
            "coverage_generated": True
        }

    def run_integration_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run integration tests"""
        print("Running integration tests...")

        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir / "integration"),
            "-v" if verbose else "-q",
            "--tb=short",
            "-m", "integration"
        ]

        result = self._run_pytest_command(cmd)
        return {
            "test_type": "integration",
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }

    def run_security_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run security tests"""
        print("Running security tests...")

        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir / "security"),
            "-v" if verbose else "-q",
            "--tb=short",
            "-m", "security"
        ]

        result = self._run_pytest_command(cmd)
        return {
            "test_type": "security",
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }

    def run_performance_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run performance tests"""
        print("Running performance tests...")

        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir / "performance"),
            "-v" if verbose else "-q",
            "--tb=short",
            "-m", "performance"
        ]

        result = self._run_pytest_command(cmd)
        return {
            "test_type": "performance",
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }

    def run_indonesian_market_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """Run Indonesian market-specific tests"""
        print("Running Indonesian market tests...")

        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-v" if verbose else "-q",
            "--tb=short",
            "-m", "indonesian_market"
        ]

        result = self._run_pytest_command(cmd)
        return {
            "test_type": "indonesian_market",
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }

    def run_all_tests(self, verbose: bool = False, skip_slow: bool = False) -> Dict[str, Any]:
        """Run all tests"""
        print("Running complete test suite...")

        markers = []
        if skip_slow:
            markers.append("not slow")

        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir),
            "-v" if verbose else "-q",
            "--tb=short",
            "--cov=src",
            "--cov=feature_engineering",
            "--cov=model_ensemble",
            "--cov=signal_generator",
            "--cov=main_pipeline",
            f"--cov-fail-under={self.coverage_threshold}",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/complete",
            "--cov-report=xml:coverage_complete.xml",
            "--durations=10"
        ]

        if markers:
            cmd.extend(["-m", " and ".join(markers)])

        result = self._run_pytest_command(cmd)
        return {
            "test_type": "complete",
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr,
            "coverage_generated": True
        }

    def run_smoke_tests(self) -> Dict[str, Any]:
        """Run smoke tests for quick validation"""
        print("Running smoke tests...")

        # Run a subset of critical tests
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir / "unit" / "api" / "test_main.py::TestHealthEndpoints::test_basic_health_check"),
            str(self.test_dir / "unit" / "api" / "test_auth.py::TestAuthManager::test_hash_password"),
            str(self.test_dir / "security" / "test_authentication_security.py::TestPasswordSecurity::test_password_hashing_uniqueness"),
            "-v",
            "--tb=line"
        ]

        result = self._run_pytest_command(cmd)
        return {
            "test_type": "smoke",
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }

    def check_test_coverage(self) -> Dict[str, Any]:
        """Check and report test coverage"""
        print("Checking test coverage...")

        # Run tests with coverage
        cmd = [
            "python", "-m", "pytest",
            str(self.test_dir / "unit"),
            "--cov=src",
            "--cov=feature_engineering",
            "--cov=model_ensemble",
            "--cov=signal_generator",
            "--cov=main_pipeline",
            "--cov-report=term-missing",
            "--cov-report=json:coverage.json",
            "-q"
        ]

        result = self._run_pytest_command(cmd)

        coverage_data = {}
        try:
            with open(self.project_root / "coverage.json", "r") as f:
                coverage_data = json.load(f)
        except FileNotFoundError:
            print("Coverage data not found")

        return {
            "coverage_passed": result.returncode == 0,
            "coverage_data": coverage_data,
            "threshold": self.coverage_threshold
        }

    def validate_test_environment(self) -> Dict[str, Any]:
        """Validate test environment setup"""
        print("Validating test environment...")

        issues = []

        # Check Python version
        if sys.version_info < (3, 8):
            issues.append("Python 3.8+ required")

        # Check required packages
        required_packages = [
            "pytest", "pytest-asyncio", "pytest-cov", "pytest-mock",
            "httpx", "factory-boy", "pandas", "numpy", "scikit-learn"
        ]

        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                issues.append(f"Missing package: {package}")

        # Check test directory structure
        required_dirs = [
            "unit", "integration", "security", "performance", "fixtures"
        ]

        for dir_name in required_dirs:
            if not (self.test_dir / dir_name).exists():
                issues.append(f"Missing test directory: {dir_name}")

        # Check configuration files
        required_files = ["pytest.ini", "conftest.py"]
        for file_name in required_files:
            if not (self.project_root / file_name if file_name == "pytest.ini" else self.test_dir / file_name).exists():
                issues.append(f"Missing configuration file: {file_name}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "python_version": sys.version,
            "test_directory": str(self.test_dir)
        }

    def generate_test_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate comprehensive test report"""
        report = []
        report.append("=" * 80)
        report.append("PROJECT AURUM TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        total_passed = 0
        total_run = 0

        for result in results:
            test_type = result.get("test_type", "unknown")
            passed = result.get("passed", False)

            report.append(f"{test_type.upper()} TESTS: {'PASS' if passed else 'FAIL'}")

            if passed:
                total_passed += 1
            total_run += 1

            if result.get("errors"):
                report.append(f"  Errors: {result['errors'][:200]}...")

            report.append("")

        # Overall summary
        report.append("-" * 40)
        report.append(f"OVERALL: {total_passed}/{total_run} test suites passed")

        if total_passed == total_run:
            report.append("✅ ALL TESTS PASSED")
        else:
            report.append("❌ SOME TESTS FAILED")

        report.append("-" * 40)

        return "\n".join(report)

    def _run_pytest_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run pytest command and return result"""
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            return result
        except subprocess.TimeoutExpired:
            print("Test execution timed out")
            return subprocess.CompletedProcess(
                cmd, 1, "Test timed out", "Execution exceeded 10 minutes"
            )
        except Exception as e:
            print(f"Error running tests: {e}")
            return subprocess.CompletedProcess(
                cmd, 1, "", str(e)
            )


def main():
    """Main entry point for test runner"""
    parser = argparse.ArgumentParser(description="Project Aurum Test Runner")
    parser.add_argument("--type", choices=["unit", "integration", "security", "performance", "indonesian", "all", "smoke"],
                       default="all", help="Type of tests to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--skip-slow", action="store_true", help="Skip slow tests")
    parser.add_argument("--validate", action="store_true", help="Validate test environment")
    parser.add_argument("--coverage", action="store_true", help="Check coverage only")
    parser.add_argument("--report", action="store_true", help="Generate detailed report")

    args = parser.parse_args()

    runner = TestRunner()

    # Validate environment if requested
    if args.validate:
        validation = runner.validate_test_environment()
        print(f"Environment validation: {'PASS' if validation['valid'] else 'FAIL'}")
        if validation['issues']:
            print("Issues found:")
            for issue in validation['issues']:
                print(f"  - {issue}")
        return 0 if validation['valid'] else 1

    # Check coverage only if requested
    if args.coverage:
        coverage_result = runner.check_test_coverage()
        print(f"Coverage check: {'PASS' if coverage_result['coverage_passed'] else 'FAIL'}")
        return 0 if coverage_result['coverage_passed'] else 1

    # Run specified tests
    results = []

    if args.type == "unit":
        results.append(runner.run_unit_tests(args.verbose))
    elif args.type == "integration":
        results.append(runner.run_integration_tests(args.verbose))
    elif args.type == "security":
        results.append(runner.run_security_tests(args.verbose))
    elif args.type == "performance":
        results.append(runner.run_performance_tests(args.verbose))
    elif args.type == "indonesian":
        results.append(runner.run_indonesian_market_tests(args.verbose))
    elif args.type == "smoke":
        results.append(runner.run_smoke_tests())
    elif args.type == "all":
        results.append(runner.run_all_tests(args.verbose, args.skip_slow))

    # Generate report if requested
    if args.report and results:
        report = runner.generate_test_report(results)
        print(report)

        # Save report to file
        report_file = runner.project_root / "test_report.txt"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"\nReport saved to: {report_file}")

    # Return appropriate exit code
    all_passed = all(result.get("passed", False) for result in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())