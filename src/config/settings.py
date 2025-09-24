"""
Configuration Management for UPS Data Manager
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path
import json

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    app_name: str = "UPS Data Manager"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use PORT environment variable if available (Render.com compatibility)
        if "PORT" in os.environ:
            self.api_port = int(os.environ["PORT"])
    
    # File paths
    data_dir: str = Field(default="data", env="DATA_DIR")
    input_dir: str = Field(default="input_data", env="INPUT_DIR")
    output_dir: str = Field(default="output_data", env="OUTPUT_DIR")
    logs_dir: str = Field(default="logs", env="LOGS_DIR")
    exports_dir: str = Field(default="exports", env="EXPORTS_DIR")
    backups_dir: str = Field(default="backups", env="BACKUPS_DIR")
    
    # Database settings (for future use)
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # Field mappings
    field_mappings_file: str = Field(default="field_mappings.json", env="FIELD_MAPPINGS_FILE")
    
    # Security settings
    secret_key: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")
    
    # Upload settings
    max_upload_size: int = Field(default=50 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 50MB
    allowed_file_types: list = Field(default=[".xlsx", ".xls", ".csv"], env="ALLOWED_FILE_TYPES")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class ConfigManager:
    """Configuration manager for the UPS Data Manager application."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.settings = Settings()
        self.project_root = Path(__file__).parent.parent.parent
        self.config_file = config_file or self.project_root / "field_mappings.json"
        
        # Ensure directories exist
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist."""
        dirs_to_create = [
            self.settings.data_dir,
            self.settings.input_dir,
            self.settings.output_dir,
            self.settings.logs_dir,
            self.settings.exports_dir,
            self.settings.backups_dir
        ]
        
        for dir_name in dirs_to_create:
            dir_path = self.project_root / dir_name
            dir_path.mkdir(exist_ok=True)
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert relative path to absolute path from project root."""
        return self.project_root / relative_path
    
    def load_field_mappings(self) -> Dict[str, Any]:
        """Load field mappings from configuration file."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return default configuration
            return self._get_default_field_mappings()
        except json.JSONDecodeError as e:
            # Log warning and return default configuration
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Invalid JSON in field mappings file: {e}. Using default mappings.")
            return self._get_default_field_mappings()
    
    def save_field_mappings(self, mappings: Dict[str, Any]):
        """Save field mappings to configuration file."""
        with open(self.config_file, 'w') as f:
            json.dump(mappings, f, indent=2)
    
    def _get_default_field_mappings(self) -> Dict[str, Any]:
        """Get default field mappings configuration."""
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
                },
                "Purchase Price": {
                    "netsuite_field": "Purchase Price",
                    "shopify_field": "Variant Cost",
                    "direction": "bidirectional",
                    "description": "Maps Purchase Price to Variant Cost"
                },
                "Shopify (sp)": {
                    "netsuite_field": "Shopify (sp)",
                    "shopify_field": "Variant Price",
                    "direction": "bidirectional",
                    "description": "Maps Shopify (sp) to Variant Price"
                }
            },
            "data_sources": {
                "netsuite": {
                    "file_path": str(self.get_absolute_path("input_data/NetSuite_TestData.xlsx")),
                    "file_type": "excel"
                },
                "shopify": {
                    "file_path": str(self.get_absolute_path("input_data/Shopify_TestData.xlsx")),
                    "file_type": "excel"
                }
            },
            "primary_link": {
                "netsuite": "SKU",
                "shopify": "Variant SKU"
            }
        }


# Global configuration instance
config_manager = ConfigManager()
settings = config_manager.settings