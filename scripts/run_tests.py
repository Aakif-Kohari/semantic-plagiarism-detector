#!/usr/bin/env python3
"""
Test Runner Script for Semantic Plagiarism Detector.

This script provides a robust wrapper around pytest, allowing developers and CI 
environments to execute the test suite with standardized configurations, logging, 
and environment checks. 

Recent changes:
- Added support for parallel test execution using pytest-xdist (-n auto).
"""

import os
import sys
import argparse
import subprocess
import logging
import platform
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("TestRunner")

# ---------------------------------------------------------------------------
# Constants and Configurations
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DIR = PROJECT_ROOT / "tests"
DEFAULT_COVERAGE_THRESHOLD = 85

class TestRunnerError(Exception):
    """Custom exception for test runner failures."""
    pass

# ---------------------------------------------------------------------------
# Core Runner Class
# ---------------------------------------------------------------------------
class PytestRunner:
    """
    Encapsulates the logic for configuring and executing pytest.
    
    Attributes:
        parallel (bool): Whether to run tests in parallel.
        verbose (bool): Whether to enable verbose output.
        coverage (bool): Whether to generate a coverage report.
        test_path (Path): Specific path to tests (defaults to all).
        marker (Optional[str]): Pytest marker to filter tests (e.g., 'unit').
    """

    def __init__(self, parallel: bool = False, verbose: bool = False, 
                 coverage: bool = False, test_path: Optional[str] = None,
                 marker: Optional[str] = None) -> None:
        """Initializes the runner with specified configuration flags."""
        self.parallel = parallel
        self.verbose = verbose
        self.coverage = coverage
        self.test_path = Path(test_path) if test_path else TEST_DIR
        self.marker = marker

    def _check_xdist_installed(self) -> bool:
        """
        Verifies if pytest-xdist is installed in the current environment.
        
        Returns:
            bool: True if installed, False otherwise.
        """
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", "pytest-xdist"],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f"Failed to check for pytest-xdist: {e}")
            return False

    def build_command(self) -> List[str]:
        """
        Constructs the pytest command list based on instance attributes.
        
        Returns:
            List[str]: The constructed command ready for subprocess.run.
        """
        cmd = [sys.executable, "-m", "pytest"]

        # 1. Path to execute
        if self.test_path.exists():
            cmd.append(str(self.test_path))
        else:
            logger.warning(f"Specified test path {self.test_path} not found. Running from root.")
            cmd.append(str(TEST_DIR))

        # 2. Markers (Scope selection)
        if self.marker:
            cmd.extend(["-m", self.marker])

        # 3. Verbosity
        if self.verbose:
            cmd.extend(["-v", "-s"])

        # 4. Coverage
        if self.coverage:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            cmd.extend([
                "--cov=src",
                "--cov=app",
                "--cov-report=term-missing", 
                "--cov-report=html",
                f"--cov-fail-under={DEFAULT_COVERAGE_THRESHOLD}",
                f"--junitxml=test-reports/junit-{timestamp}.xml"
            ])

        # 5. Parallel execution (Issue #684 logic)
        if self.parallel:
            if self._check_xdist_installed():
                logger.info("pytest-xdist detected. Enabling multi-core test execution (-n auto).")
                cmd.extend(["-n", "auto"])
            else:
                logger.warning("pytest-xdist is NOT installed. Ignoring --parallel flag.")
                logger.info("To enable parallel testing, run: pip install pytest-xdist")

        return cmd

    def run(self) -> int:
        """
        Executes the built pytest command.
        
        Returns:
            int: The return code from the pytest process.
        """
        cmd = self.build_command()
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        try:
            # Setting environment variables to ensure clean test runs
            env = os.environ.copy()
            env["PYTHONPATH"] = str(PROJECT_ROOT)
            env["TESTING_MODE"] = "1"
            
            result = subprocess.run(cmd, env=env, cwd=str(PROJECT_ROOT))
            
            if result.returncode == 0:
                logger.info("All tests passed successfully.")
            else:
                logger.error(f"Tests failed with exit code {result.returncode}.")
                
            return result.returncode
            
        except KeyboardInterrupt:
            logger.warning("Test execution interrupted by user.")
            return 130
        except Exception as e:
            logger.error(f"An unexpected error occurred during test execution: {e}")
            return 1

# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments for the test runner.
    
    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Run the test suite for Semantic Plagiarism Detector.",
        epilog="Example: python scripts/run_tests.py --parallel --verbose"
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Run the entire test suite (default).")
    group.add_argument("--unit", action="store_true", help="Run only isolated unit tests.")
    group.add_argument("--integration", action="store_true", help="Run only integration tests.")

    parser.add_argument(
        "--parallel", 
        action="store_true", 
        help="Run tests in parallel across all available CPU cores using pytest-xdist (-n auto)."
    )
    parser.add_argument(
        "--verbose", 
        "-v", 
        action="store_true", 
        help="Enable verbose output and disable capturing (-v -s)."
    )
    parser.add_argument(
        "--coverage", 
        "-c", 
        action="store_true", 
        help="Generate coverage reports and enforce thresholds."
    )
    parser.add_argument(
        "--path", 
        type=str, 
        default=None, 
        help="Specific test file or directory path to run."
    )

    return parser.parse_args()

def main() -> None:
    """Main function to initialize and run the test suite."""
    args = parse_arguments()
    
    logger.info("Initializing Test Runner...")
    logger.info(f"System: {platform.system()} {platform.release()}")
    logger.info(f"Python Version: {platform.python_version()}")
    
    # Map flags to markers
    marker = "unit" if args.unit else "integration" if args.integration else None

    runner = PytestRunner(
        parallel=args.parallel,
        verbose=args.verbose,
        coverage=args.coverage or (marker is None), # Default coverage on if running all
        test_path=args.path,
        marker=marker
    )
    
    sys.exit(runner.run())

if __name__ == "__main__":
    main()
