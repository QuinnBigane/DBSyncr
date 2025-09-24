"""
Unmatched Items Page
Shows SKUs/items that exist in one system but not the other for data quality analysis.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from typing import Optional, Dict, List, Tuple


class UnmatchedItemsPage:
    """Page for analyzing unmatched items between NetSuite and Shopify."""
    
    def __init__(self, parent, backend, update_status_callback):
        self.parent = parent
        self.backend = backend
        self.update_status = update_status_callback
        # Database name prefixes (dynamic)
        if hasattr(self.backend, 'get_database_names'):
            self.db1_name, self.db2_name = self.backend.get_database_names()
        else:
            self.db1_name, self.db2_name = 'DB1', 'DB2'
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Data storage
        self.netsuite_only: Optional[pd.DataFrame] = None
        self.shopify_only: Optional[pd.DataFrame] = None
        self.matched_items: Optional[pd.DataFrame] = None
        
        # UI Components
        self.stats_vars = {}
        self.netsuite_tree = None
        self.shopify_tree = None
        
        self.setup_interface()
        
    def extract_original_datasets_from_merged(self, combined_data):
        """Extract original NetSuite and Shopify datasets from merged data using dynamic DB prefixes."""
        try:
            prefix1 = f"{self.db1_name}_"
            prefix2 = f"{self.db2_name}_"
            # Get DB1_ columns and rename them for NetSuite dataset
            db1_cols = [col for col in combined_data.columns if col.startswith(prefix1)]
            ns_data_dict = {}
            
            # Extract DB1_ columns and remove prefix
            for col in db1_cols:
                original_col = col[len(prefix1):]
                ns_data_dict[original_col] = combined_data[col]
            
            # Add the normalized key as well for reference
            if 'NormalizedKey' in combined_data.columns:
                ns_data_dict['NormalizedKey'] = combined_data['NormalizedKey']
            # Add system-specific Key as canonical 'Key' for NetSuite
            ns_key_col = f"{self.db1_name}_Key"
            if ns_key_col in combined_data.columns:
                ns_data_dict['Key'] = combined_data[ns_key_col]
            
            # Create NetSuite DataFrame efficiently
            ns_data = pd.DataFrame(ns_data_dict)
            
            # Filter out rows where all DB1_ columns are null (these are Shopify-only items)
            if db1_cols:
                ns_mask = combined_data[db1_cols].notna().any(axis=1)
                ns_data = ns_data[ns_mask].reset_index(drop=True)
            
            # Get DB2_ columns and rename them for Shopify dataset
            db2_cols = [col for col in combined_data.columns if col.startswith(prefix2)]
            sf_data_dict = {}
            
            # Extract DB2_ columns and remove prefix
            for col in db2_cols:
                original_col = col[len(prefix2):]
                sf_data_dict[original_col] = combined_data[col]
            
            # Add the normalized key as well for reference
            if 'NormalizedKey' in combined_data.columns:
                sf_data_dict['NormalizedKey'] = combined_data['NormalizedKey']
            # Add system-specific Key as canonical 'Key' for Shopify
            sf_key_col = f"{self.db2_name}_Key"
            if sf_key_col in combined_data.columns:
                sf_data_dict['Key'] = combined_data[sf_key_col]
            
            # Create Shopify DataFrame efficiently
            sf_data = pd.DataFrame(sf_data_dict)
            
            # Filter out rows where all DB2_ columns are null (these are NetSuite-only items)
            if db2_cols:
                sf_mask = combined_data[db2_cols].notna().any(axis=1)
                sf_data = sf_data[sf_mask].reset_index(drop=True)
            
            return ns_data, sf_data
            
        except Exception as e:
            print(f"Error extracting original datasets: {e}")
            return None, None
        
    def setup_interface(self):
        """Setup the unmatched items interface."""
        # Main container with padding
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_container, text="Unmatched Items Analysis", font=('Arial', 14, 'bold'))
        title_label.pack(anchor='w', pady=(0, 10))
        
        # Description
        desc_label = ttk.Label(
            main_container, 
            text="Find SKUs that exist in one system but not the other to identify data synchronization issues.",
            font=('Arial', 10),
            foreground='gray'
        )
        desc_label.pack(anchor='w', pady=(0, 15))
        
        # Control section
        self.create_control_section(main_container)
        
        # Statistics section
        self.create_statistics_section(main_container)
        
        # Results section with tabs
        self.create_results_section(main_container)
        
        # Load initial data
        self.parent.after_idle(self.analyze_unmatched_items)
    
    def create_control_section(self, parent):
        """Create control buttons and options."""
        control_frame = ttk.LabelFrame(parent, text="Controls", padding=10)
        control_frame.pack(fill='x', pady=(0, 10))
        
        # Buttons frame
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(fill='x')
        
        # Refresh button
        ttk.Button(
            buttons_frame, 
            text="🔄 Refresh Analysis", 
            command=self.analyze_unmatched_items
        ).pack(side='left', padx=(0, 10))
        
        # Export button
        ttk.Button(
            buttons_frame, 
            text="📊 Export Report", 
            command=self.export_unmatched_report
        ).pack(side='left', padx=(0, 10))
        
        # Options frame
        options_frame = ttk.Frame(control_frame)
        options_frame.pack(fill='x', pady=(10, 0))
        
        # Show empty SKUs option
        self.show_empty_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Include items with empty/null SKUs",
            variable=self.show_empty_var,
            command=self.analyze_unmatched_items
        ).pack(side='left')
    
    def create_statistics_section(self, parent):
        """Create statistics display section."""
        stats_frame = ttk.LabelFrame(parent, text="Summary Statistics", padding=10)
        stats_frame.pack(fill='x', pady=(0, 10))
        
        # Create statistics grid
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill='x')
        
        # Initialize statistics variables
        self.stats_vars = {
            'total_netsuite': tk.StringVar(value="0"),
            'total_shopify': tk.StringVar(value="0"),
            'matched': tk.StringVar(value="0"),
            'netsuite_only': tk.StringVar(value="0"),
            'shopify_only': tk.StringVar(value="0"),
            'match_rate': tk.StringVar(value="0%")
        }
        
        # Row 1: Totals
        ttk.Label(stats_grid, text="Total NetSuite Items:").grid(row=0, column=0, sticky='w', padx=(0, 5))
        ttk.Label(stats_grid, textvariable=self.stats_vars['total_netsuite'], font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky='w', padx=(0, 20))
        
        ttk.Label(stats_grid, text="Total Shopify Items:").grid(row=0, column=2, sticky='w', padx=(0, 5))
        ttk.Label(stats_grid, textvariable=self.stats_vars['total_shopify'], font=('Arial', 10, 'bold')).grid(row=0, column=3, sticky='w', padx=(0, 20))
        
        # Row 2: Matches
        ttk.Label(stats_grid, text="Matched Items:").grid(row=1, column=0, sticky='w', padx=(0, 5), pady=(5, 0))
        ttk.Label(stats_grid, textvariable=self.stats_vars['matched'], font=('Arial', 10, 'bold'), foreground='green').grid(row=1, column=1, sticky='w', padx=(0, 20), pady=(5, 0))
        
        ttk.Label(stats_grid, text="Match Rate:").grid(row=1, column=2, sticky='w', padx=(0, 5), pady=(5, 0))
        ttk.Label(stats_grid, textvariable=self.stats_vars['match_rate'], font=('Arial', 10, 'bold'), foreground='green').grid(row=1, column=3, sticky='w', padx=(0, 20), pady=(5, 0))
        
        # Row 3: Unmatched
        ttk.Label(stats_grid, text="NetSuite Only:").grid(row=2, column=0, sticky='w', padx=(0, 5), pady=(5, 0))
        ttk.Label(stats_grid, textvariable=self.stats_vars['netsuite_only'], font=('Arial', 10, 'bold'), foreground='red').grid(row=2, column=1, sticky='w', padx=(0, 20), pady=(5, 0))
        
        ttk.Label(stats_grid, text="Shopify Only:").grid(row=2, column=2, sticky='w', padx=(0, 5), pady=(5, 0))
        ttk.Label(stats_grid, textvariable=self.stats_vars['shopify_only'], font=('Arial', 10, 'bold'), foreground='red').grid(row=2, column=3, sticky='w', padx=(0, 20), pady=(5, 0))
    
    def create_results_section(self, parent):
        """Create results section with tabbed interface."""
        results_frame = ttk.LabelFrame(parent, text="Unmatched Items", padding=10)
        results_frame.pack(fill='both', expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(results_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # NetSuite Only tab
        self.create_netsuite_only_tab()
        
        # Shopify Only tab
        self.create_shopify_only_tab()
    
    def create_netsuite_only_tab(self):
        """Create tab for items that exist only in NetSuite."""
        ns_frame = ttk.Frame(self.notebook)
        self.notebook.add(ns_frame, text="NetSuite Only")
        
        # Search frame
        search_frame = ttk.Frame(ns_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=(0, 5))
        self.ns_search_var = tk.StringVar()
        ns_search_entry = ttk.Entry(search_frame, textvariable=self.ns_search_var, width=30)
        ns_search_entry.pack(side='left', padx=(0, 10))
        ns_search_entry.bind('<KeyRelease>', lambda e: self.filter_netsuite_results())
        
        ttk.Button(search_frame, text="Clear", command=lambda: self.clear_search('netsuite')).pack(side='left')
        
        # Treeview for NetSuite items
        columns = ('SKU',)
        self.netsuite_tree = ttk.Treeview(ns_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.netsuite_tree.heading(col, text=col)
            self.netsuite_tree.column(col, width=200, anchor='center')
        
        # Scrollbars
        ns_v_scroll = ttk.Scrollbar(ns_frame, orient='vertical', command=self.netsuite_tree.yview)
        ns_h_scroll = ttk.Scrollbar(ns_frame, orient='horizontal', command=self.netsuite_tree.xview)
        self.netsuite_tree.configure(yscrollcommand=ns_v_scroll.set, xscrollcommand=ns_h_scroll.set)
        
        # Pack scrollbars first, then treeview
        ns_v_scroll.pack(side='right', fill='y')
        ns_h_scroll.pack(side='bottom', fill='x')
        self.netsuite_tree.pack(side='left', fill='both', expand=True)
    
    def create_shopify_only_tab(self):
        """Create tab for items that exist only in Shopify."""
        sf_frame = ttk.Frame(self.notebook)
        self.notebook.add(sf_frame, text="Shopify Only")
        
        # Search frame
        search_frame = ttk.Frame(sf_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=(0, 5))
        self.sf_search_var = tk.StringVar()
        sf_search_entry = ttk.Entry(search_frame, textvariable=self.sf_search_var, width=30)
        sf_search_entry.pack(side='left', padx=(0, 10))
        sf_search_entry.bind('<KeyRelease>', lambda e: self.filter_shopify_results())
        
        ttk.Button(search_frame, text="Clear", command=lambda: self.clear_search('shopify')).pack(side='left')
        
        # Treeview for Shopify items
        columns = ('SKU',)
        self.shopify_tree = ttk.Treeview(sf_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.shopify_tree.heading(col, text=col)
            self.shopify_tree.column(col, width=200, anchor='center')
        
        # Scrollbars
        sf_v_scroll = ttk.Scrollbar(sf_frame, orient='vertical', command=self.shopify_tree.yview)
        sf_h_scroll = ttk.Scrollbar(sf_frame, orient='horizontal', command=self.shopify_tree.xview)
        self.shopify_tree.configure(yscrollcommand=sf_v_scroll.set, xscrollcommand=sf_h_scroll.set)
        
        # Pack scrollbars first, then treeview
        sf_v_scroll.pack(side='right', fill='y')
        sf_h_scroll.pack(side='bottom', fill='x')
        self.shopify_tree.pack(side='left', fill='both', expand=True)
    
    def analyze_unmatched_items(self):
        """Analyze and find unmatched items between systems."""
        try:
            self.update_status("Analyzing unmatched items...")
            
            # Get data from the new merged database structure
            combined_data = None
            if hasattr(self.backend, 'get_combined_data'):
                try:
                    combined_data = self.backend.get_combined_data()
                except Exception:
                    pass
            
            if combined_data is None or combined_data.empty:
                messagebox.showwarning("No Data", "Please load data first from both NetSuite and Shopify.")
                self.update_status("No data available for analysis")
                return
            
            # Get primary link field configuration
            try:
                ns_field, sf_field = self.backend.get_primary_link_field()
                if not ns_field or not sf_field:
                    messagebox.showerror("Configuration Error", "Primary link fields not configured. Please set up field mappings first.")
                    return
            except Exception as e:
                messagebox.showerror("Configuration Error", f"Error getting primary link fields: {e}")
                return
            
            # Extract original datasets from merged structure
            ns_data, sf_data = self.extract_original_datasets_from_merged(combined_data)
            
            if ns_data is None or sf_data is None:
                messagebox.showerror("Data Error", "Could not extract original datasets from merged data.")
                self.update_status("Error extracting datasets for analysis")
                return
            
            # In extracted datasets, we inject system Keys as canonical 'Key'
            ns_sku_col = 'Key'
            sf_sku_col = 'Key'
            
            # Get SKU values
            ns_skus = set()
            sf_skus = set()
            
            if ns_sku_col in ns_data.columns:
                ns_series = ns_data[ns_sku_col].astype(str).apply(self.clean_sku)
                if not self.show_empty_var.get():
                    ns_series = ns_series[ns_series.notna() & (ns_series != '') & (ns_series != 'nan')]
                ns_skus = set(ns_series.unique())
                # Remove None values
                ns_skus.discard(None)
            
            if sf_sku_col in sf_data.columns:
                sf_series = sf_data[sf_sku_col].astype(str).apply(self.clean_sku)
                if not self.show_empty_var.get():
                    sf_series = sf_series[sf_series.notna() & (sf_series != '') & (sf_series != 'nan')]
                sf_skus = set(sf_series.unique())
                # Remove None values
                sf_skus.discard(None)
            
            # Find unmatched items
            ns_only_skus = ns_skus - sf_skus
            sf_only_skus = sf_skus - ns_skus
            matched_skus = ns_skus & sf_skus
            
            # Get full records for unmatched items
            self.netsuite_only = self.get_netsuite_records(ns_only_skus, ns_sku_col, ns_data)
            self.shopify_only = self.get_shopify_records(sf_only_skus, sf_sku_col, sf_data)
            
            # Update statistics
            self.update_statistics(len(ns_skus), len(sf_skus), len(matched_skus), len(ns_only_skus), len(sf_only_skus))
            
            # Populate the trees
            self.populate_netsuite_tree()
            self.populate_shopify_tree()
            
            self.update_status(f"Analysis complete: {len(ns_only_skus)} NetSuite-only, {len(sf_only_skus)} Shopify-only items found")
            
        except Exception as e:
            self.update_status(f"Error analyzing unmatched items: {str(e)}")
            messagebox.showerror("Analysis Error", f"Failed to analyze unmatched items: {str(e)}")
    
    def clean_sku(self, value):
        """Clean SKU value for comparison."""
        if pd.isna(value) or value in ['', 'nan', 'None']:
            return None
        
        # Convert to string and strip whitespace
        sku = str(value).strip()
        
        # Remove .0 suffix from numeric strings
        if sku.endswith('.0') and sku[:-2].replace('.', '').isdigit():
            sku = sku[:-2]
        
        return sku if sku else None
    
    def format_display_value(self, value, is_sku=False):
        """Format value for display in the tree, with special handling for SKUs."""
        if pd.isna(value) or value in ['', 'nan', 'None']:
            return ""
        
        # Convert to string
        display_value = str(value).strip()
        
        # For SKU-like values (numeric with .0), remove the .0 suffix
        if is_sku or (display_value.endswith('.0') and display_value[:-2].replace('.', '').isdigit()):
            if display_value.endswith('.0'):
                display_value = display_value[:-2]
        
        return display_value
    
    def get_netsuite_records(self, skus, sku_column, ns_data):
        """Get full NetSuite records for the specified SKUs."""
        if not skus or ns_data is None or ns_data.empty:
            return pd.DataFrame()
        
        ns_data_copy = ns_data.copy()
        ns_data_copy['cleaned_sku'] = ns_data_copy[sku_column].astype(str).apply(self.clean_sku)
        
        # Filter records
        filtered = ns_data_copy[ns_data_copy['cleaned_sku'].isin(skus)]
        
        # Select relevant columns
        columns_to_show = []
        if sku_column in filtered.columns:
            columns_to_show.append(sku_column)
        
        # Add other common columns if they exist (using original column names)
        for col in ['Internal ID', 'Name', 'Type', 'Class', 'Category']:
            if col in filtered.columns:
                columns_to_show.append(col)
        
        return filtered[columns_to_show] if columns_to_show else filtered
    
    def get_shopify_records(self, skus, sku_column, sf_data):
        """Get full Shopify records for the specified SKUs."""
        if not skus or sf_data is None or sf_data.empty:
            return pd.DataFrame()
        
        sf_data_copy = sf_data.copy()
        sf_data_copy['cleaned_sku'] = sf_data_copy[sku_column].astype(str).apply(self.clean_sku)
        
        # Filter records
        filtered = sf_data_copy[sf_data_copy['cleaned_sku'].isin(skus)]
        
        # Select relevant columns
        columns_to_show = []
        if sku_column in filtered.columns:
            columns_to_show.append(sku_column)
        
        # Add other common columns if they exist (using original column names)
        for col in ['ID', 'Title', 'Handle', 'Status', 'Published']:
            if col in filtered.columns:
                columns_to_show.append(col)
        
        return filtered[columns_to_show] if columns_to_show else filtered
    
    def update_statistics(self, total_ns, total_sf, matched, ns_only, sf_only):
        """Update the statistics display."""
        self.stats_vars['total_netsuite'].set(str(total_ns))
        self.stats_vars['total_shopify'].set(str(total_sf))
        self.stats_vars['matched'].set(str(matched))
        self.stats_vars['netsuite_only'].set(str(ns_only))
        self.stats_vars['shopify_only'].set(str(sf_only))
        
        # Calculate match rate
        total_unique = len(set(range(total_ns)) | set(range(total_sf)))  # Simplified calculation
        if total_ns > 0 and total_sf > 0:
            match_rate = (matched / max(total_ns, total_sf)) * 100
            self.stats_vars['match_rate'].set(f"{match_rate:.1f}%")
        else:
            self.stats_vars['match_rate'].set("0%")
    
    def populate_netsuite_tree(self):
        """Populate the NetSuite-only items tree."""
        # Clear existing items
        for item in self.netsuite_tree.get_children():
            self.netsuite_tree.delete(item)
        
        if self.netsuite_only is None or self.netsuite_only.empty:
            return
        
        # Add items to tree
        for _, row in self.netsuite_only.iterrows():
            # The SKU column is named 'Key' after extraction
            sku_value = ""
            if 'Key' in row.index:
                sku_value = self.format_display_value(row['Key'], is_sku=True)
            
            # Insert only the SKU value
            self.netsuite_tree.insert('', 'end', values=(sku_value,))
    
    def populate_shopify_tree(self):
        """Populate the Shopify-only items tree."""
        # Clear existing items
        for item in self.shopify_tree.get_children():
            self.shopify_tree.delete(item)
        
        if self.shopify_only is None or self.shopify_only.empty:
            return
        
        # Add items to tree
        for _, row in self.shopify_only.iterrows():
            # The SKU column is named 'Key' after extraction
            sku_value = ""
            if 'Key' in row.index:
                sku_value = self.format_display_value(row['Key'], is_sku=True)
            
            # Insert only the SKU value
            self.shopify_tree.insert('', 'end', values=(sku_value,))
    
    def filter_netsuite_results(self):
        """Filter NetSuite results based on search term."""
        search_term = self.ns_search_var.get().lower()
        
        # Clear and repopulate tree with filtered results
        for item in self.netsuite_tree.get_children():
            self.netsuite_tree.delete(item)
        
        if self.netsuite_only is None or self.netsuite_only.empty:
            return
        
        for _, row in self.netsuite_only.iterrows():
            # Check if search term matches any column
            match = False
            if not search_term:  # If search is empty, show all
                match = True
            else:
                for col in row.index:
                    if search_term in str(row[col]).lower():
                        match = True
                        break
            
            if match:
                # Only extract SKU value from canonical 'Key'
                sku_value = self.format_display_value(row.get('Key', ''), is_sku=True)
                
                # Insert only the SKU value
                self.netsuite_tree.insert('', 'end', values=(sku_value,))
    
    def filter_shopify_results(self):
        """Filter Shopify results based on search term."""
        search_term = self.sf_search_var.get().lower()
        
        # Clear and repopulate tree with filtered results
        for item in self.shopify_tree.get_children():
            self.shopify_tree.delete(item)
        
        if self.shopify_only is None or self.shopify_only.empty:
            return
        
        for _, row in self.shopify_only.iterrows():
            # Check if search term matches any column
            match = False
            if not search_term:  # If search is empty, show all
                match = True
            else:
                for col in row.index:
                    if search_term in str(row[col]).lower():
                        match = True
                        break
            
            if match:
                # Only extract SKU value from canonical 'Key'
                sku_value = self.format_display_value(row.get('Key', ''), is_sku=True)
                
                # Insert only the SKU value
                self.shopify_tree.insert('', 'end', values=(sku_value,))
    
    def clear_search(self, system):
        """Clear search and show all results."""
        if system == 'netsuite':
            self.ns_search_var.set("")
            self.filter_netsuite_results()
        else:
            self.sf_search_var.set("")
            self.filter_shopify_results()
    
    def export_unmatched_report(self):
        """Export unmatched items report to Excel."""
        try:
            from datetime import datetime
            import os
            
            if self.netsuite_only is None and self.shopify_only is None:
                messagebox.showwarning("No Data", "No unmatched items data to export.")
                return
            
            # Create exports directory if it doesn't exist
            if not os.path.exists("exports"):
                os.makedirs("exports")
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"exports/unmatched_items_report_{timestamp}.xlsx"
            
            # Create Excel writer
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                
                # Export NetSuite-only items
                if self.netsuite_only is not None and not self.netsuite_only.empty:
                    self.netsuite_only.to_excel(writer, sheet_name='NetSuite Only', index=False)
                
                # Export Shopify-only items
                if self.shopify_only is not None and not self.shopify_only.empty:
                    self.shopify_only.to_excel(writer, sheet_name='Shopify Only', index=False)
                
                # Create summary sheet
                summary_data = {
                    'Metric': ['Total NetSuite Items', 'Total Shopify Items', 'Matched Items', 'NetSuite Only', 'Shopify Only', 'Match Rate'],
                    'Value': [
                        self.stats_vars['total_netsuite'].get(),
                        self.stats_vars['total_shopify'].get(),
                        self.stats_vars['matched'].get(),
                        self.stats_vars['netsuite_only'].get(),
                        self.stats_vars['shopify_only'].get(),
                        self.stats_vars['match_rate'].get()
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            self.update_status(f"Unmatched items report exported to {filename}")
            messagebox.showinfo("Export Complete", f"Report exported successfully to:\n{filename}")
            
        except Exception as e:
            self.update_status(f"Error exporting report: {str(e)}")
            messagebox.showerror("Export Error", f"Failed to export report: {str(e)}")
    
    def refresh_data(self):
        """Refresh the unmatched items analysis."""
        self.analyze_unmatched_items()