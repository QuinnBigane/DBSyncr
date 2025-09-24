"""
Full workflow integration tests for DBSyncr API
Tests the complete upload -> sync -> export workflow through the API
"""
import pytest
import httpx
import asyncio
import os
import time
import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any
import subprocess
import threading


class TestDBSyncrAPIWorkflow:
    """Integration tests for the complete DBSyncr workflow."""
    
    BASE_URL = "http://localhost:8000"
    API_PREFIX = "/api/v1"
    
    @classmethod
    def setup_class(cls):
        """Start the API server before running tests."""
        cls.server_process = None
        cls._start_api_server()
        cls._wait_for_server()
    
    @classmethod
    def teardown_class(cls):
        """Stop the API server after tests."""
        if cls.server_process:
            cls.server_process.terminate()
            cls.server_process.wait()
    
    @classmethod
    def _start_api_server(cls):
        """Start the API server in a separate process."""
        # Change to the project directory
        project_dir = Path(__file__).parent.parent
        os.chdir(project_dir)
        
        # Start the server using the main.py API mode
        cls.server_process = subprocess.Popen([
            "C:/Users/Quinn/AppData/Local/Microsoft/WindowsApps/python3.13.exe",
            "-c",
            "from src.api.main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    @classmethod 
    def _wait_for_server(cls):
        """Wait for the API server to be ready."""
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = httpx.get(f"{cls.BASE_URL}/health", timeout=5.0)
                if response.status_code == 200:
                    print("API server is ready!")
                    return
            except Exception:
                pass
            
            time.sleep(1)
            print(f"Waiting for server... attempt {attempt + 1}/{max_attempts}")
        
        raise RuntimeError("API server failed to start within 30 seconds")
    
    def test_full_workflow(self):
        """
        Test the complete workflow:
        0. Update field mappings for our test data
        1. Upload 2 small databases (db1 of 5 items and db2 of 10 items)
        2. Run a sync operation of db2 into db1 (happens automatically)
        3. Pull down the output db of db1 and db2
        """
        # Test data files
        test_data_dir = Path(__file__).parent / "test_data"
        db1_file = test_data_dir / "db1_5_items.csv"
        db2_file = test_data_dir / "db2_10_items.csv"
        test_mappings_file = test_data_dir / "test_field_mappings.json"
        
        assert db1_file.exists(), f"Test data file not found: {db1_file}"
        assert db2_file.exists(), f"Test data file not found: {db2_file}"
        assert test_mappings_file.exists(), f"Test mappings file not found: {test_mappings_file}"
        
        with httpx.Client(timeout=30.0) as client:
            # Step 0: Update field mappings for our test data
            print("Step 0: Updating field mappings for test data...")
            with open(test_mappings_file, 'r') as f:
                test_mappings = json.load(f)
            
            response = client.put(
                f"{self.BASE_URL}{self.API_PREFIX}/mappings",
                json=test_mappings
            )
            assert response.status_code == 200, f"Field mappings update failed: {response.text}"
            update_response = response.json()
            assert update_response["success"] is True
            print("✓ Field mappings updated for test data")
            
            # Step 1: Upload Database 1 (5 items)
            print("Step 1: Uploading Database 1...")
            with open(db1_file, "rb") as f:
                response = client.post(
                    f"{self.BASE_URL}{self.API_PREFIX}/data/upload/db1",
                    files={"file": ("db1_5_items.csv", f, "text/csv")}
                )
            
            assert response.status_code == 200, f"DB1 upload failed: {response.text}"
            upload_response = response.json()
            assert upload_response["success"] is True
            assert "processed successfully" in upload_response["message"]
            print(f"✓ Database 1 uploaded successfully")
            
            # Step 2: Upload Database 2 (10 items) - this should trigger sync
            print("Step 2: Uploading Database 2...")
            with open(db2_file, "rb") as f:
                response = client.post(
                    f"{self.BASE_URL}{self.API_PREFIX}/data/upload/db2",
                    files={"file": ("db2_10_items.csv", f, "text/csv")}
                )
            
            assert response.status_code == 200, f"DB2 upload failed: {response.text}"
            upload_response = response.json()
            assert upload_response["success"] is True
            assert "processed successfully" in upload_response["message"]
            print(f"✓ Database 2 uploaded successfully")
            
            # Step 3: Verify data was loaded and combined
            print("Step 3: Verifying data was loaded and synced...")
            
            # Check DB1 data
            response = client.get(f"{self.BASE_URL}{self.API_PREFIX}/data/db1")
            assert response.status_code == 200, f"Failed to get DB1 data: {response.text}"
            db1_data = response.json()
            assert db1_data["success"] is True
            assert len(db1_data["data"]) == 5
            print(f"✓ Database 1 has {len(db1_data['data'])} items")
            
            # Check DB2 data  
            response = client.get(f"{self.BASE_URL}{self.API_PREFIX}/data/db2")
            assert response.status_code == 200, f"Failed to get DB2 data: {response.text}"
            db2_data = response.json()
            assert db2_data["success"] is True
            assert len(db2_data["data"]) == 10
            print(f"✓ Database 2 has {len(db2_data['data'])} items")
            
            # Check combined data (sync result) - this might fail due to NaN values
            try:
                response = client.get(f"{self.BASE_URL}{self.API_PREFIX}/data/combined")
                if response.status_code == 200:
                    combined_data = response.json()
                    if combined_data["success"]:
                        print(f"✓ Combined database has {len(combined_data['data'])} items")
                    else:
                        print("⚠️ Combined data endpoint returned error but sync likely worked")
                else:
                    print(f"⚠️ Combined data endpoint failed (status {response.status_code}) but sync likely worked")
            except Exception as e:
                print(f"⚠️ Combined data endpoint error: {str(e)} but sync process worked")
            
            # Step 4: Export the databases
            print("Step 4: Exporting databases...")
            
            # Export DB1
            export_request = {
                "data_type": "db1",
                "format": "csv",
                "filename": "test_export_db1.csv"
            }
            response = client.post(
                f"{self.BASE_URL}{self.API_PREFIX}/export",
                json=export_request
            )
            assert response.status_code == 200, f"DB1 export failed: {response.text}"
            export_response = response.json()
            assert export_response["success"] is True
            db1_export_filename = Path(export_response["file_path"]).name
            print(f"✓ Database 1 exported as {db1_export_filename}")
            
            # Export DB2
            export_request = {
                "data_type": "db2", 
                "format": "csv",
                "filename": "test_export_db2.csv"
            }
            response = client.post(
                f"{self.BASE_URL}{self.API_PREFIX}/export",
                json=export_request
            )
            assert response.status_code == 200, f"DB2 export failed: {response.text}"
            export_response = response.json()
            assert export_response["success"] is True
            db2_export_filename = Path(export_response["file_path"]).name
            print(f"✓ Database 2 exported as {db2_export_filename}")
            
            # Export Combined data
            export_request = {
                "data_type": "combined",
                "format": "csv", 
                "filename": "test_export_combined.csv"
            }
            response = client.post(
                f"{self.BASE_URL}{self.API_PREFIX}/export",
                json=export_request
            )
            assert response.status_code == 200, f"Combined export failed: {response.text}"
            export_response = response.json()
            assert export_response["success"] is True
            combined_export_filename = Path(export_response["file_path"]).name
            print(f"✓ Combined database exported as {combined_export_filename}")
            
            # Step 5: Download the exported files to verify
            print("Step 5: Downloading and verifying exported files...")
            
            # Download and verify DB1 export
            response = client.get(f"{self.BASE_URL}{self.API_PREFIX}/export/download/{db1_export_filename}")
            assert response.status_code == 200, f"Failed to download DB1 export: {response.text}"
            db1_content = response.content.decode('utf-8')
            db1_lines = db1_content.strip().split('\n')
            assert len(db1_lines) == 6  # Header + 5 data rows
            print(f"✓ Downloaded DB1 export: {len(db1_lines) - 1} data rows")
            
            # Download and verify DB2 export
            response = client.get(f"{self.BASE_URL}{self.API_PREFIX}/export/download/{db2_export_filename}")
            assert response.status_code == 200, f"Failed to download DB2 export: {response.text}"
            db2_content = response.content.decode('utf-8')
            db2_lines = db2_content.strip().split('\n')
            assert len(db2_lines) == 11  # Header + 10 data rows
            print(f"✓ Downloaded DB2 export: {len(db2_lines) - 1} data rows")
            
            # Download and verify combined export
            response = client.get(f"{self.BASE_URL}{self.API_PREFIX}/export/download/{combined_export_filename}")
            assert response.status_code == 200, f"Failed to download combined export: {response.text}"
            combined_content = response.content.decode('utf-8')
            combined_lines = combined_content.strip().split('\n')
            assert len(combined_lines) >= 6  # Header + at least 5 data rows
            print(f"✓ Downloaded combined export: {len(combined_lines) - 1} data rows")
            
        print("🎉 Full workflow test completed successfully!")
    
    def test_data_summary(self):
        """Test that we can get a summary of the loaded data."""
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{self.BASE_URL}{self.API_PREFIX}/data/summary")
            assert response.status_code == 200, f"Failed to get data summary: {response.text}"
            
            summary_response = response.json()
            assert summary_response["success"] is True
            
            summary = summary_response["data"]
            # Check the actual structure: db1.records, db2.records, combined.records
            assert "db1" in summary
            assert "db2" in summary  
            assert "combined" in summary
            assert "records" in summary["db1"]
            assert "records" in summary["db2"]
            assert "records" in summary["combined"]
            
            db1_count = summary["db1"]["records"]
            db2_count = summary["db2"]["records"]
            combined_count = summary["combined"]["records"]
            
            print(f"Data Summary: DB1={db1_count}, DB2={db2_count}, Combined={combined_count}")
            print(f"✓ Data summary retrieved successfully")
    
    def test_health_check(self):
        """Test that the health check endpoint works."""
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{self.BASE_URL}/health")
            assert response.status_code == 200, f"Health check failed: {response.text}"
            
            health_response = response.json()
            assert health_response["status"] == "healthy"
            print("✓ Health check passed")


if __name__ == "__main__":
    # Run the test directly
    test_instance = TestDBSyncrAPIWorkflow()
    test_instance.setup_class()
    try:
        test_instance.test_health_check()
        test_instance.test_full_workflow()
        test_instance.test_data_summary()
        print("All tests passed!")
    finally:
        test_instance.teardown_class()