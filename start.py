"""
UPS Data Manager - Startup Script
Ensures system is ready and starts the application.
"""
import os
import sys

def ensure_dependencies():
    """Ensure required packages are available."""
    try:
        import pandas
        import openpyxl
        return True
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Please install required packages:")
        print("pip install pandas openpyxl")
        return False

def check_data_files():
    """Check if data files are available."""
    excel_files = [
        "netsuite all items 9-22-2025.xls.xlsx",
        "Shopify_ALL_Export_2025-09-22_030043.xlsx"
    ]
    
    csv_files = [
        "data/NetSuiteData.csv",
        "data/ShopifyData.csv"
    ]
    
    test_excel_files = [
        "data/NetSuite_TestData.xlsx",
        "data/Shopify_TestData.xlsx"
    ]
    
    excel_available = all(os.path.exists(f) for f in excel_files)
    csv_available = all(os.path.exists(f) for f in csv_files)
    test_excel_available = all(os.path.exists(f) for f in test_excel_files)
    
    if excel_available:
        print("✓ Production Excel source files found")
        if not csv_available:
            print("  Converting Excel files to CSV...")
            try:
                from data_converter import DataConverter
                converter = DataConverter()
                success, message = converter.convert_all()
                if success:
                    print("  ✓ Excel files converted successfully")
                else:
                    print(f"  ✗ Conversion failed: {message}")
                    return False
            except Exception as e:
                print(f"  ✗ Conversion error: {e}")
                return False
        else:
            print("  ✓ CSV files already available")
        return True
    elif test_excel_available:
        print("✓ Test Excel files found - using test data")
        return True
    elif csv_available:
        print("✓ CSV data files found")
        return True
    else:
        missing = [f for f in excel_files if not os.path.exists(f)]
        print(f"✗ Missing production Excel files: {missing}")
        print("✗ No test data or CSV files found either")
        print("Please ensure either:")
        print("  - Production Excel files are present")
        print("  - Test data files are in data/ folder")  
        print("  - CSV files are available in data/ folder")
        return False

def start_application():
    """Start the UPS Data Manager application with threading."""
    try:
        print("Starting UPS Data Manager with threading support...")
        
        # Import the main application
        from UPSDataManager import UPSDataManager
        
        # Create and start manager
        manager = UPSDataManager()
        manager.start()
        
        print("✓ Application started successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Failed to start application: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main startup function."""
    print("UPS Data Manager")
    print("=" * 40)
    
    # Check dependencies
    print("Checking dependencies...")
    if not ensure_dependencies():
        return 1
    
    # Check data files
    print("Checking data files...")
    if not check_data_files():
        return 1
    
    # Start application
    print("All checks passed!")
    print("=" * 40)
    success = start_application()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())