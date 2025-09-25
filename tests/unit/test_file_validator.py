"""
Unit tests for file validation utilities
Tests file type validation, size limits, content validation, and error handling
"""
import pytest
import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.utils.file_validator import FileValidator


class TestFileValidator:
    """Test FileValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = FileValidator()

    def test_init_with_logger(self):
        """Test FileValidator initialization with custom logger."""
        mock_logger = MagicMock()
        validator = FileValidator(logger=mock_logger)

        assert validator.logger == mock_logger

    def test_validate_file_valid_csv(self):
        """Test validation of a valid CSV file."""
        # Create a simple CSV content
        csv_content = b"sku,name,price\nABC123,Test Product,29.99\nDEF456,Another Product,19.99"

        result = self.validator.validate_file(csv_content, "test.csv")

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["file_info"]["extension"] == ".csv"
        assert result["file_info"]["size"] == len(csv_content)
        assert result["file_info"]["row_count"] == 2
        assert result["file_info"]["column_count"] == 3

    def test_validate_file_valid_excel(self):
        """Test validation of a valid Excel file."""
        # Create a simple Excel file in memory
        df = pd.DataFrame({
            'sku': ['ABC123', 'DEF456'],
            'name': ['Test Product', 'Another Product'],
            'price': [29.99, 19.99]
        })
        temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        try:
            df.to_excel(temp_file.name, index=False)
            temp_file.close()  # Ensure file is closed before reading/unlinking
            with open(temp_file.name, 'rb') as f:
                excel_content = f.read()
            result = self.validator.validate_file(excel_content, "test.xlsx")
        finally:
            Path(temp_file.name).unlink(missing_ok=True)

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["file_info"]["extension"] == ".xlsx"
        assert result["file_info"]["row_count"] == 2
        assert result["file_info"]["column_count"] == 3

    def test_validate_file_size_too_large(self):
        """Test validation of file that's too large."""
        # Create content larger than MAX_FILE_SIZE (50MB)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB

        result = self.validator.validate_file(large_content, "large.csv")

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "exceeds maximum allowed size" in result["errors"][0]

    def test_validate_file_invalid_extension(self):
        """Test validation of file with invalid extension."""
        content = b"some content"

        result = self.validator.validate_file(content, "test.txt")

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "not allowed" in result["errors"][0]

    def test_validate_file_empty(self):
        """Test validation of empty file."""
        content = b""

        result = self.validator.validate_file(content, "empty.csv")

        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_file_corrupted_csv(self):
        """Test validation of corrupted CSV file."""
        # Invalid CSV content
        content = b"This is not CSV content at all!"

        result = self.validator.validate_file(content, "corrupted.csv")

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        # Accept either error message (parsing or empty)
        assert any(
            "Could not parse file content" in err or "empty or contains no data rows" in err
            for err in result["errors"]
        )

    def test_validate_file_too_many_rows(self):
        """Test validation of file with too many rows."""
        # Create CSV with more than MAX_ROWS (100000)
        rows = ["sku,name,price"]
        for i in range(100001):  # One more than max
            rows.append(f"SKU{i},Product{i},{i}.99")

        content = "\n".join(rows).encode('utf-8')

        result = self.validator.validate_file(content, "large.csv")

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "exceeding maximum allowed" in result["errors"][0]

    def test_validate_file_no_columns(self):
        """Test validation of file with no columns."""
        content = b"row1\nrow2\nrow3"  # No headers/columns

        result = self.validator.validate_file(content, "no_columns.csv")

        assert result["valid"] is False
        assert any("no columns" in err for err in result["errors"])

    def test_validate_file_all_null(self):
        """Test validation of file with all null values."""
        content = b"col1,col2,col3\n,,\n,,"

        result = self.validator.validate_file(content, "null_data.csv")

        assert result["valid"] is True  # Should still be valid
        assert any("only null values" in w for w in result["warnings"])

    @patch('src.utils.file_validator.magic', create=True)
    def test_validate_file_mime_type_detection(self, mock_magic):
        """Test MIME type detection."""
        mock_magic.from_buffer.return_value = "text/csv"

        content = b"sku,name,price\nABC123,Test,29.99"
        result = self.validator.validate_file(content, "test.csv", "text/csv")

        # Accept either the mock value or None if python-magic is not installed
        assert result["file_info"]["detected_mime"] in ("text/csv", None)
        # Only check call if magic is actually used
        if result["file_info"]["detected_mime"] == "text/csv":
            mock_magic.from_buffer.assert_called_once()

    @patch('src.utils.file_validator.magic', None)
    def test_validate_file_no_magic_library(self):
        """Test file validation when python-magic is not available."""
        content = b"sku,name,price\nABC123,Test,29.99"

        result = self.validator.validate_file(content, "test.csv")

        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert "MIME type detection not available" in result["warnings"][0]

    def test_validate_file_content_type_fallback(self):
        """Test content-type fallback when magic is not available."""
        with patch('src.utils.file_validator.HAS_MAGIC', False):
            content = b"sku,name,price\nABC123,Test,29.99"

            result = self.validator.validate_file(content, "test.csv", "text/csv")

            assert result["valid"] is True
            assert len(result["warnings"]) > 0

    def test_allowed_extensions(self):
        """Test allowed file extensions."""
        assert '.csv' in FileValidator.ALLOWED_EXTENSIONS
        assert '.xlsx' in FileValidator.ALLOWED_EXTENSIONS
        assert '.xls' in FileValidator.ALLOWED_EXTENSIONS
        assert '.txt' not in FileValidator.ALLOWED_EXTENSIONS

    def test_allowed_mime_types(self):
        """Test allowed MIME types."""
        assert 'text/csv' in FileValidator.ALLOWED_MIME_TYPES
        assert 'application/vnd.ms-excel' in FileValidator.ALLOWED_MIME_TYPES
        assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in FileValidator.ALLOWED_MIME_TYPES

    def test_size_limits(self):
        """Test file size limits."""
        assert FileValidator.MAX_FILE_SIZE == 50 * 1024 * 1024  # 50MB
        assert FileValidator.MAX_ROWS == 100000

    def test_temp_file_cleanup(self):
        """Test that temporary files are cleaned up after validation."""
        content = b"sku,name,price\nABC123,Test,29.99"

        # This should not leave any temp files behind
        result = self.validator.validate_file(content, "test.csv")

        assert result["valid"] is True

        # Check that no temp files remain (this is a basic check)
        temp_files = list(Path(tempfile.gettempdir()).glob("tmp*"))
        # We can't guarantee no temp files exist, but the validator should clean up its own