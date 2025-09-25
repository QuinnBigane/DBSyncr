"""
Unit tests for custom exception classes
Tests exception hierarchy and error message handling
"""
import pytest
from src.utils.exceptions import (
    UPSDataManagerError, ConfigurationError, DataValidationError,
    FileNotFoundError, FileFormatError, DataProcessingError,
    MappingError, ServiceError, DatabaseError
)


class TestExceptionHierarchy:
    """Test exception class hierarchy and inheritance."""

    def test_base_exception(self):
        """Test base UPSDataManagerError."""
        error = UPSDataManagerError("Base error message")
        assert str(error) == "Base error message"
        assert isinstance(error, Exception)

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Configuration is invalid")
        assert str(error) == "Configuration is invalid"
        assert isinstance(error, UPSDataManagerError)
        assert isinstance(error, Exception)

    def test_data_validation_error(self):
        """Test DataValidationError."""
        error = DataValidationError("Data validation failed")
        assert str(error) == "Data validation failed"
        assert isinstance(error, UPSDataManagerError)

    def test_file_not_found_error(self):
        """Test FileNotFoundError."""
        error = FileNotFoundError("File not found: test.csv")
        assert str(error) == "File not found: test.csv"
        assert isinstance(error, UPSDataManagerError)

    def test_file_format_error(self):
        """Test FileFormatError."""
        error = FileFormatError("Unsupported file format")
        assert str(error) == "Unsupported file format"
        assert isinstance(error, UPSDataManagerError)

    def test_data_processing_error(self):
        """Test DataProcessingError."""
        error = DataProcessingError("Failed to process data")
        assert str(error) == "Failed to process data"
        assert isinstance(error, UPSDataManagerError)

    def test_mapping_error(self):
        """Test MappingError."""
        error = MappingError("Field mapping failed")
        assert str(error) == "Field mapping failed"
        assert isinstance(error, UPSDataManagerError)

    def test_service_error(self):
        """Test ServiceError."""
        error = ServiceError("Service operation failed")
        assert str(error) == "Service operation failed"
        assert isinstance(error, UPSDataManagerError)

    def test_database_error(self):
        """Test DatabaseError."""
        error = DatabaseError("Database operation failed")
        assert str(error) == "Database operation failed"
        assert isinstance(error, UPSDataManagerError)

    def test_exception_inheritance_chain(self):
        """Test that all exceptions inherit from UPSDataManagerError."""
        exceptions = [
            ConfigurationError("test"),
            DataValidationError("test"),
            FileNotFoundError("test"),
            FileFormatError("test"),
            DataProcessingError("test"),
            MappingError("test"),
            ServiceError("test"),
            DatabaseError("test")
        ]

        for exc in exceptions:
            assert isinstance(exc, UPSDataManagerError)
            assert isinstance(exc, Exception)

    def test_exception_with_custom_messages(self):
        """Test exceptions with various message types."""
        test_messages = [
            "Simple message",
            "Message with numbers: 123",
            "Message with special chars: @#$%",
            "",
            "Very long message " * 10
        ]

        for msg in test_messages:
            error = UPSDataManagerError(msg)
            assert str(error) == msg

    def test_exception_cause_preservation(self):
        """Test that exceptions can preserve original cause."""
        original_error = ValueError("Original error")

        try:
            raise DataValidationError("Validation failed") from original_error
        except DataValidationError as e:
            assert str(e) == "Validation failed"
            assert e.__cause__ is original_error

    def test_exception_context_preservation(self):
        """Test exception context preservation."""
        try:
            try:
                raise ValueError("Inner error")
            except ValueError:
                raise ConfigurationError("Configuration error")
        except ConfigurationError as e:
            assert str(e) == "Configuration error"
            assert isinstance(e.__context__, ValueError)