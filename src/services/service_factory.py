"""
Service Factory
Factory for creating service instances with dependency injection.
"""

from src.services.data_service import DataService
from src.services.configuration_service import ConfigurationService
from src.services.filter_service import FilterService
from src.services.api_data_service import ApiDataService
from src.services.auth_service import AuthService
from src.services.rate_limit_service import RateLimitService
from src.services.websocket_service import WebSocketService
from src.config.settings import config_manager
from src.utils.logging_config import get_logger
from src.utils.dependency_injection import resolve, register_instance


class ServiceFactory:
    """Factory for creating service instances."""

    _data_service_instance = None
    _config_service_instance = None
    _filter_service_instance = None
    _api_data_service_instance = None
    _auth_service_instance = None
    _rate_limit_service_instance = None
    _websocket_service_instance = None

    @classmethod
    def create_data_service(cls) -> DataService:
        """Create a DataService instance with dependencies."""
        if cls._data_service_instance is None:
            try:
                # Try to resolve from container first
                cls._data_service_instance = resolve(DataService)
            except (ValueError, KeyError):
                # Fallback to direct creation
                cls._data_service_instance = DataService(
                    config_manager=config_manager,
                    logger=get_logger("DataService")
                )
                # Register the instance for future resolves
                register_instance(DataService, cls._data_service_instance)

        return cls._data_service_instance

    @classmethod
    def create_configuration_service(cls) -> ConfigurationService:
        """Create a ConfigurationService instance."""
        if cls._config_service_instance is None:
            cls._config_service_instance = ConfigurationService()

        return cls._config_service_instance

    @classmethod
    def create_filter_service(cls) -> FilterService:
        """Create a FilterService instance with DataService dependency."""
        if cls._filter_service_instance is None:
            data_service = cls.create_data_service()
            cls._filter_service_instance = FilterService(data_service)

        return cls._filter_service_instance

    @classmethod
    def create_api_data_service(cls) -> ApiDataService:
        """Create an ApiDataService instance."""
        if cls._api_data_service_instance is None:
            cls._api_data_service_instance = ApiDataService(
                logger=get_logger("ApiDataService")
            )

        return cls._api_data_service_instance

    @classmethod
    def create_auth_service(cls) -> AuthService:
        """Create an AuthService instance."""
        if cls._auth_service_instance is None:
            cls._auth_service_instance = AuthService()
            cls._auth_service_instance.logger.info("Created new AuthService instance")

        return cls._auth_service_instance

    @classmethod
    def create_rate_limit_service(cls) -> RateLimitService:
        """Create a RateLimitService instance."""
        if cls._rate_limit_service_instance is None:
            cls._rate_limit_service_instance = RateLimitService()

        return cls._rate_limit_service_instance

    @classmethod
    def create_websocket_service(cls) -> WebSocketService:
        """Create a WebSocketService instance."""
        if cls._websocket_service_instance is None:
            cls._websocket_service_instance = WebSocketService()

        return cls._websocket_service_instance

    @classmethod
    def clear_cache(cls):
        """Clear cached service instances (useful for testing)."""
        cls._data_service_instance = None
        cls._config_service_instance = None
        cls._filter_service_instance = None
        cls._api_data_service_instance = None
        cls._auth_service_instance = None
        cls._rate_limit_service_instance = None
        cls._websocket_service_instance = None