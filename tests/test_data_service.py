"""
Tests for DataService
"""
import unittest
from unittest.mock import Mock, patch
import pandas as pd
from pathlib import Path
import sys
import os

# Add project paths for testing
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from src.services.data_service import DataService
from src.utils.exceptions import DataProcessingError


class TestDataService(unittest.TestCase):
    """Test cases for DataService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = DataService()
    
    def test_initialization(self):
        """Test service initialization."""
        self.assertIsNotNone(self.service)
        self.assertEqual(self.service.db1_name, "NetSuite")
        self.assertEqual(self.service.db2_name, "Shopify")
    
    def test_get_data_summary_empty(self):
        """Test data summary when no data is loaded."""
        summary = self.service.get_data_summary()
        
        self.assertFalse(summary["netsuite"]["loaded"])
        self.assertFalse(summary["shopify"]["loaded"])
        self.assertFalse(summary["combined"]["loaded"])
        self.assertEqual(summary["netsuite"]["records"], 0)
        self.assertEqual(summary["shopify"]["records"], 0)
    
    @patch('pandas.read_csv')
    def test_load_file_csv(self, mock_read_csv):
        """Test loading CSV file."""
        mock_df = pd.DataFrame({"SKU": ["A", "B"], "Weight": [1.0, 2.0]})
        mock_read_csv.return_value = mock_df
        
        # Create a temporary file path
        test_file = project_root / "test_file.csv"
        test_file.touch()
        
        try:
            result = self.service._load_file(str(test_file))
            self.assertIsInstance(result, pd.DataFrame)
            mock_read_csv.assert_called_once_with(test_file)
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()


if __name__ == '__main__':
    unittest.main()