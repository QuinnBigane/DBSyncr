"""
Test configuration and fixtures for UPS Data Manager
"""
import pytest
import os
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

@pytest.fixture
def test_data_dir():
    """Provide test data directory."""
    return project_root / "tests" / "test_data"

@pytest.fixture
def sample_mappings():
    """Provide sample field mappings for testing."""
    return {
        "database_names": {
            "db1_name": "NetSuite",
            "db2_name": "Shopify"
        },
        "field_mappings": {
            "Weight": {
                "netsuite_field": "Weight",
                "shopify_field": "Variant Weight",
                "direction": "bidirectional",
                "description": "Maps Weight to Variant Weight"
            }
        },
        "data_sources": {
            "netsuite": {
                "file_path": "test_netsuite.csv",
                "file_type": "csv"
            },
            "shopify": {
                "file_path": "test_shopify.csv",
                "file_type": "csv"
            }
        },
        "primary_link": {
            "netsuite": "SKU",
            "shopify": "Variant SKU"
        }
    }