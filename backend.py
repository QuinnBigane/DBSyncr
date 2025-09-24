"""
DBSyncr Backend
Backend class with dynamic linking fields and  mapping support.
"""
import pandas as pd
import os
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from data_converter import DataConverter


class UPSDataBackend:
    def propagate_to_individual_outputs(self):
        """Push updates from combined database to individual output CSVs."""
        output_dir = "output_data"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # Extract NetSuite and Shopify data from combined
        if self.combined_data is not None:
            # NetSuite
            ns_key = f'{self.db1_name}_Key'
            ns_cols = [col for col in self.combined_data.columns if col.startswith(f'{self.db1_name}_')]
            ns_df = self.combined_data[ns_cols].copy()
            # Remove DB prefix from columns and NormalizedKey
            ns_df = ns_df.rename(columns=lambda c: c.replace(f'{self.db1_name}_', '') if c != ns_key else 'SKU')
            ns_path = os.path.join(output_dir, f"{self.db1_name}Data.csv")
            ns_df.to_csv(ns_path, index=False)
            # Shopify
            sf_key = f'{self.db2_name}_Key'
            sf_cols = [col for col in self.combined_data.columns if col.startswith(f'{self.db2_name}_')]
            sf_df = self.combined_data[sf_cols].copy()
            # Remove DB prefix from columns and NormalizedKey
            sf_df = sf_df.rename(columns=lambda c: c.replace(f'{self.db2_name}_', '') if c != sf_key else 'Variant SKU')
            sf_path = os.path.join(output_dir, f"{self.db2_name}Data.csv")
            sf_df.to_csv(sf_path, index=False)
    """Backend class with dynamic linking and improved data operations."""
    
    def __init__(self, mappings_file: str = "field_mappings.json"):
        self.netsuite_data: Optional[pd.DataFrame] = None
        self.shopify_data: Optional[pd.DataFrame] = None
        self.mappings: Dict[str, Any] = {}
        self.combined_data: Optional[pd.DataFrame] = None
        self.linking_config: Dict[str, Any] = {}
        
        # Custom database names (will be set after loading mappings)
        self.db1_name: str = "DB1"
        self.db2_name: str = "DB2"
        
        # Set mappings file
        self.mappings_file = mappings_file
        
        # Setup logging
        self.setup_logging()
        self.logger.info("UPS Data Backend initialized")
        
        # Create necessary directories
        self.ensure_directories()
        
        # Load mappings
        self.load_mappings()
        
        # Initialize data converter
        self.data_converter = DataConverter(self.mappings_file)

        # Load input data ONCE at startup
        self.input_loaded = False
        self.load_input_data_once()

        # Initialize output data at startup
        self.init_output_data()
    def load_input_data_once(self):
        """Load input data only once at startup."""
        if self.input_loaded:
            return
        self.input_loaded = True
        self.load_data()  # This loads and merges input data

    def init_output_data(self):
        """Initialize output data CSVs at startup based on input data."""
        output_dir = "output_data"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        # Save NetSuite and Shopify as CSVs in output_data
        if self.netsuite_data is not None:
            netsuite_path = os.path.join(output_dir, "NetSuiteData.csv")
            self.netsuite_data.to_csv(netsuite_path, index=False)
        if self.shopify_data is not None:
            shopify_path = os.path.join(output_dir, "ShopifyData.csv")
            self.shopify_data.to_csv(shopify_path, index=False)
        # Save combined data as CSV in output_data
        if self.combined_data is not None:
            combined_path = os.path.join(output_dir, "CombinedData.csv")
            self.combined_data.to_csv(combined_path, index=False)
    
    def setup_logging(self):
        """Setup logging configuration."""
        if not os.path.exists("logs"):
            os.makedirs("logs")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"logs/ups_data_manager_{datetime.now().strftime('%Y%m%d')}.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("UPSDataBackend")
    
    def ensure_directories(self):
        """Ensure required directories exist."""
        directories = ["backups", "exports", "logs", "data"]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                self.logger.info(f"Created directory: {directory}")
    
    def load_mappings(self) -> bool:
        """Load  field mappings configuration."""
        try:
            if os.path.exists(self.mappings_file):
                with open(self.mappings_file, 'r') as f:
                    content = f.read().strip()
                    
                if content:
                    # File has content, try to parse it
                    self.mappings = json.loads(content)
                else:
                    # File is empty, create minimal structure
                    self.logger.info("Field mappings file is empty, creating minimal structure")
                    self.mappings = self.create_minimal_mappings_structure()
                    self.save_field_mappings()  # Save the minimal structure
            else:
                # File doesn't exist, create it with minimal structure
                self.logger.info("Field mappings file not found, creating with minimal structure")
                self.mappings = self.create_minimal_mappings_structure()
                self.save_field_mappings()  # Save the minimal structure
            
            # Extract linking configuration
            self.linking_config = self.mappings.get("linking_configuration", {})                
            self.logger.info(f"Loaded mappings with {len(self.mappings.get('field_mappings', {}))} field mappings")
            
            # Load custom database names
            self.db1_name = self.mappings.get("database_names", {}).get("db1_name", "DB1")
            self.db2_name = self.mappings.get("database_names", {}).get("db2_name", "DB2")
            self.logger.info(f"Using database names: {self.db1_name}, {self.db2_name}")
            
            return True
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in mappings file: {e}")
            self.logger.info("Creating minimal mappings structure due to JSON error")
            self.mappings = self.create_minimal_mappings_structure()
            self.save_field_mappings()  # Save the minimal structure
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load mappings: {e}")
            # Create minimal structure to prevent crashes
            self.mappings = self.create_minimal_mappings_structure()
            return True
    
    def get_database_names(self) -> Tuple[str, str]:
        """Get the custom database names or defaults."""
        return self.db1_name, self.db2_name
    
    def create_minimal_mappings_structure(self) -> Dict[str, Any]:
        """Create a minimal mappings structure when file is missing or corrupt."""
        return {
            "field_mappings": {}
        }

    def create_default_mappings_structure(self) -> Dict[str, Any]:
        """Create a default mappings structure when file is missing or corrupt."""
        return {
            "linking_configuration": {
                "primary_link_field": {
                    "field_name": "sku",
                    "netsuite_field": "SKU",
                    "shopify_field": "Variant SKU",
                    "description": "Primary linking field - SKU used to match records between systems",
                    "required": True
                },
                "secondary_link_fields": []
            },
            "field_mappings": {},
            "sync_settings": {
                "auto_sync_on_load": False,
                "confirm_before_sync": True,
                "backup_before_changes": True,
                "log_sync_operations": True,
                "use_primary_link_only": False,
                "fallback_to_secondary_links": True
            },
            "field_validation": {
                "weight": {
                    "type": "numeric",
                    "min_value": 0,
                    "max_value": 10000,
                    "required": False
                },
                "cost": {
                    "type": "numeric",
                    "min_value": 0,
                    "max_value": 100000,
                    "required": False
                },
                "price": {
                    "type": "numeric",
                    "min_value": 0,
                    "max_value": 100000,
                    "required": False
                },
                "title": {
                    "type": "text",
                    "max_length": 255,
                    "required": False
                }
            },
            "data_sources": {
                "netsuite": {
                    "file_path": "netsuite all items 9-22-2025.xls.xlsx",
                    "file_type": "excel",
                    "csv_export_path": "data/NetSuiteData.csv"
                },
                "shopify": {
                    "file_path": "Shopify_ALL_Export_2025-09-22_030043.xlsx",
                    "file_type": "excel",
                    "csv_export_path": "data/ShopifyData.csv"
                }
            },
            "primary_link": {
                "netsuite": "",
                "shopify": ""
            }
        }
    
    def is_primary_link_configured(self) -> bool:
        """Check if primary link field is properly configured."""
        # Check new linking_configuration format first
        linking_config = self.mappings.get("linking_configuration", {})
        primary_link = linking_config.get("primary_link_field", {})
        
        netsuite_field = primary_link.get("netsuite_field", "")
        shopify_field = primary_link.get("shopify_field", "")
        
        if netsuite_field and shopify_field:
            return True
        
        # Check legacy/simple primary_link format
        simple_primary_link = self.mappings.get("primary_link", {})
        netsuite_simple = simple_primary_link.get("netsuite", "")
        shopify_simple = simple_primary_link.get("shopify", "")
        
        return bool(netsuite_simple and shopify_simple)
    
    def get_primary_link_field(self) -> Tuple[str, str]:
        """Get the primary linking field names for both systems."""
        # Try new linking_configuration format first
        primary_link = self.linking_config.get("primary_link_field", {})
        netsuite_field = primary_link.get("netsuite_field", "")
        shopify_field = primary_link.get("shopify_field", "")
        
        if netsuite_field and shopify_field:
            return netsuite_field, shopify_field
        
        # Fallback to simple primary_link format
        simple_primary_link = self.mappings.get("primary_link", {})
        netsuite_simple = simple_primary_link.get("netsuite", "SKU")
        shopify_simple = simple_primary_link.get("shopify", "Variant SKU")
        
        return netsuite_simple, shopify_simple
    
    def get_secondary_link_fields(self) -> List[Tuple[str, str]]:
        """Get secondary linking field pairs."""
        secondary_links = self.linking_config.get("secondary_link_fields", [])
        return [(link.get("netsuite_field"), link.get("shopify_field")) 
                for link in secondary_links 
                if link.get("netsuite_field") and link.get("shopify_field")]
    
    def ensure_data_files_exist(self) -> Tuple[bool, str]:
        """Check if data files are configured and exist."""
        # Check if files are configured in the  mappings
        data_sources = self.mappings.get("data_sources", {})
        netsuite_config = data_sources.get("netsuite", {})
        shopify_config = data_sources.get("shopify", {})
        
        netsuite_file = netsuite_config.get("file_path", "")
        shopify_file = shopify_config.get("file_path", "")
        
        # If no files configured, return false
        if not netsuite_file or not shopify_file:
            return False, "Data source files not configured. Please configure files in Field Mappings."
        
        # Check if configured files exist
        missing_files = []
        if not os.path.exists(netsuite_file):
            missing_files.append(f"NetSuite file: {netsuite_file}")
        if not os.path.exists(shopify_file):
            missing_files.append(f"Shopify file: {shopify_file}")
        
        if missing_files:
            return False, f"Configured files not found: {', '.join(missing_files)}"
        
        # Update instance file paths
        self.netsuite_file = netsuite_file
        self.shopify_file = shopify_file
        
        self.logger.info(f"Using configured files - NetSuite: {netsuite_file}, Shopify: {shopify_file}")
        return True, "Data source files configured and available"
    
    def configure_data_sources(self, netsuite_file: str, shopify_file: str) -> Tuple[bool, str]:
        """Configure data source file paths."""
        try:
            # Ensure the mappings has data_sources section
            if "data_sources" not in self.mappings:
                self.mappings["data_sources"] = {}
            
            # Update file paths
            self.mappings["data_sources"]["netsuite"] = {
                "file_path": netsuite_file,
                "file_type": "excel" if netsuite_file.endswith(('.xlsx', '.xls')) else "csv"
            }
            
            self.mappings["data_sources"]["shopify"] = {
                "file_path": shopify_file,
                "file_type": "excel" if shopify_file.endswith(('.xlsx', '.xls')) else "csv"
            }
            
            # Save the configuration
            success = self.save_field_mappings()
            if success:
                self.logger.info(f"Data sources configured - NetSuite: {netsuite_file}, Shopify: {shopify_file}")
                return True, "Data sources configured successfully"
            else:
                return False, "Failed to save configuration"
                
        except Exception as e:
            self.logger.error(f"Error configuring data sources: {e}")
            return False, f"Error configuring data sources: {e}"
    
    def get_configured_data_sources(self) -> Tuple[str, str]:
        """Get the currently configured data source file paths."""
        data_sources = self.mappings.get("data_sources", {})
        netsuite_file = data_sources.get("netsuite", {}).get("file_path", "")
        shopify_file = data_sources.get("shopify", {}).get("file_path", "")
        return netsuite_file, shopify_file

    def load_data(self) -> Tuple[bool, str]:
        """Load all data files with  mapping support."""
        try:
            success_messages = []
            
            # Load  mappings first
            if not self.load_mappings():
                return False, "Failed to load  field mappings"
            
            # Ensure data files exist
            files_ready, files_message = self.ensure_data_files_exist()
            if not files_ready:
                return False, files_message
            
            # Load NetSuite data
            if os.path.exists(self.netsuite_file):
                if self.netsuite_file.endswith(('.xlsx', '.xls')):
                    self.netsuite_data = pd.read_excel(self.netsuite_file)
                else:
                    self.netsuite_data = pd.read_csv(self.netsuite_file)
                
                # Convert numeric columns properly
                self.netsuite_data = self.clean_numeric_data(self.netsuite_data, 'netsuite')
                success_messages.append(f"NetSuite: {len(self.netsuite_data)} records")
                self.logger.info(f"NetSuite columns ({len(self.netsuite_data.columns)}): {list(self.netsuite_data.columns)}")
            
            # Load Shopify data
            if os.path.exists(self.shopify_file):
                if self.shopify_file.endswith(('.xlsx', '.xls')):
                    self.shopify_data = pd.read_excel(self.shopify_file)
                else:
                    self.shopify_data = pd.read_csv(self.shopify_file)
                
                # Convert numeric columns properly
                self.shopify_data = self.clean_numeric_data(self.shopify_data, 'shopify')
                success_messages.append(f"Shopify: {len(self.shopify_data)} records")
                self.logger.info(f"Shopify columns ({len(self.shopify_data.columns)}): {list(self.shopify_data.columns)}")
            
            if self.netsuite_data is None and self.shopify_data is None:
                return False, "No data files found or loaded successfully."
            
            # Create combined data with  linking
            self.create__combined_data()
            
            message = "Data loaded successfully! " + ", ".join(success_messages)
            self.logger.info(message)
            return True, message
            
        except Exception as e:
            error_msg = f"Failed to load data: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def clean_numeric_data(self, df: pd.DataFrame, system: str) -> pd.DataFrame:
        """Clean and convert numeric data properly."""
        df_cleaned = df.copy()
        
        # Get numeric field mappings for this system
        field_mappings = self.mappings.get("field_mappings", {})
        
        for mapping_name, mapping_config in field_mappings.items():
            data_type = mapping_config.get("data_type", "text")
            if data_type == "numeric":
                field_name = mapping_config.get(f"{system}_field")
                if field_name and field_name in df_cleaned.columns:
                    # Convert to numeric, replacing errors with NaN
                    df_cleaned[field_name] = pd.to_numeric(df_cleaned[field_name], errors='coerce')
        
        return df_cleaned
    
    def clean_primary_link_formatting(self, sku_series: pd.Series) -> pd.Series:
        """Clean numeric formatting from primary link fields to prevent mismatches."""
        def clean_sku_value(value):
            if pd.isna(value) or value == '' or str(value).lower() in ['nan', 'none']:
                return value
            
            value_str = str(value)
            
            # If it's a number with .0 suffix, remove it
            if value_str.endswith('.0'):
                # Check if the part before .0 is all digits
                base_part = value_str[:-2]
                if base_part.isdigit() or (base_part.startswith('-') and base_part[1:].isdigit()):
                    return base_part
            
            return value_str
        
        return sku_series.apply(clean_sku_value)
    
    def create__combined_data(self):
        """Create a single merged database with normalized structure using vectorized operations."""
        try:
            self.logger.info("Creating merged database with normalized structure...")
            if self.netsuite_data is None and self.shopify_data is None:
                self.combined_data = pd.DataFrame()
                return
            # Prepare NetSuite data
            ns_df = None
            ns_primary, sf_primary = self.get_primary_link_field()
            if self.netsuite_data is not None and ns_primary in self.netsuite_data.columns:
                ns_df = self.netsuite_data.copy()
                ns_df['NormalizedKey'] = ns_df[ns_primary].astype(str).apply(self.normalize_key)
                ns_df = ns_df[ns_df['NormalizedKey'].notna()]
                ns_df = ns_df.drop_duplicates(subset=['NormalizedKey'], keep='first')
                column_mapping = {}
                for col in ns_df.columns:
                    if col not in ['NormalizedKey', ns_primary]:
                        column_mapping[col] = f'{self.db1_name}_{col}'
                ns_df = ns_df.rename(columns=column_mapping)
                ns_df = ns_df.rename(columns={ns_primary: f'{self.db1_name}_Key'})
            # Prepare Shopify data
            sf_df = None
            if self.shopify_data is not None and sf_primary in self.shopify_data.columns:
                sf_df = self.shopify_data.copy()
                sf_df['NormalizedKey'] = sf_df[sf_primary].astype(str).apply(self.normalize_key)
                sf_df = sf_df[sf_df['NormalizedKey'].notna()]
                sf_df = sf_df.drop_duplicates(subset=['NormalizedKey'], keep='first')
                column_mapping = {}
                for col in sf_df.columns:
                    if col not in ['NormalizedKey', sf_primary]:
                        column_mapping[col] = f'{self.db2_name}_{col}'
                sf_df = sf_df.rename(columns=column_mapping)
                sf_df = sf_df.rename(columns={sf_primary: f'{self.db2_name}_Key'})
            # Merge
            if ns_df is not None and sf_df is not None:
                self.combined_data = pd.merge(ns_df, sf_df, on='NormalizedKey', how='outer')
            elif ns_df is not None:
                self.combined_data = ns_df.copy()
                self.combined_data[f'{self.db2_name}_Key'] = None
            elif sf_df is not None:
                self.combined_data = sf_df.copy()
                self.combined_data[f'{self.db1_name}_Key'] = None
            else:
                self.combined_data = pd.DataFrame()
                return
            # Ensure proper column ordering
            if not self.combined_data.empty:
                key_columns = ['NormalizedKey', f'{self.db1_name}_Key', f'{self.db2_name}_Key']
                db1_columns = [col for col in self.combined_data.columns if col.startswith(f'{self.db1_name}_') and col != f'{self.db1_name}_Key']
                db2_columns = [col for col in self.combined_data.columns if col.startswith(f'{self.db2_name}_') and col != f'{self.db2_name}_Key']
                column_order = key_columns + sorted(db1_columns) + sorted(db2_columns)
                column_order = [col for col in column_order if col in self.combined_data.columns]
                self.combined_data = self.combined_data[column_order]
            self.logger.info(f"Created merged database with {len(self.combined_data)} records and {len(self.combined_data.columns)} columns")
            # After creating combined_data, propagate to individual outputs
            self.propagate_to_individual_outputs()
            
            # Log statistics
            if not self.combined_data.empty:
                db1_key_col = f'{self.db1_name}_Key'
                db2_key_col = f'{self.db2_name}_Key'
                
                matched_count = len(self.combined_data[
                    self.combined_data[db1_key_col].notna() & self.combined_data[db2_key_col].notna()
                ])
                db1_only_count = len(self.combined_data[
                    self.combined_data[db1_key_col].notna() & self.combined_data[db2_key_col].isna()
                ])
                db2_only_count = len(self.combined_data[
                    self.combined_data[db1_key_col].isna() & self.combined_data[db2_key_col].notna()
                ])
                
                self.logger.info(f"Merge statistics: {matched_count} matched, {db1_only_count} {self.db1_name}-only, {db2_only_count} {self.db2_name}-only")
            
        except Exception as e:
            self.logger.error(f"Failed to create merged database: {e}")
            import traceback
            traceback.print_exc()
            self.combined_data = pd.DataFrame()
    
    def normalize_key(self, key):
        """Normalize a key for consistent matching."""
        if pd.isna(key) or key in ['', 'nan', 'None']:
            return None
        
        # Convert to string and strip whitespace
        normalized = str(key).strip()
        
        # Remove .0 suffix from numeric strings
        if normalized.endswith('.0') and normalized[:-2].replace('.', '').replace('-', '').isdigit():
            normalized = normalized[:-2]
        
        return normalized if normalized else None
    
    def find_record_by_linking(self, df: pd.DataFrame, link_value: str, system: str) -> Optional[pd.Series]:
        """Find a record using primary and secondary linking fields."""
        if df is None:
            return None
        
        # Try primary linking field first
        ns_primary, sf_primary = self.get_primary_link_field()
        primary_field = ns_primary if system == 'netsuite' else sf_primary
        
        if primary_field in df.columns:
            # Apply SKU normalization for consistent matching
            normalized_df = df.copy()
            normalized_df[primary_field] = normalized_df[primary_field].astype(str).str.replace(r'\.0$', '', regex=True)
            
            mask = normalized_df[primary_field].astype(str) == str(link_value)
            
            if mask.any():
                # Return the original record (not normalized)
                original_index = normalized_df[mask].index[0]
                return df.loc[original_index]
        
        # Try secondary linking fields if primary didn't work
        use_secondary = self.mappings.get("sync_settings", {}).get("fallback_to_secondary_links", True)
        if use_secondary:
            secondary_links = self.get_secondary_link_fields()
            for ns_field, sf_field in secondary_links:
                field = ns_field if system == 'netsuite' else sf_field
                if field and field in df.columns:
                    mask = df[field].astype(str) == str(link_value)
                    if mask.any():
                        return df[mask].iloc[0]
        
        return None
    
    def get_all_link_values(self) -> List[str]:
        """Get all linking values from both systems."""
        all_values = set()
        
        # Primary linking fields
        ns_primary, sf_primary = self.get_primary_link_field()
        
        if self.netsuite_data is not None and ns_primary in self.netsuite_data.columns:
            all_values.update(self.netsuite_data[ns_primary].dropna().astype(str))
        
        if self.shopify_data is not None and sf_primary in self.shopify_data.columns:
            all_values.update(self.shopify_data[sf_primary].dropna().astype(str))
        
        return sorted(all_values, key=lambda x: int(float(x)) if x.replace('.', '').isdigit() else float('inf'))
    
    def get_link_value_data(self, link_value: str) -> Dict[str, Any]:
        """Get comprehensive data for a specific linking value."""
        result = {
            'link_value': link_value, 
            'netsuite_data': {}, 
            'shopify_data': {},
            'mapped_fields': {}
        }
        
        # Get NetSuite data
        ns_record = self.find_record_by_linking(self.netsuite_data, link_value, 'netsuite')
        if ns_record is not None:
            result['netsuite_data'] = ns_record.to_dict()
        
        # Get Shopify data
        sf_record = self.find_record_by_linking(self.shopify_data, link_value, 'shopify')
        if sf_record is not None:
            result['shopify_data'] = sf_record.to_dict()
        
        # Get mapped field values
        field_mappings = self.mappings.get("field_mappings", {})
        for field_name, mapping in field_mappings.items():
            ns_field = mapping.get("netsuite_field")
            sf_field = mapping.get("shopify_field")
            
            mapped_data = {"field_name": field_name}
            if ns_field and ns_record is not None and ns_field in ns_record:
                mapped_data["netsuite_value"] = ns_record[ns_field]
            if sf_field and sf_record is not None and sf_field in sf_record:
                mapped_data["shopify_value"] = sf_record[sf_field]
            
            result['mapped_fields'][field_name] = mapped_data
        
        return result
    
    def get_combined_data(self) -> Optional[pd.DataFrame]:
        """Get the combined data DataFrame."""
        return self.combined_data
    
    def get_field_mappings_config(self) -> Dict[str, Any]:
        """Get the complete field mappings configuration."""
        return self.mappings
    
    def update_record(self, link_value: str, field: str, value: Any, system: str = 'both') -> Tuple[bool, str]:
        """Update a field for a specific linking value in the specified system(s)."""
        try:
            success_messages = []
            
            # Get the actual field names from mappings
            field_mappings = self.mappings.get("field_mappings", {})
            mapping = field_mappings.get(field)
            
            if not mapping:
                return False, f"Field mapping '{field}' not found in configuration"
            
            ns_field = mapping.get("netsuite_field")
            sf_field = mapping.get("shopify_field")
            
            if system in ['both', 'netsuite'] and self.netsuite_data is not None and ns_field:
                ns_record = self.find_record_by_linking(self.netsuite_data, link_value, 'netsuite')
                if ns_record is not None:
                    # Find the index and update using normalized matching
                    ns_primary, _ = self.get_primary_link_field()
                    # Apply same normalization used in find_record_by_linking
                    normalized_sku = self.netsuite_data[ns_primary].astype(str).str.replace(r'\.0$', '', regex=True)
                    mask = normalized_sku == str(link_value)
                    
                    if mask.any() and ns_field in self.netsuite_data.columns:
                        self.netsuite_data.loc[mask, ns_field] = value
                        success_messages.append("NetSuite")
            
            if system in ['both', 'shopify'] and self.shopify_data is not None and sf_field:
                sf_record = self.find_record_by_linking(self.shopify_data, link_value, 'shopify')
                if sf_record is not None:
                    # Find the index and update using normalized matching
                    _, sf_primary = self.get_primary_link_field()
                    # Apply same normalization used in find_record_by_linking
                    normalized_sku = self.shopify_data[sf_primary].astype(str).str.replace(r'\.0$', '', regex=True)
                    mask = normalized_sku == str(link_value)
                    
                    if mask.any() and sf_field in self.shopify_data.columns:
                        self.shopify_data.loc[mask, sf_field] = value
                        success_messages.append("Shopify")
            
            if success_messages:
                # Recreate combined data
                self.create__combined_data()
                message = f"Updated {field} for {link_value} in {', '.join(success_messages)}"
                self.logger.info(message)
                return True, message
            else:
                return False, f"Record with linking value {link_value} not found or field {field} doesn't exist"
                
        except Exception as e:
            error_msg = f"Failed to update record: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def save_data(self) -> Tuple[bool, str]:
        """Save updated data back to CSV files."""
        try:
            success_messages = []

            # Save input data to input_data folder
            input_dir = "input_data"
            if not os.path.exists(input_dir):
                os.makedirs(input_dir)

            if self.netsuite_data is not None:
                netsuite_path = os.path.join(input_dir, os.path.basename(self.netsuite_file).replace('.xlsx', '.csv'))
                self.netsuite_data.to_csv(netsuite_path, index=False)
                success_messages.append(f"NetSuite ({len(self.netsuite_data)} records)")

            if self.shopify_data is not None:
                shopify_path = os.path.join(input_dir, os.path.basename(self.shopify_file).replace('.xlsx', '.csv'))
                self.shopify_data.to_csv(shopify_path, index=False)
                success_messages.append(f"Shopify ({len(self.shopify_data)} records)")

            # Save combined output data to output_data folder as CSV
            output_dir = "output_data"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            combined = self.get_combined_data()
            if combined is not None:
                # Disabled timestamped debug output
                # timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                # output_path = os.path.join(output_dir, f"ups_combined_{timestamp}.csv")
                # combined.to_csv(output_path, index=False)
                # success_messages.append(f"Combined ({len(combined)} records)")
                pass

            if success_messages:
                message = f"Data saved successfully: {', '.join(success_messages)}"
                self.logger.info(message)
                return True, message
            else:
                return False, "No data to save"

        except Exception as e:
            error_msg = f"Failed to save data: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    # Compatibility methods for GUI
    def get_all_skus(self) -> List[str]:
        """Get all linking values (compatibility method for GUI)."""
        return self.get_all_link_values()
    
    def get_sku_data(self, sku: str) -> Dict[str, Any]:
        """Get data for a specific SKU (compatibility method for GUI)."""
        return self.get_link_value_data(sku)
    
    def get_field_mappings(self) -> Dict[str, Any]:
        """Get field mappings (compatibility method for GUI)."""
        return self.mappings.get("field_mappings", {})
    
    def get_available_fields(self) -> Dict[str, List[str]]:
        """Get available fields from both systems (compatibility method for GUI)."""
        available = {"netsuite": [], "shopify": []}
        
        if self.netsuite_data is not None:
            available["netsuite"] = list(self.netsuite_data.columns)
        
        if self.shopify_data is not None:
            available["shopify"] = list(self.shopify_data.columns)
        
        return available
    
    def get_available_netsuite_fields(self) -> List[str]:
        """Get available NetSuite fields from the merged database."""
        if self.combined_data is not None:
            ns_fields = []
            prefix = f'{self.db1_name}_'
            for col in self.combined_data.columns:
                if col.startswith(prefix):
                    original_field = col[len(prefix):]
                    ns_fields.append(original_field)
            return sorted(ns_fields)
        return []
    
    def get_available_shopify_fields(self) -> List[str]:
        """Get available Shopify fields from the merged database."""
        if self.combined_data is not None:
            sf_fields = []
            prefix = f'{self.db2_name}_'
            for col in self.combined_data.columns:
                if col.startswith(prefix):
                    original_field = col[len(prefix):]
                    sf_fields.append(original_field)
            return sorted(sf_fields)
        return []
    
    def get_linking_configuration(self) -> Dict[str, Any]:
        """Get linking field configuration."""
        return {
            "primary_link": self.mappings.get("primary_link", {"netsuite": "", "shopify": ""}),
            "secondary_links": self.mappings.get("secondary_links", [])
        }
    
    def save_linking_configuration(self, config: Dict[str, Any]) -> bool:
        """Save linking field configuration."""
        try:
            self.mappings["primary_link"] = config.get("primary_link", {"netsuite": "", "shopify": ""})
            self.mappings["secondary_links"] = config.get("secondary_links", [])
            self.save_field_mappings()
            return True
        except Exception as e:
            print(f"Error saving linking configuration: {e}")
            try:
                success_messages = []
                output_dir = "output_data"
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                # Save NetSuite and Shopify as CSVs in output_data
                if self.netsuite_data is not None:
                    netsuite_path = os.path.join(output_dir, "NetSuiteData.csv")
                    self.netsuite_data.to_csv(netsuite_path, index=False)
                    success_messages.append(f"NetSuite ({len(self.netsuite_data)} records)")
                if self.shopify_data is not None:
                    shopify_path = os.path.join(output_dir, "ShopifyData.csv")
                    self.shopify_data.to_csv(shopify_path, index=False)
                    success_messages.append(f"Shopify ({len(self.shopify_data)} records)")
                # Save combined output data to output_data folder as CSV
                combined = self.get_combined_data()
                if combined is not None:
                    combined_path = os.path.join(output_dir, "CombinedData.csv")
                    combined.to_csv(combined_path, index=False)
                    success_messages.append(f"Combined ({len(combined)} records)")
                if success_messages:
                    message = f"Data saved successfully: {', '.join(success_messages)}"
                    self.logger.info(message)
                    return True, message
                else:
                    return False, "No data to save"
            except Exception as e:
                error_msg = f"Failed to save data: {str(e)}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # Save the configuration
            self.save_field_mappings()
            self.logger.info(f"Field mapping updated: {source_field} -> {target_field}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating field mapping: {e}")
            return False
    
    def add_field_mapping(self, source_field: str, target_field: str, description: str = "") -> bool:
        """Add a new field mapping (alias for update_field_mapping for GUI compatibility)."""
        self.logger.info(f"Field mapping add requested: {source_field} -> {target_field}")
        return self.update_field_mapping(source_field, target_field, description)
    
    def export_data(self, format_type: str, filename: str = None) -> Tuple[bool, str]:
        """Export data in specified format (compatibility method for GUI)."""
        try:
            if filename is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"ups_export_{timestamp}.{format_type}"
            
            # Ensure exports directory exists
            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            export_path = os.path.join(export_dir, filename)
            
            if format_type.lower() == 'csv':
                combined = self.get_combined_data()
                if combined is not None:
                    combined.to_csv(export_path, index=False)
                    message = f"Data exported to {export_path} ({len(combined)} records)"
                    self.logger.info(message)
                    return True, message
                else:
                    return False, "No combined data available to export"
            else:
                return False, f"Export format '{format_type}' not supported"
                
        except Exception as e:
            error_msg = f"Failed to export data: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def save_field_mappings(self) -> bool:
        """Save field mappings (compatibility method for GUI)."""
        try:
            with open(self.mappings_file, 'w') as f:
                json.dump(self.mappings, f, indent=2)
            self.logger.info(" field mappings saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save  field mappings: {e}")
            return False
