#!/usr/bin/env python3
"""
DBSyncr - Main Entry Point
Supports multiple modes: GUI only, API only, or both
"""
import argparse
import sys
import os
import threading
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add src to path for imports
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from src.config.settings import settings
from src.utils.logging_config import setup_logging, get_logger


def run_gui():
    """Run the GUI application."""
    try:
        # Import GUI components
        from DBSyncr import DBSyncr
        
        logger = get_logger("GUI")
        logger.info("Starting GUI application")
        
        # Create and run the application
        app = DBSyncr()
        app.start()
        
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
        from src.api.main import app
        
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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="DBSyncr")
    parser.add_argument(
        "mode",
        choices=["gui", "api", "both"],
        default="gui",
        nargs="?",
        help="Run mode: gui (default), api, or both"
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
    
    args = parser.parse_args()
    
    # Update settings with command line arguments
    settings.api_host = args.host
    settings.api_port = args.port
    settings.debug = args.debug
    settings.log_level = args.log_level
    
    # Setup logging
    setup_logging(log_level=args.log_level)
    logger = get_logger("Main")
    
    logger.info(f"DBSyncr starting in {args.mode} mode")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Run based on mode
    try:
        if args.mode == "gui":
            success = run_gui()
        elif args.mode == "api":
            success = run_api()
        elif args.mode == "both":
            success = run_both()
        else:
            print(f"Invalid mode: {args.mode}")
            sys.exit(1)
        
        if not success:
            logger.error("Application failed to start")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()