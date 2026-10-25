# run_tests.py
# Maya Faceit Plugin - Test Runner
# Run from Maya Script Editor or command line

"""
Test runner for Faceit Maya plugin.
Run all tests or specific test suites.
"""

import maya.cmds as cmds # type: ignore
import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import test modules
from .test_core import run_core_tests
from .test_operators import run_operators_tests


def run_all_tests():
    """
    Run all tests.
    """
    print("\n" + "=" * 60)
    print("FACEIT TEST SUITE")
    print("=" * 60)
    
    # Run core tests
    print("\nRunning Core Tests...")
    core_results = run_core_tests()
    
    # Run operators tests
    print("\nRunning Operators Tests...")
    operators_results = run_operators_tests()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Core Tests: {core_results['passed']}/{core_results['total']} passed")
    print(f"Operators Tests: {operators_results['passed']}/{operators_results['total']} passed")
    
    total = core_results['total'] + operators_results['total']
    passed = core_results['passed'] + operators_results['passed']
    failed = core_results['failed'] + operators_results['failed']
    
    print(f"\nTotal: {passed}/{total} passed")
    print(f"Failed: {failed}")
    print("=" * 60)
    
    return {
        'total': total,
        'passed': passed,
        'failed': failed,
        'core': core_results,
        'operators': operators_results
    }


def run_test_suite(suite_name: str):
    """
    Run a specific test suite.
    
    Args:
        suite_name: 'core' or 'operators'
    """
    if suite_name == 'core':
        run_core_tests()
    elif suite_name == 'operators':
        run_operators_tests()
    else:
        print(f"Unknown test suite: {suite_name}")
        print("Available suites: core, operators")


if __name__ == "__main__":
    # Check command line arguments
    import sys
    if len(sys.argv) > 1:
        suite = sys.argv[1]
        run_test_suite(suite)
    else:
        run_all_tests()