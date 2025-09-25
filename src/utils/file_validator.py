"""
File validation utilities for API uploads.
"""
import os
from typing import Optional, Dict, Any, List
from pathlib import Path
import pandas as pd
from utils.logging_config import get_logger

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    magic = None
    HAS_MAGIC = False


class FileValidator:
    """Utility class for validating uploaded files."""

    # Allowed file types
    ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}
    ALLOWED_MIME_TYPES = {
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }

    # Size limits (in bytes)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_ROWS = 100000  # Maximum rows allowed

    def __init__(self, logger=None):
        self.logger = logger or get_logger("FileValidator")

    def validate_file(self, file_content: bytes, filename: str,
                     content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate an uploaded file.

        Returns:
            Dict with validation results and file info
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "file_info": {
                "filename": filename,
                "size": len(file_content),
                "content_type": content_type,
                "detected_mime": None,
                "extension": Path(filename).suffix.lower(),
                "row_count": None,
                "column_count": None
            }
        }

        # Check file size
        if len(file_content) > self.MAX_FILE_SIZE:
            result["valid"] = False
            result["errors"].append(f"File size ({len(file_content)} bytes) exceeds maximum allowed size ({self.MAX_FILE_SIZE} bytes)")

        # Check file extension
        if result["file_info"]["extension"] not in self.ALLOWED_EXTENSIONS:
            result["valid"] = False
            result["errors"].append(f"File extension '{result['file_info']['extension']}' not allowed. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}")

        # Detect MIME type
        if HAS_MAGIC:
            try:
                detected_mime = magic.from_buffer(file_content, mime=True)
                result["file_info"]["detected_mime"] = detected_mime

                if detected_mime not in self.ALLOWED_MIME_TYPES:
                    result["valid"] = False
                    result["errors"].append(f"Detected MIME type '{detected_mime}' not allowed. Allowed: {', '.join(self.ALLOWED_MIME_TYPES)}")
            except Exception as e:
                result["warnings"].append(f"Could not detect MIME type: {e}")
        else:
            result["warnings"].append("MIME type detection not available (python-magic not installed)")
            # Fallback: check content type from upload if provided
            if content_type and content_type not in self.ALLOWED_MIME_TYPES:
                result["warnings"].append(f"Content-Type '{content_type}' may not be allowed. Allowed: {', '.join(self.ALLOWED_MIME_TYPES)}")

        # Validate file content can be read
        if result["valid"]:
            content_validation = self._validate_file_content(file_content, filename)
            result["errors"].extend(content_validation.get("errors", []))
            result["warnings"].extend(content_validation.get("warnings", []))
            result["file_info"].update(content_validation.get("file_info", {}))

            if content_validation.get("errors"):
                result["valid"] = False

        # If file has no columns, or a single unnamed column (pandas fallback), mark as invalid
        col_count = result["file_info"].get("column_count")
        if col_count == 0 or (
            col_count == 1 and result["file_info"].get("row_count") is not None and
            result["file_info"].get("filename", "").endswith('.csv')
        ):
            if not any("no columns" in err for err in result["errors"]):
                result["errors"].append("File contains no columns")
            result["valid"] = False

        return result

    def _validate_file_content(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Validate that file content can be properly parsed."""
        result = {"errors": [], "warnings": [], "file_info": {}}

        try:
            # Save to temporary file for pandas to read
            temp_path = self._save_temp_file(file_content, filename)

            try:
                if filename.lower().endswith('.csv'):
                    df = pd.read_csv(temp_path, nrows=self.MAX_ROWS + 1)
                else:  # Excel files
                    df = pd.read_excel(temp_path, nrows=self.MAX_ROWS + 1)

                # Check row count
                if len(df) > self.MAX_ROWS:
                    result["errors"].append(f"File contains {len(df)} rows, exceeding maximum allowed ({self.MAX_ROWS})")
                else:
                    result["file_info"]["row_count"] = len(df)

                # Check column count
                result["file_info"]["column_count"] = len(df.columns)

                # Check for empty file
                if len(df) == 0:
                    result["errors"].append("File appears to be empty or contains no data rows")

                # Check for required columns (basic validation)
                if len(df.columns) == 0:
                    result["errors"].append("File contains no columns")

                # Check for potential data quality issues
                if df.isnull().all().all():
                    result["warnings"].append("File appears to contain only null values")

            except Exception as e:
                result["errors"].append(f"Could not parse file content: {str(e)}")
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass

        except Exception as e:
            result["errors"].append(f"Could not process file: {str(e)}")

        return result

    def _save_temp_file(self, content: bytes, filename: str) -> str:
        """Save content to a temporary file and return the path."""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
            temp_file.write(content)
            return temp_file.name

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent security issues."""
        # Remove path separators and dangerous characters
        import re
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = filename.strip()

        # Ensure it has an extension
        if not Path(filename).suffix:
            filename += '.csv'  # Default to CSV

        return filename

    def get_file_summary(self, validation_result: Dict[str, Any]) -> str:
        """Generate a human-readable summary of file validation."""
        if not validation_result["valid"]:
            return f"Invalid file: {', '.join(validation_result['errors'])}"

        info = validation_result["file_info"]
        summary = f"Valid {info['extension'][1:].upper()} file"

        if info.get("row_count") is not None:
            summary += f" with {info['row_count']} rows"

        if info.get("column_count") is not None:
            summary += f" and {info['column_count']} columns"

        if validation_result["warnings"]:
            summary += f" (Warnings: {', '.join(validation_result['warnings'])})"

        return summary


# Global validator instance
file_validator = FileValidator()