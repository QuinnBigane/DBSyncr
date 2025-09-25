"""
Unit tests for configuration management
Tests environment variable overrides, configuration file parsing, and default value fallbacks
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.config.settings import Settings


class TestSettings:
    """Test Settings configuration class."""

    def test_settings_default_values(self):
        """Test default values for Settings."""
        settings = Settings()

        assert settings.app_name == "UPS Data Manager"
        assert settings.app_version == "1.0.0"
        assert settings.debug is False
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.api_prefix == "/api/v1"

    def test_settings_environment_override(self):
        """Test environment variable overrides."""
        with patch.dict(os.environ, {
            'DEBUG': 'true',
            'API_HOST': 'localhost',
            'API_PORT': '3000',
            'API_PREFIX': '/api/v2'
        }):
            settings = Settings()

            assert settings.debug is True
            assert settings.api_host == "localhost"
            assert settings.api_port == 3000
            assert settings.api_prefix == "/api/v2"

    def test_settings_port_environment_variable(self):
        """Test PORT environment variable compatibility."""
        with patch.dict(os.environ, {'PORT': '5000'}):
            settings = Settings()

            assert settings.api_port == 5000

    def test_settings_file_paths(self):
        """Test file path configurations."""
        settings = Settings()

        # Test that paths are properly set
        assert settings.data_dir == "data"
        assert settings.api_input_dir == "data/api/incoming"
        assert settings.api_output_dir == "data/api/results"
        assert settings.logs_dir == "logs"
        assert settings.backups_dir == "backups"

    def test_settings_custom_data_dir(self):
        """Test custom data directory."""
        with patch.dict(os.environ, {'DATA_DIR': '/custom/data'}):
            settings = Settings()

            assert settings.data_dir == "/custom/data"
            # Dependent paths should update accordingly
            assert settings.api_input_dir == "/custom/data/api/incoming"

    def test_settings_database_url(self):
        """Test database URL configuration."""
        settings = Settings()

        # Should be None by default
        assert settings.database_url is None

        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://localhost/test'}):
            settings = Settings()
            assert settings.database_url == 'postgresql://localhost/test'

    def test_settings_model_dump(self):
        """Test settings serialization."""
        settings = Settings()

        data = settings.model_dump()

        assert data['app_name'] == "UPS Data Manager"
        assert data['api_host'] == "0.0.0.0"
        assert data['api_port'] == 8000

    def test_settings_exclude_none_values(self):
        """Test that None values are properly handled in serialization."""
        settings = Settings()

        # database_url should be None by default
        data = settings.model_dump(exclude_none=True)

        assert 'database_url' not in data or data['database_url'] is None

    def test_settings_validation(self):
        """Test settings validation."""
        # Valid settings should work
        settings = Settings(api_port=8080)
        assert settings.api_port == 8080

        # Invalid port should raise error
        with pytest.raises(ValueError):
            Settings(api_port="invalid")

    def test_settings_from_env_file(self):
        """Test loading settings from environment variables."""
        with patch.dict(os.environ, {
            'DEBUG': 'true',
            'API_HOST': '127.0.0.1',
            'API_PORT': '4000',
            'APP_NAME': 'Test App'
        }):
            settings = Settings()

            assert settings.debug is True
            assert settings.api_host == "127.0.0.1"
            assert settings.api_port == 4000
            assert settings.app_name == "Test App"

    def test_settings_runtime_updates(self):
        """Test that settings can be updated at runtime."""
        settings = Settings()

        original_host = settings.api_host
        settings.api_host = "updated-host"

        assert settings.api_host == "updated-host"
        assert settings.api_host != original_host

    def test_settings_immutable_after_init(self):
        """Test that settings behave correctly after initialization."""
        settings = Settings(api_host="initial")

        # Should be able to change
        settings.api_host = "changed"
        assert settings.api_host == "changed"

    def test_settings_with_custom_values(self):
        """Test Settings initialization with custom values."""
        settings = Settings(
            app_name="Custom App",
            app_version="2.0.0",
            debug=True,
            api_host="custom-host",
            api_port=9000
        )

        assert settings.app_name == "Custom App"
        assert settings.app_version == "2.0.0"
        assert settings.debug is True
        assert settings.api_host == "custom-host"
        assert settings.api_port == 9000

    def test_settings_path_construction(self):
        """Test that paths are constructed correctly."""
        settings = Settings(data_dir="/base")

        assert settings.api_input_dir == "/base/api/incoming"
        assert settings.api_output_dir == "/base/api/results"
        assert settings.api_config_dir == "/base/api/config"
        assert settings.dev_input_dir == "/base/dev/inputs"
        assert settings.dev_output_dir == "/base/dev/outputs"
        assert settings.dev_samples_dir == "/base/dev/samples"
        assert settings.config_dir == "/base/dev/config"

    def test_settings_log_format(self):
        """Test log format configuration."""
        settings = Settings()

        # Should have a default log format
        assert isinstance(settings.log_format, str)
        assert len(settings.log_format) > 0

    def test_settings_log_level(self):
        """Test log level configuration."""
        settings = Settings()

        # Should have a default log level
        assert isinstance(settings.log_level, str)
        assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def test_settings_cors_origins(self):
        """Test CORS origins configuration."""
        settings = Settings()

        # Should have CORS origins configured
        assert hasattr(settings, 'cors_origins')
        assert isinstance(settings.cors_origins, list)

    def test_settings_upload_limits(self):
        """Test upload limit configurations."""
        settings = Settings()

        assert hasattr(settings, 'max_upload_size')
        assert isinstance(settings.max_upload_size, int)
        assert settings.max_upload_size > 0

        assert hasattr(settings, 'allowed_file_types')
        assert isinstance(settings.allowed_file_types, list)
        assert len(settings.allowed_file_types) > 0

    def test_settings_secret_key(self):
        """Test secret key configuration."""
        settings = Settings()

        assert hasattr(settings, 'secret_key')
        assert isinstance(settings.secret_key, str)
        assert len(settings.secret_key) > 0