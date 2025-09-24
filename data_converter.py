"""
Data Converter Utility
Converts Excel files from NetSuite and Shopify to CSV format with proper field mapping.
"""
import pandas as pd
import os
import json
import logging
from typing import Dict, List, Optional, Tuple


class DataConverter:
    """Handles conversion of Excel data to CSV format with field mapping."""
    
    def __init__(self, config_path: str = "field_mappings.json"):
        self.config_path = config_path
        
        # Setup logging first
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("DataConverter")
        
        # Then load config
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Load the field mappings configuration."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    content = f.read().strip()
                    
                if content:
                    return json.loads(content)
                else:
                    self.logger.warning(f"Configuration file is empty: {self.config_path}")
                    return {}
            else:
                self.logger.warning(f"Configuration file not found: {self.config_path}")
                return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return {}
    
    def convert_netsuite_to_csv(self) -> Tuple[bool, str]:
        """Convert NetSuite Excel file to CSV format."""
        try:
            source_config = self.config.get("data_sources", {}).get("netsuite", {})
            excel_path = source_config.get("file_path")
            csv_path = source_config.get("csv_export_path")
            
            if not excel_path or not os.path.exists(excel_path):
                return False, f"NetSuite Excel file not found: {excel_path}"
            
            # Read Excel file
            self.logger.info(f"Reading NetSuite data from {excel_path}")
            df = pd.read_excel(excel_path)
            
            # Get relevant fields based on mappings
            relevant_fields = self.get_netsuite_relevant_fields()
            
            # Filter to only relevant columns that exist
            existing_fields = [field for field in relevant_fields if field in df.columns]
            df_filtered = df[existing_fields]
            
            # Ensure data directory exists
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            
            # Export to CSV
            df_filtered.to_csv(csv_path, index=False)
            
            self.logger.info(f"NetSuite data converted to CSV: {csv_path}")
            self.logger.info(f"Records: {len(df_filtered)}, Fields: {len(existing_fields)}")
            
            return True, f"NetSuite data converted successfully. {len(df_filtered)} records exported."
            
        except Exception as e:
            error_msg = f"Failed to convert NetSuite data: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def convert_shopify_to_csv(self) -> Tuple[bool, str]:
        """Convert Shopify Excel file to CSV format."""
        try:
            source_config = self.config.get("data_sources", {}).get("shopify", {})
            excel_path = source_config.get("file_path")
            csv_path = source_config.get("csv_export_path")
            
            if not excel_path or not os.path.exists(excel_path):
                return False, f"Shopify Excel file not found: {excel_path}"
            
            # Read Excel file
            self.logger.info(f"Reading Shopify data from {excel_path}")
            df = pd.read_excel(excel_path)
            
            # Get relevant fields based on mappings
            relevant_fields = self.get_shopify_relevant_fields()
            
            # Filter to only relevant columns that exist
            existing_fields = [field for field in relevant_fields if field in df.columns]
            df_filtered = df[existing_fields]
            
            # Ensure data directory exists
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            
            # Export to CSV
            df_filtered.to_csv(csv_path, index=False)
            
            self.logger.info(f"Shopify data converted to CSV: {csv_path}")
            self.logger.info(f"Records: {len(df_filtered)}, Fields: {len(existing_fields)}")
            
            return True, f"Shopify data converted successfully. {len(df_filtered)} records exported."
            
        except Exception as e:
            error_msg = f"Failed to convert Shopify data: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def get_netsuite_relevant_fields(self) -> List[str]:
        """Get list of relevant NetSuite fields from configuration."""
        fields = []
        
        # Add primary linking field
        linking_config = self.config.get("linking_configuration", {})
        primary_link = linking_config.get("primary_link_field", {})
        if primary_link.get("netsuite_field"):
            fields.append(primary_link["netsuite_field"])
        
        # Add secondary linking fields
        secondary_links = linking_config.get("secondary_link_fields", [])
        for link in secondary_links:
            if link.get("netsuite_field"):
                fields.append(link["netsuite_field"])
        
        # Add mapped fields
        field_mappings = self.config.get("field_mappings", {})
        for mapping in field_mappings.values():
            if mapping.get("netsuite_field"):
                fields.append(mapping["netsuite_field"])
        
        return list(set(fields))  # Remove duplicates
    
    def get_shopify_relevant_fields(self) -> List[str]:
        """Get list of relevant Shopify fields from configuration."""
        fields = []
        
        # Add primary linking field
        linking_config = self.config.get("linking_configuration", {})
        primary_link = linking_config.get("primary_link_field", {})
        if primary_link.get("shopify_field"):
            fields.append(primary_link["shopify_field"])
        
        # Add secondary linking fields
        secondary_links = linking_config.get("secondary_link_fields", [])
        for link in secondary_links:
            if link.get("shopify_field"):
                fields.append(link["shopify_field"])
        
        # Add mapped fields
        field_mappings = self.config.get("field_mappings", {})
        for mapping in field_mappings.values():
            if mapping.get("shopify_field"):
                fields.append(mapping["shopify_field"])
        
        return list(set(fields))  # Remove duplicates
    
    def convert_all(self) -> Tuple[bool, str]:
        """Convert both NetSuite and Shopify files to CSV."""
        messages = []
        overall_success = True
        
        # Convert NetSuite
        ns_success, ns_message = self.convert_netsuite_to_csv()
        messages.append(f"NetSuite: {ns_message}")
        if not ns_success:
            overall_success = False
        
        # Convert Shopify
        sf_success, sf_message = self.convert_shopify_to_csv()
        messages.append(f"Shopify: {sf_message}")
        if not sf_success:
            overall_success = False
        
        return overall_success, " | ".join(messages)
    
    def validate_conversions(self) -> Tuple[bool, str]:
        """Validate that CSV files were created successfully."""
        messages = []
        success = True
        
        source_config = self.config.get("data_sources", {})
        
        # Check NetSuite CSV
        netsuite_csv = source_config.get("netsuite", {}).get("csv_export_path")
        if netsuite_csv and os.path.exists(netsuite_csv):
            try:
                df = pd.read_csv(netsuite_csv)
                messages.append(f"NetSuite CSV: {len(df)} records")
            except Exception as e:
                messages.append(f"NetSuite CSV error: {e}")
                success = False
        else:
            messages.append("NetSuite CSV: Not found")
            success = False
        
        # Check Shopify CSV
        shopify_csv = source_config.get("shopify", {}).get("csv_export_path")
        if shopify_csv and os.path.exists(shopify_csv):
            try:
                df = pd.read_csv(shopify_csv)
                messages.append(f"Shopify CSV: {len(df)} records")
            except Exception as e:
                messages.append(f"Shopify CSV error: {e}")
                success = False
        else:
            messages.append("Shopify CSV: Not found")
            success = False
        
        return success, " | ".join(messages)


def main():
    """Main function for standalone execution."""
    print("UPS Data Manager - Data Converter")
    print("Converting Excel files to CSV format...")
    
    converter = DataConverter()
    
    # Convert all files
    success, message = converter.convert_all()
    print(f"Conversion result: {message}")
    
    # Validate conversions
    validation_success, validation_message = converter.validate_conversions()
    print(f"Validation result: {validation_message}")
    
    if success and validation_success:
        print("✓ All conversions completed successfully!")
        return 0
    else:
        print("✗ Some conversions failed.")
        return 1


if __name__ == "__main__":
    exit(main())