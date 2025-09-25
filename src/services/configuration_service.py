"""
Configuration Service
Handles configuration management including field mappings, database names, and linking fields.
"""
import json
import os
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path


class ConfigurationService:
    """Service for managing application configuration."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        # Configuration file paths
        self.field_mappings_file = self.config_dir / "field_mappings.json"
        self.database_names_file = self.config_dir / "database_names.json"
        self.linking_config_file = self.config_dir / "linking_config.json"
        self.data_sources_file = self.config_dir / "data_sources.json"

    def load_field_mappings(self) -> Dict[str, Any]:
        """Load field mappings from configuration file."""
        try:
            if self.field_mappings_file.exists():
                with open(self.field_mappings_file, 'r') as f:
                    return json.load(f)
            else:
                return self._get_default_field_mappings()
        except Exception as e:
            print(f"Error loading field mappings: {e}")
            return self._get_default_field_mappings()

    def save_field_mappings(self, mappings: Dict[str, Any]) -> bool:
        """Save field mappings to configuration file."""
        try:
            with open(self.field_mappings_file, 'w') as f:
                json.dump(mappings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving field mappings: {e}")
            return False

    def load_database_names(self) -> Tuple[str, str]:
        """Load database names from configuration file."""
        try:
            if self.database_names_file.exists():
                with open(self.database_names_file, 'r') as f:
                    data = json.load(f)
                    return data.get('db1_name', 'Database1'), data.get('db2_name', 'Database2')
            else:
                return 'Database1', 'Database2'
        except Exception as e:
            print(f"Error loading database names: {e}")
            return 'Database1', 'Database2'

    def save_database_names(self, db1_name: str, db2_name: str) -> bool:
        """Save database names to configuration file."""
        try:
            data = {'db1_name': db1_name, 'db2_name': db2_name}
            with open(self.database_names_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving database names: {e}")
            return False

    def load_linking_configuration(self) -> Dict[str, Any]:
        """Load linking field configuration."""
        try:
            if self.linking_config_file.exists():
                with open(self.linking_config_file, 'r') as f:
                    return json.load(f)
            else:
                return self._get_default_linking_config()
        except Exception as e:
            print(f"Error loading linking configuration: {e}")
            return self._get_default_linking_config()

    def save_linking_field(self, linking_field: str) -> bool:
        """Save linking field configuration."""
        try:
            config = self.load_linking_configuration()
            config['linking_field'] = linking_field
            with open(self.linking_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving linking field: {e}")
            return False

    def load_data_sources(self) -> Dict[str, Any]:
        """Load configured data sources."""
        try:
            if self.data_sources_file.exists():
                with open(self.data_sources_file, 'r') as f:
                    return json.load(f)
            else:
                return self._get_default_data_sources()
        except Exception as e:
            print(f"Error loading data sources: {e}")
            return self._get_default_data_sources()

    def save_data_sources(self, sources: Dict[str, Any]) -> bool:
        """Save data sources configuration."""
        try:
            with open(self.data_sources_file, 'w') as f:
                json.dump(sources, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving data sources: {e}")
            return False

    def get_available_fields(self, data_service) -> Dict[str, List[str]]:
        """Get available fields from loaded data."""
        available_fields = {'db1': [], 'db2': []}

        try:
            combined_data = data_service.get_combined_data()
            if combined_data is not None:
                db1_name, db2_name = data_service.get_database_names()

                # Get DB1 fields
                db1_cols = [col for col in combined_data.columns if col.startswith(f'{db1_name}_')]
                available_fields['db1'] = [col.replace(f'{db1_name}_', '') for col in db1_cols]

                # Get DB2 fields
                db2_cols = [col for col in combined_data.columns if col.startswith(f'{db2_name}_')]
                available_fields['db2'] = [col.replace(f'{db2_name}_', '') for col in db2_cols]

        except Exception as e:
            print(f"Error getting available fields: {e}")

        return available_fields

    def _get_default_field_mappings(self) -> Dict[str, Any]:
        """Get default field mappings."""
        return {
            "mappings": [],
            "last_updated": None
        }

    def _get_default_linking_config(self) -> Dict[str, Any]:
        """Get default linking configuration."""
        return {
            "linking_field": "SKU",
            "case_sensitive": False,
            "trim_whitespace": True
        }

    def _get_default_data_sources(self) -> Dict[str, Any]:
        """Get default data sources configuration."""
        return {
            "db1": {
                "type": "csv",
                "path": "data/dev/inputs/db1_data.csv",
                "enabled": True
            },
            "db2": {
                "type": "csv",
                "path": "data/dev/inputs/db2_data.csv",
                "enabled": True
            }
        }