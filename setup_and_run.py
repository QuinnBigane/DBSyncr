#!/usr/bin/env python3
"""
UPS Data Manager Setup and Startup Script
Installs dependencies and starts the application
"""
import subprocess
import sys
import os
from pathlib import Path


def install_dependencies():
    """Install required Python packages."""
    print("Installing dependencies...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 7):
        print(f"✗ Python 3.7+ required. You have {sys.version}")
        return False
    print(f"✓ Python version {sys.version.split()[0]} is compatible")
    return True


def create_directories():
    """Create necessary directories."""
    directories = [
        "data", "input_data", "output_data", 
        "logs", "exports", "backups"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✓ Directory structure created")


def check_data_files():
    """Check for test data files."""
    test_files = [
        "input_data/NetSuite_TestData.xlsx",
        "input_data/Shopify_TestData.xlsx"
    ]
    
    existing_files = [f for f in test_files if os.path.exists(f)]
    
    if existing_files:
        print(f"✓ Found {len(existing_files)} test data files")
        return True
    else:
        print("⚠ No test data files found in input_data/")
        print("  You can upload files via the web interface or place them in input_data/")
        return False


def main():
    """Main setup and startup routine."""
    print("UPS Data Manager - Setup and Startup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not install_dependencies():
        print("\nTry manually installing dependencies:")
        print("  pip install pandas openpyxl pydantic fastapi uvicorn python-multipart")
        sys.exit(1)
    
    # Check for data files
    check_data_files()
    
    print("\n" + "=" * 40)
    print("Setup complete! Starting application...")
    print("=" * 40)
    
    # Get user choice for run mode
    print("\nChoose run mode:")
    print("1. GUI only (traditional desktop interface)")
    print("2. API only (web server)")
    print("3. Both (GUI + API)")
    
    while True:
        choice = input("\nEnter choice (1-3) or 'q' to quit: ").strip()
        
        if choice == 'q':
            print("Goodbye!")
            sys.exit(0)
        elif choice == '1':
            mode = "gui"
            break
        elif choice == '2':
            mode = "api"
            break
        elif choice == '3':
            mode = "both"
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 'q'")
    
    # Start application
    try:
        if mode == "api":
            print(f"\n🚀 Starting API server...")
            print(f"   API will be available at: http://localhost:8000")
            print(f"   Documentation at: http://localhost:8000/docs")
            print(f"   Press Ctrl+C to stop")
        elif mode == "gui":
            print(f"\n🚀 Starting GUI application...")
        else:
            print(f"\n🚀 Starting GUI application with API server...")
            print(f"   API available at: http://localhost:8000")
        
        print()
        subprocess.check_call([sys.executable, "main.py", mode])
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Application failed to start: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nApplication stopped by user")


if __name__ == "__main__":
    main()