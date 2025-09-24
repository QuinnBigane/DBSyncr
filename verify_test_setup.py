#!/usr/bin/env python3
"""
Simple test verification script
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
src_path = project_root / "src"

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def test_imports():
    """Test that we can import the required modules."""
    try:
        from src.api.main import app
        print("✓ FastAPI app import successful")
        
        from fastapi.testclient import TestClient
        print("✓ TestClient import successful")
        
        client = TestClient(app)
        print("✓ TestClient created successfully")
        
        # Test health endpoint
        response = client.get("/health")
        print(f"✓ Health check: {response.status_code} - {response.json()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_files():
    """Test that test data files exist."""
    test_data_dir = Path(__file__).parent / "tests" / "test_data"
    
    db1_file = test_data_dir / "db1_5_items.csv"
    db2_file = test_data_dir / "db2_10_items.csv"
    
    if db1_file.exists():
        print(f"✓ DB1 test file exists: {db1_file}")
        with open(db1_file) as f:
            lines = f.readlines()
            print(f"  - Has {len(lines)} lines (including header)")
    else:
        print(f"❌ DB1 test file missing: {db1_file}")
        return False
    
    if db2_file.exists():
        print(f"✓ DB2 test file exists: {db2_file}")
        with open(db2_file) as f:
            lines = f.readlines()
            print(f"  - Has {len(lines)} lines (including header)")
    else:
        print(f"❌ DB2 test file missing: {db2_file}")
        return False
        
    return True

if __name__ == "__main__":
    print("DBSyncr Test Setup Verification")
    print("=" * 40)
    
    all_good = True
    
    if not test_data_files():
        all_good = False
    
    print()
    if not test_imports():
        all_good = False
    
    print("\n" + "=" * 40)
    if all_good:
        print("🎉 All verifications passed! Ready to run tests.")
    else:
        print("❌ Some verifications failed. Check the errors above.")
        sys.exit(1)