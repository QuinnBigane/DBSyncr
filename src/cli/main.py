#!/usr/bin/env python3
"""
DBSyncr - Main Entry Point
Supports multiple modes: GUI only, API only, both, setup, test, validate
"""
import argparse
import sys
import os
import threading
import time
import subprocess
import requests
import json
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent  # Go up to src/
src_path = project_root
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Remove duplicate path addition
# src_path = project_root / "src"
# if str(src_path) not in sys.path:
#     sys.path.insert(0, str(src_path))

from config.settings import settings
from utils.logging_config import setup_logging, get_logger
from utils.dependency_injection import register, register_factory
from services.data_service import DataService
from services.api_data_service import ApiDataService
from services.auth_service import AuthService
from services.rate_limit_service import RateLimitService
from services.websocket_service import WebSocketService
from config.settings import config_manager
from utils.logging_config import get_logger as get_logger_func


def bootstrap_dependencies():
    """Bootstrap the dependency injection container."""
    # Register DataService as singleton
    register(
        DataService,
        lambda: DataService(
            config_manager=config_manager,
            logger=get_logger_func("DataService")
        ),
        singleton=True
    )

    # Register other services as singletons
    register(ApiDataService, lambda: ApiDataService(logger=get_logger_func("ApiDataService")), singleton=True)
    register(AuthService, lambda: AuthService(), singleton=True)
    register(RateLimitService, lambda: RateLimitService(), singleton=True)
    register(WebSocketService, lambda: WebSocketService(), singleton=True)


def run_gui():
    """Run the GUI application."""
    try:
        # Import GUI components
        from core.DBSyncr import DBSyncr
        
        logger = get_logger("GUI")
        logger.info("Starting GUI application")
        
        # Create and run the application
        app = DBSyncr()
        app.run()
        
    except ImportError as e:
        print(f"GUI dependencies not available: {e}")
        print("Install tkinter to run the GUI: pip install tk")
        return False
    except Exception as e:
        logger = get_logger("GUI")
        logger.error(f"GUI application failed: {e}")
        return False
    
    return True


def run_api():
    """Run the FastAPI application."""
    try:
        import uvicorn
        from api.main import app
        
        logger = get_logger("API")
        logger.info(f"Starting API server on {settings.api_host}:{settings.api_port}")
        
        uvicorn.run(
            "src.api.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.debug,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"API dependencies not available: {e}")
        print("Install FastAPI dependencies: pip install -r requirements.txt")
        return False
    except Exception as e:
        logger = get_logger("API")
        logger.error(f"API server failed: {e}")
        return False
    
    return True


def run_both():
    """Run both GUI and API in separate threads."""
    logger = get_logger("Main")
    logger.info("Starting both GUI and API applications")
    
    # Start API in a separate thread
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    # Give API time to start
    time.sleep(2)
    
    # Run GUI in main thread
    return run_gui()


def check_dependencies():
    """Check if required dependencies are available."""
    missing_deps = []
    
    try:
        import pandas
    except ImportError:
        missing_deps.append("pandas")
    
    try:
        import openpyxl
    except ImportError:
        missing_deps.append("openpyxl")
    
    try:
        import pydantic
    except ImportError:
        missing_deps.append("pydantic")
    
    if missing_deps:
        print("Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nInstall with: pip install -r requirements.txt")
        return False
    
    return True


def setup_project():
    """Setup the project - install dependencies and create directories."""
    print("🚀 Setting up DBSyncr project...")
    
    # Check Python version
    if sys.version_info < (3, 7):
        print(f"✗ Python 3.7+ required. You have {sys.version}")
        return False
    print(f"✓ Python version {sys.version.split()[0]} is compatible")
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False
    
    # Create directories
    directories = [
        "data/api/incoming", "data/api/processing", "data/api/results",
        "data/dev/samples", "data/dev/inputs", "data/dev/outputs",
        "data/config", "logs", "backups"
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✓ Directory structure created")
    print("\n🎉 Setup complete! You can now run:")
    print("  python main.py gui    # Start GUI")
    print("  python main.py api    # Start API server")
    print("  python main.py both   # Start both")
    
    return True


def run_tests():
    """Run the complete test suite."""
    print("🧪 Running DBSyncr Test Suite")
    print("=" * 50)

    # Change to project root directory
    project_root = Path(__file__).parent.parent.parent  # src/cli/main.py -> cli -> src -> project root
    os.chdir(project_root)
    
    # Ensure tests directory exists
    tests_dir = project_root / "tests"
    if not tests_dir.exists():
        print(f"❌ Tests directory not found: {tests_dir}")
        return False    # Run all tests with pytest
    print("\n📋 Running Complete Test Suite...")
    test_result = subprocess.run([
        sys.executable, "-m", "pytest",
        str(tests_dir),
        "-v", "--tb=short",
        "--color=yes",
        "--durations=10"
    ], capture_output=False, text=True)

    print("\n📊 Test Summary")
    print("=" * 30)

    if test_result.returncode == 0:
        print("✅ All Tests: PASSED")
        print("\n🎉 Test Coverage:")
        print("   - Unit tests (services, models, utilities)")
        print("   - Integration tests (API endpoints)")
        print("   - End-to-end workflow tests")
        print("   - Authentication and security tests")
        return True
    else:
        print("❌ Tests: FAILED")
        print("   Check the output above for details")
        return False
def validate_api(base_url="http://localhost:8000"):
    """Validate API endpoints."""
    api_prefix = "/api/v1"
    
    print("🔍 API Endpoint Validation")
    print("=" * 50)
    print(f"Server: {base_url}")
    print()
    
    endpoints = [
        ("Health Check", "GET", f"{base_url}/health", None, "Status should be healthy"),
        ("Data Summary", "GET", f"{base_url}{api_prefix}/data/summary", None, "Should show loaded data counts"),
        ("Field Mappings", "GET", f"{base_url}{api_prefix}/mappings", None, "Should return mapping configuration"),
        ("DB1 Data (Small)", "GET", f"{base_url}{api_prefix}/data/db1?page=1&limit=3", None, "Should return database 1 test data"),
        ("DB2 Data (Small)", "GET", f"{base_url}{api_prefix}/data/db2?page=1&limit=3", None, "Should return database 2 test data"),
        ("Combined Data (Small)", "GET", f"{base_url}{api_prefix}/data/combined?page=1&limit=3", None, "Should return merged data"),
        ("Unmatched Analysis", "GET", f"{base_url}{api_prefix}/analysis/unmatched", None, "Should show matching statistics"),
    ]
    
    passed = 0
    total = len(endpoints)
    
    for name, method, url, payload, description in endpoints:
        print(f"⚡ Testing {name}...")
        print(f"   URL: {url}")
        print(f"   Expected: {description}")
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=5)
            elif method == "POST":
                response = requests.post(url, json=payload, timeout=5)
            
            if response.status_code == 200:
                print("   ✅ Status: 200 OK")
                passed += 1
            else:
                print(f"   ❌ Status: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    print(f"📊 Results: {passed}/{total} endpoints working")
    
    if passed == total:
        print("🎉 All API endpoints are working!")
        return True
    else:
        print("⚠️  Some endpoints failed. Make sure the API server is running.")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DBSyncr - Data Synchronization Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py gui          # Start GUI application
  python main.py api          # Start API server
  python main.py both         # Start both GUI and API
  python main.py setup        # Setup project (install dependencies)
  python main.py test         # Run test suite
  python main.py validate     # Validate API endpoints
        """
    )
    
    parser.add_argument(
        "command",
        choices=["gui", "api", "both", "setup", "test", "validate"],
        help="Command to run"
    )
    parser.add_argument(
        "--host",
        default=settings.api_host,
        help=f"API host (default: {settings.api_host})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.api_port,
        help=f"API port (default: {settings.api_port})"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=settings.log_level,
        help=f"Logging level (default: {settings.log_level})"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API URL for validation (default: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    # Update settings with command line arguments
    settings.api_host = args.host
    settings.api_port = args.port
    settings.debug = args.debug
    settings.log_level = args.log_level
    
    # Setup logging
    setup_logging(log_level=args.log_level)
    logger = get_logger("Main")
    
    # Bootstrap dependency injection
    bootstrap_dependencies()
    
    logger.info(f"DBSyncr command: {args.command}")
    
    # Execute command
    try:
        if args.command == "setup":
            success = setup_project()
        elif args.command == "test":
            success = run_tests()
        elif args.command == "validate":
            success = validate_api(args.api_url)
        elif args.command == "gui":
            # Check dependencies for GUI/API modes
            if not check_dependencies():
                sys.exit(1)
            success = run_gui()
        elif args.command == "api":
            if not check_dependencies():
                sys.exit(1)
            success = run_api()
        elif args.command == "both":
            if not check_dependencies():
                sys.exit(1)
            success = run_both()
        else:
            print(f"Invalid command: {args.command}")
            sys.exit(1)
        
        if not success:
            logger.error(f"Command '{args.command}' failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
