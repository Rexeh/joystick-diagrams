#!/usr/bin/env python3
"""
Test runner script for IL-2 Sturmovik parser tests

This script provides an easy way to run the IL-2 parser tests with different options.

Usage:
    python run_il2_tests.py                    # Run all tests
    python run_il2_tests.py -v                 # Run with verbose output
    python run_il2_tests.py --coverage         # Run with coverage report
    python run_il2_tests.py --encoding-only    # Run only encoding-related tests
    python run_il2_tests.py --integration      # Run only integration tests
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_filter=None, verbose=False, coverage=False):
    """Run the IL-2 parser tests with specified options"""
    
    # Base command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add test file path
    test_file = Path(__file__).parent / "test_il2_parser.py"
    cmd.append(str(test_file))
    
    # Add options
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=joystick_diagrams.plugins.il2_sturmovik_plugin.il2_parser", 
                   "--cov-report=html", 
                   "--cov-report=term"])
    
    # Add test filter if specified
    if test_filter:
        cmd.extend(["-k", test_filter])
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 60)
    
    # Run the tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent.parent)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run IL-2 Sturmovik parser tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Enable verbose test output")
    
    parser.add_argument("--coverage", action="store_true",
                       help="Run tests with coverage analysis")
    
    parser.add_argument("--encoding-only", action="store_true",
                       help="Run only encoding-related tests")
    
    parser.add_argument("--integration", action="store_true",
                       help="Run only integration tests")
    
    parser.add_argument("--control-objects", action="store_true",
                       help="Run only control object creation tests")
    
    parser.add_argument("--edge-cases", action="store_true",
                       help="Run only edge case tests")
    
    args = parser.parse_args()
    
    # Determine test filter
    test_filter = None
    if args.encoding_only:
        test_filter = "encoding"
    elif args.integration:
        test_filter = "integration"
    elif args.control_objects:
        test_filter = "control_object"
    elif args.edge_cases:
        test_filter = "TestIL2ParserEdgeCases"
    
    # Run tests
    exit_code = run_tests(
        test_filter=test_filter,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())