"""
Data Service for DBSyncr
Handles all data operations and business logic.
"""
import pandas as pd
import os
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import json
from pathlib import Path

from src.models.data_models import (
    DatabaseRecord, CombinedRecord, UnmatchedAnalysis,
    FieldMappingsConfig, FieldMapping, DataSource
)
from src.utils.exceptions import (
    DataValidationError, FileNotFoundError, DataProcessingError, MappingError
)
from src.utils.logging_config import get_logger
from src.config.settings import config_manager


class DataService:
    """Service class for handling all data operations."""
    
    def __init__(self):
        self.logger = get_logger("DataService")
        self.config_manager = config_manager
        
        # Data storage
        self.db1_data: Optional[pd.DataFrame] = None
        self.db2_data: Optional[pd.DataFrame] = None
        self.combined_data: Optional[pd.DataFrame] = None
        
        # Configuration
        self.field_mappings: Optional[FieldMappingsConfig] = None
        self.db1_name: str = "Database 1"
        self.db2_name: str = "Database 2"
        
        # Initialize
        self._load_configuration()
        self._ensure_directories()
    
    def _load_configuration(self):
        """Load field mappings configuration."""
        try:
            mappings_data = self.config_manager.load_field_mappings()
            self.field_mappings = FieldMappingsConfig(**mappings_data)
            
            # Update database names
            self.db1_name = self.field_mappings.database_names.db1_name
            self.db2_name = self.field_mappings.database_names.db2_name
            
            self.logger.info(f"Loaded configuration with {len(self.field_mappings.field_mappings)} field mappings")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise DataProcessingError(f"Configuration loading failed: {e}")
    
    def _ensure_directories(self):
        """Ensure required directories exist."""
        directories = [
            self.config_manager.settings.data_dir,
            self.config_manager.settings.input_dir,
            self.config_manager.settings.output_dir,
            self.config_manager.settings.exports_dir,
            self.config_manager.settings.backups_dir,
            self.config_manager.settings.logs_dir
        ]
        
        for directory in directories:
            dir_path = self.config_manager.get_absolute_path(directory)
            dir_path.mkdir(exist_ok=True)
    
    def load_data_from_files(self, db1_file: str = None, db2_file: str = None) -> bool:
        """Load data from Excel or CSV files."""
        try:
            # Use configured file paths if not provided
            if not db1_file and self.field_mappings:
                db1_file = self.field_mappings.data_sources.get("db1", {}).file_path
            if not db2_file and self.field_mappings:
                db2_file = self.field_mappings.data_sources.get("db2", {}).file_path
            
            # Load Database 1 data
            if db1_file and os.path.exists(db1_file):
                self.db1_data = self._load_file(db1_file)
                self.logger.info(f"Loaded {self.db1_name} data: {len(self.db1_data)} records")
            else:
                self.logger.warning(f"{self.db1_name} file not found: {db1_file}")
            
            # Load Database 2 data
            if db2_file and os.path.exists(db2_file):
                self.db2_data = self._load_file(db2_file)
                self.logger.info(f"Loaded {self.db2_name} data: {len(self.db2_data)} records")
            else:
                self.logger.warning(f"{self.db2_name} file not found: {db2_file}")
            
            # Combine data if both are loaded
            if self.db1_data is not None and self.db2_data is not None:
                self._combine_data()
                self._save_output_files()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load data: {e}")
            raise DataProcessingError(f"Data loading failed: {e}")
    
    def _load_file(self, file_path: str) -> pd.DataFrame:
        """Load data from a single file (Excel or CSV)."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            if file_path.suffix.lower() in ['.xlsx', '.xls']:
                return pd.read_excel(file_path)
            elif file_path.suffix.lower() == '.csv':
                return pd.read_csv(file_path)
            else:
                raise DataValidationError(f"Unsupported file format: {file_path.suffix}")
                
        except Exception as e:
            raise DataProcessingError(f"Failed to load file {file_path}: {e}")
    
    def _combine_data(self):
        """Combine database data based on linking configuration."""
        if not self.field_mappings:
            raise MappingError("Field mappings not loaded")
        
        try:
            # Get linking fields
            db1_key = self.field_mappings.primary_link.db1
            db2_key = self.field_mappings.primary_link.db2
            
            # Normalize keys for matching
            db1_data = self.db1_data.copy()
            db2_data = self.db2_data.copy()
            
            # Create normalized keys for matching - handle float vs int issue
            def normalize_key(value):
                """Normalize a key for consistent matching."""
                if pd.isna(value):
                    return ''
                str_value = str(value).strip().upper()
                # Remove trailing .0 from float values to match integers
                if str_value.endswith('.0'):
                    str_value = str_value[:-2]
                return str_value
            
            db1_data['NormalizedKey'] = db1_data[db1_key].apply(normalize_key)
            db2_data['NormalizedKey'] = db2_data[db2_key].apply(normalize_key)
            
            # Remove duplicates based on NormalizedKey (keep first occurrence)
            db1_initial_count = len(db1_data)
            db2_initial_count = len(db2_data)
            
            db1_data = db1_data.drop_duplicates(subset=['NormalizedKey'], keep='first')
            db2_data = db2_data.drop_duplicates(subset=['NormalizedKey'], keep='first')
            
            if len(db1_data) != db1_initial_count:
                self.logger.warning(f"{self.db1_name}: Removed {db1_initial_count - len(db1_data)} duplicate keys")
            if len(db2_data) != db2_initial_count:
                self.logger.warning(f"{self.db2_name}: Removed {db2_initial_count - len(db2_data)} duplicate keys")
            
            # Add database prefixes to columns (including renaming the key fields)
            db1_cols = {col: f"{self.db1_name}_{col}" for col in db1_data.columns if col not in ['NormalizedKey', db1_key]}
            db1_cols[db1_key] = f"{self.db1_name}_Key"
            db1_data = db1_data.rename(columns=db1_cols)
            
            db2_cols = {col: f"{self.db2_name}_{col}" for col in db2_data.columns if col not in ['NormalizedKey', db2_key]}
            db2_cols[db2_key] = f"{self.db2_name}_Key"
            db2_data = db2_data.rename(columns=db2_cols)
            
            # Perform outer join on the common NormalizedKey
            self.combined_data = pd.merge(
                db1_data, db2_data,
                on='NormalizedKey',
                how='outer'
            )
            
            self.logger.info(f"Combined data created: {len(self.combined_data)} records")
            
        except Exception as e:
            self.logger.error(f"Failed to combine data: {e}")
            raise DataProcessingError(f"Data combination failed: {e}")
    
    def _save_output_files(self):
        """Save processed data to output files."""
        output_dir = self.config_manager.get_absolute_path(self.config_manager.settings.output_dir)
        
        try:
            # Save individual datasets
            if self.db1_data is not None:
                db1_path = output_dir / f"{self.db1_name}Data.csv"
                self.db1_data.to_csv(db1_path, index=False)
            
            if self.db2_data is not None:
                db2_path = output_dir / f"{self.db2_name}Data.csv"
                self.db2_data.to_csv(db2_path, index=False)
            
            # Save combined data
            if self.combined_data is not None:
                combined_path = output_dir / "CombinedData.csv"
                self.combined_data.to_csv(combined_path, index=False)
                
                # Save timestamped version (disabled for debug cleanup)
                # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # timestamped_path = output_dir / f"combined_{timestamp}.csv"
                # self.combined_data.to_csv(timestamped_path, index=False)
            
            self.logger.info("Output files saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save output files: {e}")
            raise DataProcessingError(f"Output file saving failed: {e}")
    
    def get_unmatched_analysis(self) -> UnmatchedAnalysis:
        """Analyze unmatched items between databases."""
        if self.db1_data is None or self.db2_data is None:
            raise DataProcessingError("Both database datasets must be loaded")
        
        try:
            # Get linking fields
            db1_key = self.field_mappings.primary_link.db1
            db2_key = self.field_mappings.primary_link.db2
            
            # Get key sets
            db1_keys = set(
                self.db1_data[db1_key].dropna().astype(str).str.strip().str.upper()
            )
            db2_keys = set(
                self.db2_data[db2_key].dropna().astype(str).str.strip().str.upper()
            )
            
            # Calculate matches
            matched_keys = db1_keys.intersection(db2_keys)
            db1_only = db1_keys - db2_keys
            db2_only = db2_keys - db1_keys
            
            # Calculate match rate
            total_unique_keys = len(db1_keys.union(db2_keys))
            match_rate = len(matched_keys) / total_unique_keys * 100 if total_unique_keys > 0 else 0
            
            return UnmatchedAnalysis(
                total_db1_items=len(db1_keys),
                total_db2_items=len(db2_keys),
                matched_items=len(matched_keys),
                db1_only_items=len(db1_only),
                db2_only_items=len(db2_only),
                match_rate=match_rate,
                db1_only_keys=sorted(list(db1_only)),
                db2_only_keys=sorted(list(db2_only)),
                analysis_timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to analyze unmatched items: {e}")
            raise DataProcessingError(f"Unmatched analysis failed: {e}")
    
    def update_field_mappings(self, mappings: Dict[str, Any]) -> bool:
        """Update field mappings configuration."""
        try:
            # Validate and create new config
            new_config = FieldMappingsConfig(**mappings)
            self.field_mappings = new_config
            
            # Save to file
            self.config_manager.save_field_mappings(mappings)
            
            # Update database names
            self.db1_name = self.field_mappings.database_names.db1_name
            self.db2_name = self.field_mappings.database_names.db2_name
            
            self.logger.info("Field mappings updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update field mappings: {e}")
            raise MappingError(f"Field mappings update failed: {e}")
    
    def get_field_mappings(self) -> Dict[str, Any]:
        """Get current field mappings configuration."""
        if not self.field_mappings:
            return {}
        return self.field_mappings.dict()
    
    def export_data(self, data_type: str, format: str = "csv", file_path: str = None) -> str:
        """Export data to file."""
        try:
            # Select data to export
            if data_type == "netsuite":
                data = self.netsuite_data
                default_name = f"{self.db1_name}Data"
            elif data_type == "shopify":
                data = self.shopify_data
                default_name = f"{self.db2_name}Data"
            elif data_type == "combined":
                data = self.combined_data
                default_name = "CombinedData"
            else:
                raise DataValidationError(f"Invalid data type: {data_type}")
            
            if data is None:
                raise DataProcessingError(f"No {data_type} data available for export")
            
            # Generate file path if not provided
            if not file_path:
                exports_dir = self.config_manager.get_absolute_path(self.config_manager.settings.exports_dir)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = exports_dir / f"{default_name}_{timestamp}.{format}"
            
            # Export based on format
            if format.lower() == "csv":
                data.to_csv(file_path, index=False)
            elif format.lower() in ["xlsx", "excel"]:
                data.to_excel(file_path, index=False)
            else:
                raise DataValidationError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Data exported to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to export data: {e}")
            raise DataProcessingError(f"Data export failed: {e}")
    
    def update_record(self, data_type: str, record_index: int, updates: Dict[str, Any]) -> bool:
        """Update a specific record."""
        try:
            # Select data to update
            if data_type == "netsuite":
                data = self.netsuite_data
            elif data_type == "shopify":
                data = self.shopify_data
            elif data_type == "combined":
                data = self.combined_data
            else:
                raise DataValidationError(f"Invalid data type: {data_type}")
            
            if data is None:
                raise DataProcessingError(f"No {data_type} data available")
            
            if record_index >= len(data):
                raise DataValidationError(f"Invalid record index: {record_index}")
            
            # Apply updates
            for column, value in updates.items():
                if column in data.columns:
                    data.iloc[record_index, data.columns.get_loc(column)] = value
            
            # Re-save output files
            self._save_output_files()
            
            self.logger.info(f"Record {record_index} updated in {data_type} data")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update record: {e}")
            raise DataProcessingError(f"Record update failed: {e}")
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all loaded data."""
        summary = {
            "netsuite": {
                "loaded": self.netsuite_data is not None,
                "records": len(self.netsuite_data) if self.netsuite_data is not None else 0,
                "columns": list(self.netsuite_data.columns) if self.netsuite_data is not None else []
            },
            "shopify": {
                "loaded": self.shopify_data is not None,
                "records": len(self.shopify_data) if self.shopify_data is not None else 0,
                "columns": list(self.shopify_data.columns) if self.shopify_data is not None else []
            },
            "combined": {
                "loaded": self.combined_data is not None,
                "records": len(self.combined_data) if self.combined_data is not None else 0,
                "columns": list(self.combined_data.columns) if self.combined_data is not None else []
            },
            "configuration": {
                "db1_name": self.db1_name,
                "db2_name": self.db2_name,
                "field_mappings_count": len(self.field_mappings.field_mappings) if self.field_mappings else 0
            }
        }
        
        return summary