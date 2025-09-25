"""
Complete end-to-end workflow tests for DBSyncr
Tests the full user journey from data upload through synchronization to export
"""
import pytest
import httpx
import pandas as pd
import time
import os
from pathlib import Path
from typing import Dict, Any
from contextlib import contextmanager


class TestCompleteWorkflowE2E:
    """Test complete user workflows against deployed API."""

    @pytest.fixture(scope="class")
    def api_client(self):
        """Create authenticated API client for E2E tests."""
        base_url = os.getenv("E2E_API_URL", "http://localhost:8000")
        client = httpx.Client(base_url=base_url, timeout=120.0)

        # Attempt authentication
        self._authenticate_client(client)

        return client

    def _authenticate_client(self, client: httpx.Client) -> None:
        """Authenticate the client if authentication is enabled."""
        try:
            auth_data = {
                "username": os.getenv("E2E_USERNAME", "admin"),
                "password": os.getenv("E2E_PASSWORD", "admin123")
            }

            response = client.post("/api/v1/auth/login", json=auth_data)

            if response.status_code == 200:
                token_data = response.json()
                if "access_token" in token_data:
                    client.headers["Authorization"] = f"Bearer {token_data['access_token']}"

        except Exception:
            # Authentication might not be required or configured
            pass

    def _upload_test_data(self, api_client):
        """Helper method to upload test data for synchronization tests."""
        # Create test data
        db1_data = pd.DataFrame({
            'sku': ['WF001', 'WF002', 'WF003'],
            'product_name': ['Workflow Product 1', 'Workflow Product 2', 'Workflow Product 3'],
            'price': [19.99, 29.99, 39.99],
            'quantity': [50, 30, 20]
        })

        db2_data = pd.DataFrame({
            'product_code': ['WF001', 'WF002', 'WF004'],
            'item_name': ['Workflow Product 1', 'Workflow Product 2', 'New Product'],
            'unit_price': [19.99, 29.99, 49.99],
            'stock_level': [50, 30, 15]
        })

        # Upload DB1
        with self._create_temp_csv(db1_data, "db1_workflow.csv") as db1_file:
            files = {"file": ("db1_workflow.csv", db1_file, "text/csv")}
            response1 = api_client.post("/api/v1/data/upload/db1", files=files)

        assert response1.status_code == 200
        upload1_result = response1.json()
        assert upload1_result["success"] is True

        # Upload DB2 (should trigger sync)
        with self._create_temp_csv(db2_data, "db2_workflow.csv") as db2_file:
            files = {"file": ("db2_workflow.csv", db2_file, "text/csv")}
            response2 = api_client.post("/api/v1/data/upload/db2", files=files)

        assert response2.status_code == 200
        upload2_result = response2.json()
        assert upload2_result["success"] is True

        # Wait for processing
        time.sleep(3)

    def test_data_upload_workflow(self, api_client, ensure_api_running):
        """Test complete data upload workflow."""
        try:
            # Upload test data
            self._upload_test_data(api_client)

            # Verify data is accessible
            db1_response = api_client.get("/api/v1/data/db1")
            assert db1_response.status_code == 200
            db1_info = db1_response.json()
            assert db1_info["pagination"]["total_records"] >= 3

            db2_response = api_client.get("/api/v1/data/db2")
            assert db2_response.status_code == 200
            db2_info = db2_response.json()
            assert db2_info["pagination"]["total_records"] >= 3

        except httpx.ConnectError:
            pytest.skip("API deployment not available - skipping E2E workflow test")
        except Exception as e:
            pytest.fail(f"Data upload workflow test failed: {e}")

    def test_data_synchronization_workflow(self, api_client, ensure_api_running):
        """Test data synchronization between databases."""
        try:
            # Upload test data
            self._upload_test_data(api_client)

            # Check synchronization status (if endpoint exists)
            sync_response = api_client.get("/api/v1/sync/status")
            if sync_response.status_code == 200:
                sync_status = sync_response.json()
                assert "last_sync" in sync_status
                assert "sync_in_progress" in sync_status

            # Get combined data
            combined_response = api_client.get("/api/v1/data/combined")
            assert combined_response.status_code == 200
            combined_info = combined_response.json()
            assert combined_info["pagination"]["total_records"] > 0

            # Verify synchronization logic
            export_response = api_client.post("/api/v1/export", json={"data_type": "combined", "format": "csv"})
            assert export_response.status_code == 200
            export_result = export_response.json()
            assert export_result["success"] is True
            
            # Download the exported file
            filename = export_result["file_path"].split("/")[-1]
            combined_data_response = api_client.get(f"/api/v1/export/download/{filename}")
            assert combined_data_response.status_code == 200

            # Parse combined data
            combined_csv = combined_data_response.text
            import io
            combined_df = pd.read_csv(io.StringIO(combined_csv))

            # Should have merged data from both sources
            assert len(combined_df) >= 4  # At least the records we uploaded

            # Check for expected columns (based on field mappings)
            # Combined data has prefixed column names to distinguish sources
            expected_columns = [
                "TestDatabase1_product_name", "TestDatabase1_Key", "TestDatabase1_price", "TestDatabase1_quantity",
                "NormalizedKey",
                "TestDatabase2_item_name", "TestDatabase2_Key", "TestDatabase2_unit_price", "TestDatabase2_stock_level"
            ]
            for col in expected_columns:
                assert col in combined_df.columns, f"Missing expected column: {col}"

        except httpx.ConnectError:
            pytest.skip("API deployment not available - skipping sync workflow test")
        except Exception as e:
            pytest.fail(f"Data synchronization workflow test failed: {e}")

    def test_data_export_workflow(self, api_client, ensure_api_running):
        """Test data export functionality."""
        try:
            # Upload test data
            self._upload_test_data(api_client)

            # Test different export formats
            export_endpoints = [
                {"data_type": "db1"},
                {"data_type": "db2"},
                {"data_type": "combined"}
            ]

            for export_request in export_endpoints:
                response = api_client.post("/api/v1/export", json=export_request)
                assert response.status_code == 200

                export_result = response.json()
                assert export_result["success"] is True
                assert "file_path" in export_result

                # Verify file exists by trying to download it
                filename = export_result["file_path"].split("/")[-1]
                download_response = api_client.get(f"/api/v1/export/download/{filename}")
                assert download_response.status_code == 200

                # Verify content is valid CSV
                csv_content = download_response.text
                assert len(csv_content.strip()) > 0

                # Try to parse as CSV
                import io
                df = pd.read_csv(io.StringIO(csv_content))
                assert len(df) > 0
                assert len(df.columns) > 0

        except httpx.ConnectError:
            pytest.skip("API deployment not available - skipping export workflow test")
        except Exception as e:
            pytest.fail(f"Data export workflow test failed: {e}")

    def test_field_mappings_workflow(self, api_client, ensure_api_running):
        """Test field mappings configuration and application."""
        try:
            # Get current field mappings
            mappings_response = api_client.get("/api/v1/mappings")
            if mappings_response.status_code == 200:
                current_mappings = mappings_response.json()

                # Update field mappings
                new_mappings = {
                    "database_names": {
                        "db1_name": "Test DB1",
                        "db2_name": "Test DB2"
                    },
                    "primary_link": {
                        "db1": "sku",
                        "db2": "product_code"
                    },
                    "field_mappings": {
                        "product_name": {
                            "db1_field": "product_name",
                            "db2_field": "item_name",
                            "direction": "bidirectional"
                        },
                        "price": {
                            "db1_field": "price",
                            "db2_field": "unit_price",
                            "direction": "bidirectional"
                        },
                        "quantity": {
                            "db1_field": "quantity",
                            "db2_field": "stock_level",
                            "direction": "bidirectional"
                        }
                    },
                    "data_sources": {}
                }

                update_response = api_client.put("/api/v1/mappings", json=new_mappings)
                assert update_response.status_code == 200

                # Verify mappings were updated
                verify_response = api_client.get("/api/v1/mappings")
                assert verify_response.status_code == 200
                updated_mappings = verify_response.json()

                assert updated_mappings["data"]["primary_link"]["db1"] == "sku"
                assert "product_name" in updated_mappings["data"]["field_mappings"]

            elif mappings_response.status_code in [401, 403, 404]:
                # Field mappings endpoint might not exist or require auth
                pytest.skip("Field mappings endpoint not available")

        except httpx.ConnectError:
            pytest.skip("API deployment not available - skipping field mappings test")
        except Exception as e:
            pytest.fail(f"Field mappings workflow test failed: {e}")

    def test_error_handling_workflow(self, api_client, ensure_api_running):
        """Test error handling in workflows."""
        try:
            # Test invalid file upload
            invalid_content = b"This is not a CSV file"
            files = {"file": ("invalid.txt", invalid_content, "text/plain")}
            response = api_client.post("/api/v1/upload/db1", files=files)

            # Should return an error status
            assert response.status_code >= 400

            error_data = response.json()
            assert "error" in error_data or "detail" in error_data

            # Test accessing non-existent database
            nonexistent_response = api_client.get("/api/v1/databases/nonexistent")
            assert nonexistent_response.status_code in [404, 400]

            # Test invalid export request
            invalid_export = api_client.get("/api/v1/export/invalid_db")
            assert invalid_export.status_code in [404, 400]

        except httpx.ConnectError:
            pytest.skip("API deployment not available - skipping error handling test")
        except Exception as e:
            pytest.fail(f"Error handling workflow test failed: {e}")

    def test_concurrent_user_workflow(self, api_client, ensure_api_running):
        """Test multiple users performing operations concurrently."""
        try:
            # This is a simplified test - in a real scenario you'd use multiple clients
            # For now, just test that the API can handle rapid sequential requests

            results = []
            for i in range(5):
                response = api_client.get("/health")
                results.append(response.status_code)
                time.sleep(0.1)  # Small delay between requests

            # All requests should succeed
            assert all(status == 200 for status in results)

        except httpx.ConnectError:
            pytest.skip("API deployment not available - skipping concurrent workflow test")
        except Exception as e:
            pytest.fail(f"Concurrent user workflow test failed: {e}")

    def test_large_dataset_workflow(self, api_client, ensure_api_running):
        """Test handling of larger datasets."""
        try:
            # Create a larger dataset (but not too large for testing)
            large_data = pd.DataFrame({
                'sku': [f'LARGE{i:04d}' for i in range(100)],
                'product_name': [f'Large Product {i}' for i in range(100)],
                'price': [round(10.0 + i * 0.5, 2) for i in range(100)],
                'quantity': [100 + i for i in range(100)]
            })

            with self._create_temp_csv(large_data, "large_dataset.csv") as csv_file:
                files = {"file": ("large_dataset.csv", csv_file, "text/csv")}
                response = api_client.post("/api/v1/data/upload/db1", files=files)

            assert response.status_code == 200
            upload_result = response.json()
            assert upload_result["success"] is True

            # Verify large dataset was processed
            db1_response = api_client.get("/api/v1/data/db1")
            assert db1_response.status_code == 200
            db1_info = db1_response.json()
            assert db1_info["pagination"]["total_records"] >= 100

        except httpx.ConnectError:
            pytest.skip("API deployment not available - skipping large dataset test")
        except Exception as e:
            pytest.fail(f"Large dataset workflow test failed: {e}")

    @contextmanager
    def _create_temp_csv(self, df: pd.DataFrame, filename: str):
        """Context manager for creating temporary CSV files."""
        import tempfile
        import os

        temp_fd, temp_path = tempfile.mkstemp(suffix='.csv')
        try:
            df.to_csv(temp_path, index=False)
            with open(temp_path, 'rb') as f:
                yield f
        finally:
            os.close(temp_fd)
            Path(temp_path).unlink(missing_ok=True)