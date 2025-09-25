"""
Shared test configuration for DBSyncr tests
"""
import pytest
import sys
from pathlib import Path
import requests
import subprocess
import time

# Add the project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add src to path for imports
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# --- Register DataService in DI container for all tests ---
from src.services.data_service import DataService
from src.config.settings import config_manager
from src.utils.logging_config import get_logger
from src.utils.dependency_injection import register_instance

# Ensure ServiceFactory cache is cleared before and after each test
import pytest
from src.services.service_factory import ServiceFactory

@pytest.fixture(autouse=True)
def reset_service_factory_cache():
    ServiceFactory.clear_cache()
    yield
    ServiceFactory.clear_cache()


@pytest.fixture(scope="session", autouse=True)
def register_data_service():
    """Register DataService in the DI container for all tests."""
    instance = DataService(config_manager=config_manager, logger=get_logger("DataService"))
    register_instance(DataService, instance)
    yield
    # Optionally clear the DI container after tests if needed


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_data_dir(project_root):
    """Return the test data directory."""
    return project_root / "tests" / "test_data"


@pytest.fixture
def api_base_url():
    """Base URL for the API server."""
    return "http://localhost:8000"


@pytest.fixture
def api_prefix():
    """API prefix for endpoints."""
    return "/api/v1"


@pytest.fixture
def e2e_api_url():
    """API URL for E2E tests - can be overridden by environment."""
    import os
    return os.getenv("E2E_API_URL", "http://localhost:8000")


@pytest.fixture
def e2e_auth_credentials():
    """Authentication credentials for E2E tests."""
    import os
    return {
        "username": os.getenv("E2E_USERNAME", "admin"),
        "password": os.getenv("E2E_PASSWORD", "admin123")
    }


@pytest.fixture
def test_csv_data():
    """Sample CSV data for testing."""
    import pandas as pd
    return pd.DataFrame({
        'sku': ['TEST001', 'TEST002', 'TEST003'],
        'product_name': ['Test Product 1', 'Test Product 2', 'Test Product 3'],
        'price': [10.99, 20.50, 15.75],
        'quantity': [100, 50, 75]
    })


@pytest.fixture
def test_excel_data():
    """Sample Excel data for testing."""
    import pandas as pd
    return pd.DataFrame({
        'product_code': ['EXCEL001', 'EXCEL002'],
        'item_name': ['Excel Product 1', 'Excel Product 2'],
        'unit_price': [25.00, 30.00],
        'stock_level': [200, 150]
    })


@pytest.fixture
def field_mappings_config():
    """Sample field mappings configuration."""
    return {
        "primary_key": "sku",
        "mappings": {
            "product_name": "item_name",
            "price": "unit_price",
            "quantity": "stock_level"
        }
    }


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Clean up temporary files created during tests."""
    import tempfile
    import shutil

    # This fixture runs automatically before and after each test
    temp_dir = Path(tempfile.gettempdir()) / "dbsyncr_test_temp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

    temp_dir.mkdir(exist_ok=True)

    yield

    # Cleanup after test
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session", autouse=False)
def ensure_api_running(request):
    """
    Ensure the FastAPI server is running locally before API/integration/E2E tests.
    Starts the API if not reachable, and tears it down after tests if started by this fixture.
    Usage: add 'ensure_api_running' as a fixture to any test or conftest fixture that interacts with the API.
    """
    api_url = "http://localhost:8000/health"
    started = False
    proc = None
    try:
        # Try to reach the API health endpoint
        for _ in range(5):
            try:
                resp = requests.get(api_url, timeout=1)
                if resp.status_code == 200:
                    yield  # API is already running, just yield control
                    return
            except Exception:
                time.sleep(1)
        # Not running, so start it
        proc = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000"
        ])
        started = True
        # Wait for API to be up
        for _ in range(10):
            try:
                resp = requests.get(api_url, timeout=1)
                if resp.status_code == 200:
                    break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError("API server did not start in time.")
        yield
    finally:
        if started and proc:
            proc.terminate()
            proc.wait()

# Example usage in a test or fixture:
# def test_api_something(ensure_api_running):
#     ...