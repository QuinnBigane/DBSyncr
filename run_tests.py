#!/usr/bin/env python3
"""
DBSyncr Test Runner
Convenience script to run the complete test suite
"""
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import and run the CLI test command
from cli.main import run_tests

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)