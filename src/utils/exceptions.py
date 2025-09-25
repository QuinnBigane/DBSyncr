"""
Custom Exceptions for UPS Data Manager
"""


class UPSDataManagerError(Exception):
    """Base exception for UPS Data Manager."""
    pass


class ConfigurationError(UPSDataManagerError):
    """Raised when configuration is invalid or missing."""
    pass


class DataValidationError(UPSDataManagerError):
    """Raised when data validation fails."""
    pass


class FileNotFoundError(UPSDataManagerError):
    """Raised when a required file is not found."""
    pass


class FileFormatError(UPSDataManagerError):
    """Raised when a file format is invalid or unsupported."""
    pass


class DataProcessingError(UPSDataManagerError):
    """Raised when data processing fails."""
    pass


class MappingError(UPSDataManagerError):
    """Raised when field mapping operations fail."""
    pass


class ServiceError(UPSDataManagerError):
    """Raised when a service operation fails."""
    pass


class DatabaseError(UPSDataManagerError):
    """Raised when database operations fail."""
    pass


class AuthenticationError(UPSDataManagerError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(UPSDataManagerError):
    """Raised when authorization fails."""
    pass
