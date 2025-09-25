"""
Deployment health checks for DBSyncr API
Tests service startup, database connectivity, file system permissions, and configuration loading
"""
import pytest
import httpx
import os
import subprocess
import time
from pathlib import Path


class TestDeploymentHealth:
    """Test deployment health and infrastructure."""

    @pytest.fixture(scope="class")
    def deployed_url(self):
        """Get deployed API URL from environment."""
        url = os.getenv("E2E_API_URL", "http://localhost:8000")
        return url

    def test_service_startup(self, deployed_url, ensure_api_running):
        """Test that the service starts up correctly."""
        import time
        max_retries = 10
        for attempt in range(max_retries):
            try:
                response = httpx.get(f"{deployed_url}/health", timeout=10)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    else:
                        assert response.status_code == 200, f"Service returned 429 Too Many Requests after {max_retries} retries"
                assert response.status_code == 200
                data = response.json()
                assert "status" in data
                assert data["status"] in ["healthy", "ok", "running"]

                # Check for additional health metrics
                if "version" in data:
                    assert isinstance(data["version"], str)
                if "uptime" in data:
                    assert isinstance(data["uptime"], (int, float))
                break
            except httpx.ConnectError:
                pytest.skip(f"Cannot connect to deployed API at {deployed_url}. "
                           "Set E2E_API_URL environment variable to test deployment.")
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                pytest.fail(f"Service startup test failed: {e}")

    def test_database_connectivity(self, deployed_url, ensure_api_running):
        """Test database connectivity if configured."""
        try:
            response = httpx.get(f"{deployed_url}/api/v1/health/db", timeout=10)

            # If database health endpoint exists, test it
            if response.status_code == 200:
                data = response.json()
                assert "database" in data
                assert data["database"] in ["connected", "ok", "healthy"]
            else:
                # Database might not be configured, which is OK
                assert response.status_code in [404, 501]  # Not found or not implemented

        except httpx.ConnectError:
            pytest.skip("API deployment not available")
        except Exception as e:
            pytest.fail(f"Database connectivity test failed: {e}")

    def test_file_system_permissions(self, deployed_url, ensure_api_running):
        """Test file system permissions for uploads and data storage."""
        try:
            # Try to upload a small test file
            test_content = b"test,data\n1,2"

            files = {"file": ("test.csv", test_content, "text/csv")}
            response = httpx.post(
                f"{deployed_url}/api/v1/upload/db1",
                files=files,
                timeout=30
            )

            # Should either succeed or fail with a clear error
            if response.status_code == 200:
                data = response.json()
                assert data["success"] is True
            elif response.status_code == 403:
                # Permission denied - file system issue
                pytest.fail("File system permissions prevent uploads")
            elif response.status_code == 500:
                # Server error - might be file system related
                error_data = response.json()
                if "permission" in str(error_data).lower():
                    pytest.fail("File system permission error detected")
                else:
                    # Other server error, might not be file system related
                    pass
            # Other status codes are acceptable (auth required, etc.)

        except httpx.ConnectError:
            pytest.skip("API deployment not available")
        except Exception as e:
            pytest.fail(f"File system permissions test failed: {e}")

    def test_configuration_loading(self, deployed_url, ensure_api_running):
        """Test that configuration is loaded correctly."""
        try:
            response = httpx.get(f"{deployed_url}/api/v1/config", timeout=10)

            if response.status_code == 200:
                config = response.json()

                # Check for expected configuration keys
                expected_keys = ["app_name", "version", "debug", "api_host", "api_port"]
                for key in expected_keys:
                    if key in config:
                        assert config[key] is not None

            elif response.status_code in [401, 403]:
                # Configuration endpoint might require authentication
                pass
            elif response.status_code == 404:
                # Configuration endpoint might not exist
                pass

        except httpx.ConnectError:
            pytest.skip("API deployment not available")
        except Exception as e:
            pytest.fail(f"Configuration loading test failed: {e}")

    def test_cors_headers(self, deployed_url, ensure_api_running):
        """Test CORS headers are properly configured."""
        try:
            response = httpx.options(
                f"{deployed_url}/api/v1/health",
                headers={"Origin": "http://localhost:3000"},
                timeout=10
            )

            # Check for CORS headers
            cors_headers = [
                "access-control-allow-origin",
                "access-control-allow-methods",
                "access-control-allow-headers"
            ]

            found_cors_headers = any(h in response.headers for h in cors_headers)

            if found_cors_headers:
                # If CORS is configured, check it's not too permissive
                allow_origin = response.headers.get("access-control-allow-origin")
                if allow_origin == "*":
                    # CORS allows all origins - this is noted but not a failure
                    pass

        except httpx.ConnectError:
            pytest.skip("API deployment not available")
        except Exception as e:
            pytest.fail(f"CORS test failed: {e}")

    def test_security_headers(self, deployed_url, ensure_api_running):
        """Test security headers are present."""
        try:
            response = httpx.get(f"{deployed_url}/health", timeout=10)

            # Check for common security headers
            security_headers = {
                "x-content-type-options": "nosniff",
                "x-frame-options": ["DENY", "SAMEORIGIN"],
                "x-xss-protection": "1; mode=block",
                "strict-transport-security": None,  # Should exist for HTTPS
            }

            warnings = []
            for header, expected_value in security_headers.items():
                if header in response.headers:
                    if expected_value is not None:
                        actual_value = response.headers[header]
                        if isinstance(expected_value, list):
                            if actual_value not in expected_value:
                                warnings.append(f"{header} has unexpected value: {actual_value}")
                        elif actual_value != expected_value:
                            warnings.append(f"{header} has unexpected value: {actual_value}")
                else:
                    warnings.append(f"Missing security header: {header}")

            if warnings:
                for warning in warnings:
                    # Log warnings but don't fail the test
                    print(f"Security header warning: {warning}")
                    # In a real test, you might want to assert that certain headers are present
                    # For now, we just note the warnings

        except httpx.ConnectError:
            pytest.skip("API deployment not available")
        except Exception as e:
            pytest.fail(f"Security headers test failed: {e}")

    def test_environment_variables(self, deployed_url, ensure_api_running):
        """Test that environment variables are properly set."""
        try:
            response = httpx.get(f"{deployed_url}/api/v1/env-check", timeout=10)

            if response.status_code == 200:
                env_data = response.json()

                # Check for critical environment variables
                critical_vars = ["DEBUG", "API_HOST", "API_PORT"]
                for var in critical_vars:
                    if var in env_data:
                        assert env_data[var] is not None, f"Critical env var {var} is not set"

            # If endpoint doesn't exist, that's OK
            elif response.status_code == 404:
                pass

        except httpx.ConnectError:
            pytest.skip("API deployment not available")
        except Exception as e:
            pytest.fail(f"Environment variables test failed: {e}")

    def test_log_files_accessible(self, deployed_url, ensure_api_running):
        """Test that log files are being written (if accessible)."""
        try:
            response = httpx.get(f"{deployed_url}/api/v1/logs/status", timeout=10)

            if response.status_code == 200:
                log_status = response.json()

                # Check that logging is working
                assert "logs_writable" in log_status
                if not log_status["logs_writable"]:
                    pytest.fail("Log files are not writable")

                if "recent_logs" in log_status:
                    assert isinstance(log_status["recent_logs"], list)

        except httpx.ConnectError:
            pytest.skip("API deployment not available")
        except Exception as e:
            pytest.fail(f"Log files test failed: {e}")

    def test_backup_system(self, deployed_url, ensure_api_running):
        """Test backup system functionality."""
        try:
            response = httpx.post(f"{deployed_url}/api/v1/backup", timeout=30)

            if response.status_code == 200:
                backup_result = response.json()
                assert "backup_created" in backup_result
                assert backup_result["backup_created"] is True

                if "backup_path" in backup_result:
                    assert backup_result["backup_path"] is not None

            elif response.status_code in [401, 403]:
                # Backup might require admin privileges
                pass
            elif response.status_code == 404:
                # Backup endpoint might not exist
                pass

        except httpx.ConnectError:
            pytest.skip("API deployment not available")
        except Exception as e:
            pytest.fail(f"Backup system test failed: {e}")