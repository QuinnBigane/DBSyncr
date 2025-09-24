"""
Backward-compatible backend wrapper for DBSyncr
This maintains the original backend interface while using the new service layer.
"""
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from src.services.data_service import DataService
from src.utils.logging_config import get_logger
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd


class DataBackend:
    """
    Backward-compatible backend wrapper that uses the new modular architecture.
    This ensures the existing GUI continues to work without changes.
    """
    
    def __init__(self, mappings_file: str = "field_mappings.json"):
        """Initialize the backend with the new service layer."""
        self._logger = get_logger("BackendWrapper")
        self.service = DataService()
        
        # Maintain backward compatibility attributes
        self.mappings_file = mappings_file
        self.mappings = {}
        self.linking_config = {}
        
        # Initialize data loading
        self._sync_from_service()
    
    def _sync_from_service(self):
        """Sync attributes from the service layer."""
        # Load data if available
        try:
            self.service.load_data_from_files()
        except Exception as e:
            self._logger.warning(f"Could not load data on initialization: {e}")
        
        # Sync data references (keep cached for performance where needed)
        self.db1_data = self.service.db1_data
        self.db2_data = self.service.db2_data
        # combined_data is always fetched fresh via get_combined_data()
        
        # Sync configuration
        self.mappings = self.service.get_field_mappings()
        self.db1_name = self.service.db1_name
        self.db2_name = self.service.db2_name
        
        # Create linking config for backward compatibility
        if self.service.field_mappings and self.service.field_mappings.primary_link:
            self.linking_config = {
                "primary_link": {
                    "db1": self.service.field_mappings.primary_link.db1,
                    "db2": self.service.field_mappings.primary_link.db2
                }
            }
    
    @property
    def logger(self):
        """Maintain logger compatibility."""
        return self._logger
    
    def load_data(self) -> Tuple[bool, str]:
        """Load data using the service layer."""
        try:
            success = self.service.load_data_from_files()
            self._sync_from_service()
            if success:
                return True, "Data loaded successfully"
            else:
                return False, "Failed to load data"
        except Exception as e:
            self._logger.error(f"Failed to load data: {e}")
            return False, f"Error loading data: {str(e)}"
    
    def load_mappings(self) -> bool:
        """Load mappings configuration."""
        try:
            self._sync_from_service()
            return True
        except Exception as e:
            self._logger.error(f"Failed to load mappings: {e}")
            return False
    
    def save_field_mappings(self) -> bool:
        """Save field mappings."""
        try:
            if self.mappings:
                self.service.update_field_mappings(self.mappings)
            return True
        except Exception as e:
            self._logger.error(f"Failed to save field mappings: {e}")
            return False
    
    def get_field_mappings_list(self) -> List[Dict[str, Any]]:
        """Get field mappings as a list for GUI compatibility."""
        if not self.mappings or 'field_mappings' not in self.mappings:
            return []
        
        mappings_list = []
        for name, mapping in self.mappings['field_mappings'].items():
            mappings_list.append({
                'name': name,
                'netsuite_field': mapping.get('netsuite_field', ''),
                'shopify_field': mapping.get('shopify_field', ''),
                'direction': mapping.get('direction', 'bidirectional'),
                'description': mapping.get('description', '')
            })
        
        return mappings_list
    
    def get_field_mappings_config(self) -> Dict[str, Any]:
        """Get field mappings configuration for GUI compatibility."""
        return self.mappings
    
    def is_primary_link_configured(self) -> bool:
        """Check if primary link is configured."""
        return (self.service.field_mappings is not None and 
                self.service.field_mappings.primary_link is not None)
    
    def get_combined_data(self):
        """Get combined data DataFrame."""
        # Always get the latest data from the service
        return self.service.combined_data
    
    def get_primary_link_field(self) -> Tuple[str, str]:
        """Get primary link fields for Database 1 and Database 2."""
        if self.service.field_mappings and self.service.field_mappings.primary_link:
            return (self.service.field_mappings.primary_link.db1,
                   self.service.field_mappings.primary_link.db2)
        return ("SKU", "Variant SKU")
    
    def update_linking_field(self, ns_field: str, sf_field: str) -> bool:
        """Update primary linking fields."""
        try:
            if 'primary_link' not in self.mappings:
                self.mappings['primary_link'] = {}
            self.mappings['primary_link']['db1'] = ns_field
            self.mappings['primary_link']['db2'] = sf_field
            return self.save_field_mappings()
        except Exception as e:
            self._logger.error(f"Failed to update linking field: {e}")
            return False
    
    def update_database_names(self, db1_name: str, db2_name: str) -> bool:
        """Update database names."""
        try:
            if 'database_names' not in self.mappings:
                self.mappings['database_names'] = {}
            self.mappings['database_names']['db1_name'] = db1_name
            self.mappings['database_names']['db2_name'] = db2_name
            
            # Also update the service layer
            self.service.db1_name = db1_name
            self.service.db2_name = db2_name
            
            return self.save_field_mappings()
        except Exception as e:
            self._logger.error(f"Failed to update database names: {e}")
            return False
    
    def get_available_db1_fields(self) -> List[str]:
        """Get available database 1 fields."""
        if self.db1_data is not None:
            return list(self.db1_data.columns)
        return []
    
    def get_available_db2_fields(self) -> List[str]:
        """Get available database 2 fields."""
        if self.db2_data is not None:
            return list(self.db2_data.columns)
        return []
    
    # Backward compatibility methods (deprecated)
    def get_available_netsuite_fields(self) -> List[str]:
        """Get available database 1 fields (deprecated - use get_available_db1_fields)."""
        return self.get_available_db1_fields()
    
    def get_available_shopify_fields(self) -> List[str]:
        """Get available database 2 fields (deprecated - use get_available_db2_fields)."""
        return self.get_available_db2_fields()
    
    def get_linking_configuration(self) -> Dict[str, Any]:
        """Get linking configuration."""
        return self.linking_config
    
    def get_field_mappings(self) -> Dict[str, Any]:
        """Get field mappings."""
        return self.mappings.get('field_mappings', {})
    
    def configure_data_sources(self, netsuite_file: str, shopify_file: str) -> Tuple[bool, str]:
        """Configure data sources."""
        try:
            # Update the data sources in mappings with new file paths
            if 'data_sources' not in self.mappings:
                self.mappings['data_sources'] = {}
            
            self.mappings['data_sources']['db1'] = {
                "file_path": netsuite_file,
                "file_type": "excel" if netsuite_file.endswith(('.xlsx', '.xls')) else "csv",
                "name": None,
                "description": None
            }
            
            self.mappings['data_sources']['db2'] = {
                "file_path": shopify_file,
                "file_type": "excel" if shopify_file.endswith(('.xlsx', '.xls')) else "csv",
                "name": None,
                "description": None
            }
            
            # Save the updated configuration to JSON file
            save_success = self.save_field_mappings()
            if not save_success:
                return False, "Failed to save configuration"
            
            # Then load the data from the files
            success = self.service.load_data_from_files(netsuite_file, shopify_file)
            self._sync_from_service()
            
            if success:
                return True, "Data sources configured and saved successfully"
            else:
                return False, "Failed to configure data sources"
        except Exception as e:
            self._logger.error(f"Failed to configure data sources: {e}")
            return False, f"Error: {str(e)}"
    
    def get_configured_data_sources(self) -> Tuple[Optional[str], Optional[str]]:
        """Get configured data source paths."""
        if self.service.field_mappings and self.service.field_mappings.data_sources:
            # Check for new format first (db1/db2), then fall back to old format (netsuite/shopify)
            db1_source = self.service.field_mappings.data_sources.get('db1')
            if not db1_source:
                db1_source = self.service.field_mappings.data_sources.get('netsuite')
            
            db2_source = self.service.field_mappings.data_sources.get('db2')
            if not db2_source:
                db2_source = self.service.field_mappings.data_sources.get('shopify')
            
            return (
                db1_source.file_path if db1_source else None,
                db2_source.file_path if db2_source else None
            )
        return None, None
    
    def clear_all_field_mappings(self) -> bool:
        """Clear all field mappings."""
        try:
            if 'field_mappings' in self.mappings:
                self.mappings['field_mappings'] = {}
            return self.save_field_mappings()
        except Exception as e:
            self._logger.error(f"Failed to clear field mappings: {e}")
            return False
    
    def add_field_mapping(self, name: str, netsuite_field: str, shopify_field: str, 
                         direction: str = "bidirectional", description: str = "") -> bool:
        """Add a new field mapping."""
        try:
            if 'field_mappings' not in self.mappings:
                self.mappings['field_mappings'] = {}
            
            self.mappings['field_mappings'][name] = {
                'netsuite_field': netsuite_field,
                'shopify_field': shopify_field,
                'direction': direction,
                'description': description
            }
            
            return self.save_field_mappings()
        except Exception as e:
            self._logger.error(f"Failed to add field mapping: {e}")
            return False
    
    def add_field_mapping(self, netsuite_field: str, shopify_field: str, 
                         description: str = "") -> bool:
        """Add a new field mapping (GUI compatibility version)."""
        try:
            # Generate a name from the fields
            name = f"{netsuite_field}_to_{shopify_field}".replace(" ", "_")
            
            if 'field_mappings' not in self.mappings:
                self.mappings['field_mappings'] = {}
            
            self.mappings['field_mappings'][name] = {
                'netsuite_field': netsuite_field,
                'shopify_field': shopify_field,
                'direction': 'bidirectional',
                'description': description
            }
            
            return self.save_field_mappings()
        except Exception as e:
            self._logger.error(f"Failed to add field mapping: {e}")
            return False
    
    def add_field_mapping_by_name(self, name: str, netsuite_field: str, shopify_field: str, 
                                 direction: str = "bidirectional", description: str = "") -> bool:
        """Add a new field mapping by name."""
        try:
            if 'field_mappings' not in self.mappings:
                self.mappings['field_mappings'] = {}
            
            self.mappings['field_mappings'][name] = {
                'netsuite_field': netsuite_field,
                'shopify_field': shopify_field,
                'direction': direction,
                'description': description
            }
            
            return self.save_field_mappings()
        except Exception as e:
            self._logger.error(f"Failed to add field mapping: {e}")
            return False
    
    def remove_field_mapping(self, netsuite_field: str, shopify_field: str) -> bool:
        """Remove a field mapping by fields (GUI compatibility version)."""
        try:
            if 'field_mappings' not in self.mappings:
                return True
                
            # Find mapping by fields
            to_remove = None
            for name, mapping in self.mappings['field_mappings'].items():
                if (mapping.get('netsuite_field') == netsuite_field and 
                    mapping.get('shopify_field') == shopify_field):
                    to_remove = name
                    break
            
            if to_remove:
                del self.mappings['field_mappings'][to_remove]
                return self.save_field_mappings()
            
            return True
        except Exception as e:
            self._logger.error(f"Failed to remove field mapping: {e}")
            return False
    
    def remove_field_mapping_by_name(self, name: str) -> bool:
        """Remove a field mapping by name."""
        try:
            if 'field_mappings' in self.mappings and name in self.mappings['field_mappings']:
                del self.mappings['field_mappings'][name]
                return self.save_field_mappings()
            return True
        except Exception as e:
            self._logger.error(f"Failed to remove field mapping: {e}")
            return False
    
    def update_field_mapping(self, old_name: str, new_name: str, netsuite_field: str, 
                           shopify_field: str, direction: str = "bidirectional", 
                           description: str = "") -> bool:
        """Update an existing field mapping."""
        try:
            # Remove old mapping if name changed
            if old_name != new_name and old_name in self.mappings.get('field_mappings', {}):
                del self.mappings['field_mappings'][old_name]
            
            # Add/update new mapping
            return self.add_field_mapping(new_name, netsuite_field, shopify_field, direction, description)
        except Exception as e:
            self._logger.error(f"Failed to update field mapping: {e}")
            return False
    
    def get_unmatched_analysis(self) -> Dict[str, Any]:
        """Get unmatched items analysis."""
        try:
            analysis = self.service.get_unmatched_analysis()
            return analysis.dict()
        except Exception as e:
            self._logger.error(f"Failed to get unmatched analysis: {e}")
            return {}
    
    def export_to_excel(self, data_type: str, filename: str = None) -> str:
        """Export data to Excel file."""
        try:
            file_path = self.service.export_data(data_type, "xlsx", filename)
            return file_path
        except Exception as e:
            self._logger.error(f"Failed to export to Excel: {e}")
            return ""
    
    def get_database_names(self) -> Tuple[str, str]:
        """Get database names."""
        return self.db1_name, self.db2_name
    
    def set_database_names(self, db1_name: str, db2_name: str) -> bool:
        """Set custom database names."""
        try:
            if 'database_names' not in self.mappings:
                self.mappings['database_names'] = {}
            
            self.mappings['database_names']['db1_name'] = db1_name
            self.mappings['database_names']['db2_name'] = db2_name
            
            success = self.save_field_mappings()
            if success:
                self._sync_from_service()
            return success
        except Exception as e:
            self._logger.error(f"Failed to set database names: {e}")
            return False
    
    def update_record(self, data_type: str, record_index: int, updates: Dict[str, Any]) -> bool:
        """Update a specific record."""
        try:
            success = self.service.update_record(data_type, record_index, updates)
            if success:
                self._sync_from_service()
            return success
        except Exception as e:
            self._logger.error(f"Failed to update record: {e}")
            return False
    
    def get_record(self, data_type: str, record_index: int) -> Dict[str, Any]:
        """Get a specific record."""
        try:
            if data_type == "netsuite" and self.service.netsuite_data is not None:
                if record_index < len(self.service.netsuite_data):
                    return self.service.netsuite_data.iloc[record_index].to_dict()
            elif data_type == "shopify" and self.service.shopify_data is not None:
                if record_index < len(self.service.shopify_data):
                    return self.service.shopify_data.iloc[record_index].to_dict()
            elif data_type == "combined" and self.service.combined_data is not None:
                if record_index < len(self.service.combined_data):
                    return self.service.combined_data.iloc[record_index].to_dict()
            return {}
        except Exception as e:
            self._logger.error(f"Failed to get record: {e}")
            return {}
    
    def propagate_to_individual_outputs(self):
        """Propagate updates to individual output files."""
        try:
            self.service._save_output_files()
        except Exception as e:
            self._logger.error(f"Failed to propagate to individual outputs: {e}")
    
    # Additional methods that might be used by the GUI
    def ensure_directories(self):
        """Ensure required directories exist."""
        # This is handled by the service layer
        pass
    
    def setup_logging(self):
        """Setup logging - handled by the service layer."""
        pass
    
    def create_minimal_mappings_structure(self) -> Dict[str, Any]:
        """Create minimal mappings structure."""
        return {"field_mappings": {}}
    
    def create_default_mappings_structure(self) -> Dict[str, Any]:
        """Create default mappings structure."""
        return self.service.config_manager._get_default_field_mappings()