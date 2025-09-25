"""
Unmatched Items Page
Shows SKUs/items that exist in one system but not the other for data quality analysis.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from typing import Optional, Dict, List, Tuple


class UnmatchedItemsPage:
    """Page for analyzing unmatched items between databases."""
    
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
        self.db1_only: Optional[pd.DataFrame] = None
        self.db2_only: Optional[pd.DataFrame] = None
        self.matched_items: Optional[pd.DataFrame] = None
        
        # UI Components
        self.stats_vars = {}
        self.db1_tree = None
        self.db2_tree = None
        
        self.setup_interface()
        
    def extract_original_datasets_from_merged(self, combined_data):
        """Extract original database datasets from merged data using dynamic DB prefixes."""
        try:
            prefix1 = f"{self.db1_name}_"
            prefix2 = f"{self.db2_name}_"
            # Get DB1_ columns and rename them for database 1 dataset
            db1_cols = [col for col in combined_data.columns if col.startswith(prefix1)]
            db1_data_dict = {}
            
            # Extract DB1_ columns and remove prefix
            for col in db1_cols:
                original_col = col[len(prefix1):]
                db1_data_dict[original_col] = combined_data[col]
            
            # Add the normalized key as well for reference
            if 'NormalizedKey' in combined_data.columns:
                db1_data_dict['NormalizedKey'] = combined_data['NormalizedKey']
            # Add system-specific Key as canonical 'Key' for database 1
            db1_key_col = f"{self.db1_name}_Key"
            if db1_key_col in combined_data.columns:
                db1_data_dict['Key'] = combined_data[db1_key_col]
            
            # Create database 1 DataFrame efficiently
            db1_data = pd.DataFrame(db1_data_dict)
            
            # Filter out rows where all DB1_ columns are null (these are database 2-only items)
            if db1_cols:
                db1_mask = combined_data[db1_cols].notna().any(axis=1)
                db1_data = db1_data[db1_mask].reset_index(drop=True)
            
            # Get DB2_ columns and rename them for database 2 dataset
            db2_cols = [col for col in combined_data.columns if col.startswith(prefix2)]
            db2_data_dict = {}
            
            # Extract DB2_ columns and remove prefix
            for col in db2_cols:
                original_col = col[len(prefix2):]
                db2_data_dict[original_col] = combined_data[col]
            
            # Add the normalized key as well for reference
            if 'NormalizedKey' in combined_data.columns:
                db2_data_dict['NormalizedKey'] = combined_data['NormalizedKey']
            # Add system-specific Key as canonical 'Key' for database 2
            db2_key_col = f"{self.db2_name}_Key"
            if db2_key_col in combined_data.columns:
                db2_data_dict['Key'] = combined_data[db2_key_col]
            
            # Create database 2 DataFrame efficiently
            db2_data = pd.DataFrame(db2_data_dict)
            
            # Filter out rows where all DB2_ columns are null (these are database 1-only items)
            if db2_cols:
                db2_mask = combined_data[db2_cols].notna().any(axis=1)
                db2_data = db2_data[db2_mask].reset_index(drop=True)
            
            return db1_data, db2_data
            
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
            'total_db1': tk.StringVar(value="0"),
            'total_db2': tk.StringVar(value="0"),
            'matched': tk.StringVar(value="0"),
            'db1_only': tk.StringVar(value="0"),
            'db2_only': tk.StringVar(value="0"),
            'match_rate': tk.StringVar(value="0%")
        }
        
        # Row 1: Totals
        ttk.Label(stats_grid, text=f"Total {self.db1_name} Items:").grid(row=0, column=0, sticky='w', padx=(0, 5))
        ttk.Label(stats_grid, textvariable=self.stats_vars['total_db1'], font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky='w', padx=(0, 20))
        
        ttk.Label(stats_grid, text=f"Total {self.db2_name} Items:").grid(row=0, column=2, sticky='w', padx=(0, 5))
        ttk.Label(stats_grid, textvariable=self.stats_vars['total_db2'], font=('Arial', 10, 'bold')).grid(row=0, column=3, sticky='w', padx=(0, 20))
        
        # Row 2: Matches
        ttk.Label(stats_grid, text="Matched Items:").grid(row=1, column=0, sticky='w', padx=(0, 5), pady=(5, 0))
        ttk.Label(stats_grid, textvariable=self.stats_vars['matched'], font=('Arial', 10, 'bold'), foreground='green').grid(row=1, column=1, sticky='w', padx=(0, 20), pady=(5, 0))
        
        ttk.Label(stats_grid, text="Match Rate:").grid(row=1, column=2, sticky='w', padx=(0, 5), pady=(5, 0))
        ttk.Label(stats_grid, textvariable=self.stats_vars['match_rate'], font=('Arial', 10, 'bold'), foreground='green').grid(row=1, column=3, sticky='w', padx=(0, 20), pady=(5, 0))
        
        # Row 3: Unmatched
        ttk.Label(stats_grid, text=f"{self.db1_name} Only:").grid(row=2, column=0, sticky='w', padx=(0, 5), pady=(5, 0))
        ttk.Label(stats_grid, textvariable=self.stats_vars['db1_only'], font=('Arial', 10, 'bold'), foreground='red').grid(row=2, column=1, sticky='w', padx=(0, 20), pady=(5, 0))
        
        ttk.Label(stats_grid, text=f"{self.db2_name} Only:").grid(row=2, column=2, sticky='w', padx=(0, 5), pady=(5, 0))
        ttk.Label(stats_grid, textvariable=self.stats_vars['db2_only'], font=('Arial', 10, 'bold'), foreground='red').grid(row=2, column=3, sticky='w', padx=(0, 20), pady=(5, 0))
    
    def create_results_section(self, parent):
        """Create results section with tabbed interface."""
        results_frame = ttk.LabelFrame(parent, text="Unmatched Items", padding=10)
        results_frame.pack(fill='both', expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(results_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # Database 1 Only tab
        self.create_db1_only_tab()
        
        # Database 2 Only tab
        self.create_db2_only_tab()
    
    def create_db1_only_tab(self):
        """Create tab for items that exist only in database 1."""
        db1_frame = ttk.Frame(self.notebook)
        self.notebook.add(db1_frame, text=f"{self.db1_name} Only")
        
        # Search frame
        search_frame = ttk.Frame(db1_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=(0, 5))
        self.db1_search_var = tk.StringVar()
        db1_search_entry = ttk.Entry(search_frame, textvariable=self.db1_search_var, width=30)
        db1_search_entry.pack(side='left', padx=(0, 10))
        db1_search_entry.bind('<KeyRelease>', lambda e: self.filter_db1_results())
        
        ttk.Button(search_frame, text="Clear", command=lambda: self.clear_search('db1')).pack(side='left')
        
        # Treeview for database 1 items
        columns = ('SKU',)
        self.db1_tree = ttk.Treeview(db1_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.db1_tree.heading(col, text=col)
            self.db1_tree.column(col, width=200, anchor='center')
        
        # Scrollbars
        db1_v_scroll = ttk.Scrollbar(db1_frame, orient='vertical', command=self.db1_tree.yview)
        db1_h_scroll = ttk.Scrollbar(db1_frame, orient='horizontal', command=self.db1_tree.xview)
        self.db1_tree.configure(yscrollcommand=db1_v_scroll.set, xscrollcommand=db1_h_scroll.set)
        
        # Pack scrollbars first, then treeview
        db1_v_scroll.pack(side='right', fill='y')
        db1_h_scroll.pack(side='bottom', fill='x')
        self.db1_tree.pack(side='left', fill='both', expand=True)
    
    def create_db2_only_tab(self):
        """Create tab for items that exist only in database 2."""
        db2_frame = ttk.Frame(self.notebook)
        self.notebook.add(db2_frame, text=f"{self.db2_name} Only")
        
        # Search frame
        search_frame = ttk.Frame(db2_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=(0, 5))
        self.db2_search_var = tk.StringVar()
        db2_search_entry = ttk.Entry(search_frame, textvariable=self.db2_search_var, width=30)
        db2_search_entry.pack(side='left', padx=(0, 10))
        db2_search_entry.bind('<KeyRelease>', lambda e: self.filter_db2_results())
        
        ttk.Button(search_frame, text="Clear", command=lambda: self.clear_search('db2')).pack(side='left')
        
        # Treeview for database 2 items
        columns = ('SKU',)
        self.db2_tree = ttk.Treeview(db2_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.db2_tree.heading(col, text=col)
            self.db2_tree.column(col, width=200, anchor='center')
        
        # Scrollbars
        db2_v_scroll = ttk.Scrollbar(db2_frame, orient='vertical', command=self.db2_tree.yview)
        db2_h_scroll = ttk.Scrollbar(db2_frame, orient='horizontal', command=self.db2_tree.xview)
        self.db2_tree.configure(yscrollcommand=db2_v_scroll.set, xscrollcommand=db2_h_scroll.set)
        
        # Pack scrollbars first, then treeview
        db2_v_scroll.pack(side='right', fill='y')
        db2_h_scroll.pack(side='bottom', fill='x')
        self.db2_tree.pack(side='left', fill='both', expand=True)
    
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
                messagebox.showwarning("No Data", f"Please load data first from both {self.db1_name} and {self.db2_name}.")
                self.update_status("No data available for analysis")
                return
            
            # Get primary link field configuration
            try:
                db1_field, db2_field = self.backend.get_primary_link_field()
                if not db1_field or not db2_field:
                    messagebox.showerror("Configuration Error", "Primary link fields not configured. Please set up field mappings first.")
                    return
            except Exception as e:
                messagebox.showerror("Configuration Error", f"Error getting primary link fields: {e}")
                return
            
            # Extract original datasets from merged structure
            db1_data, db2_data = self.extract_original_datasets_from_merged(combined_data)
            
            if db1_data is None or db2_data is None:
                messagebox.showerror("Data Error", "Could not extract original datasets from merged data.")
                self.update_status("Error extracting datasets for analysis")
                return
            
            # In extracted datasets, we inject system Keys as canonical 'Key'
            db1_sku_col = 'Key'
            db2_sku_col = 'Key'
            
            # Get SKU values
            db1_skus = set()
            db2_skus = set()
            
            if db1_sku_col in db1_data.columns:
                db1_series = db1_data[db1_sku_col].astype(str).apply(self.clean_sku)
                if not self.show_empty_var.get():
                    db1_series = db1_series[db1_series.notna() & (db1_series != '') & (db1_series != 'nan')]
                db1_skus = set(db1_series.unique())
                # Remove None values
                db1_skus.discard(None)
            
            if db2_sku_col in db2_data.columns:
                db2_series = db2_data[db2_sku_col].astype(str).apply(self.clean_sku)
                if not self.show_empty_var.get():
                    db2_series = db2_series[db2_series.notna() & (db2_series != '') & (db2_series != 'nan')]
                db2_skus = set(db2_series.unique())
                # Remove None values
                db2_skus.discard(None)
            
            # Find unmatched items
            db1_only_skus = db1_skus - db2_skus
            db2_only_skus = db2_skus - db1_skus
            matched_skus = db1_skus & db2_skus
            
            # Get full records for unmatched items
            self.db1_only = self.get_db1_records(db1_only_skus, db1_sku_col, db1_data)
            self.db2_only = self.get_db2_records(db2_only_skus, db2_sku_col, db2_data)
            
            # Update statistics
            self.update_statistics(len(db1_skus), len(db2_skus), len(matched_skus), len(db1_only_skus), len(db2_only_skus))
            
            # Populate the trees
            self.populate_db1_tree()
            self.populate_db2_tree()
            
            self.update_status(f"Analysis complete: {len(db1_only_skus)} {self.db1_name}-only, {len(db2_only_skus)} {self.db2_name}-only items found")
            
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
    
    def get_db1_records(self, skus, sku_column, db1_data):
        """Get full Database 1 records for the specified SKUs."""
        if not skus or db1_data is None or db1_data.empty:
            return pd.DataFrame()
        
        db1_data_copy = db1_data.copy()
        db1_data_copy['cleaned_sku'] = db1_data_copy[sku_column].astype(str).apply(self.clean_sku)
        
        # Filter records
        filtered = db1_data_copy[db1_data_copy['cleaned_sku'].isin(skus)]
        
        # Select relevant columns
        columns_to_show = []
        if sku_column in filtered.columns:
            columns_to_show.append(sku_column)
        
        # Add other common columns if they exist (using original column names)
        for col in ['Internal ID', 'Name', 'Type', 'Class', 'Category']:
            if col in filtered.columns:
                columns_to_show.append(col)
        
        return filtered[columns_to_show] if columns_to_show else filtered
    
    def get_db2_records(self, skus, sku_column, db2_data):
        """Get full Database 2 records for the specified SKUs."""
        if not skus or db2_data is None or db2_data.empty:
            return pd.DataFrame()
        
        db2_data_copy = db2_data.copy()
        db2_data_copy['cleaned_sku'] = db2_data_copy[sku_column].astype(str).apply(self.clean_sku)
        
        # Filter records
        filtered = db2_data_copy[db2_data_copy['cleaned_sku'].isin(skus)]
        
        # Select relevant columns
        columns_to_show = []
        if sku_column in filtered.columns:
            columns_to_show.append(sku_column)
        
        # Add other common columns if they exist (using original column names)
        for col in ['ID', 'Title', 'Handle', 'Status', 'Published']:
            if col in filtered.columns:
                columns_to_show.append(col)
        
        return filtered[columns_to_show] if columns_to_show else filtered
    
    def update_statistics(self, total_db1, total_db2, matched, db1_only, db2_only):
        """Update the statistics display."""
        self.stats_vars['total_db1'].set(str(total_db1))
        self.stats_vars['total_db2'].set(str(total_db2))
        self.stats_vars['matched'].set(str(matched))
        self.stats_vars['db1_only'].set(str(db1_only))
        self.stats_vars['db2_only'].set(str(db2_only))
        
        # Calculate match rate
        total_unique = len(set(range(total_db1)) | set(range(total_db2)))  # Simplified calculation
        if total_db1 > 0 and total_db2 > 0:
            match_rate = (matched / max(total_db1, total_db2)) * 100
            self.stats_vars['match_rate'].set(f"{match_rate:.1f}%")
        else:
            self.stats_vars['match_rate'].set("0%")
    
    def populate_db1_tree(self):
        """Populate the database 1-only items tree."""
        # Clear existing items
        for item in self.db1_tree.get_children():
            self.db1_tree.delete(item)
        
        if self.db1_only is None or self.db1_only.empty:
            return
        
        # Add items to tree
        for _, row in self.db1_only.iterrows():
            # The SKU column is named 'Key' after extraction
            sku_value = ""
            if 'Key' in row.index:
                sku_value = self.format_display_value(row['Key'], is_sku=True)
            
            # Insert only the SKU value
            self.db1_tree.insert('', 'end', values=(sku_value,))
    
    def populate_db2_tree(self):
        """Populate the database 2-only items tree."""
        # Clear existing items
        for item in self.db2_tree.get_children():
            self.db2_tree.delete(item)
        
        if self.db2_only is None or self.db2_only.empty:
            return
        
        # Add items to tree
        for _, row in self.db2_only.iterrows():
            # The SKU column is named 'Key' after extraction
            sku_value = ""
            if 'Key' in row.index:
                sku_value = self.format_display_value(row['Key'], is_sku=True)
            
            # Insert only the SKU value
            self.db2_tree.insert('', 'end', values=(sku_value,))
    
    def filter_db1_results(self):
        """Filter database 1 results based on search term."""
        search_term = self.db1_search_var.get().lower()
        
        # Clear and repopulate tree with filtered results
        for item in self.db1_tree.get_children():
            self.db1_tree.delete(item)
        
        if self.db1_only is None or self.db1_only.empty:
            return
        
        for _, row in self.db1_only.iterrows():
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
                self.db1_tree.insert('', 'end', values=(sku_value,))
    
    def filter_db2_results(self):
        """Filter database 2 results based on search term."""
        search_term = self.db2_search_var.get().lower()
        
        # Clear and repopulate tree with filtered results
        for item in self.db2_tree.get_children():
            self.db2_tree.delete(item)
        
        if self.db2_only is None or self.db2_only.empty:
            return
        
        for _, row in self.db2_only.iterrows():
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
                self.db2_tree.insert('', 'end', values=(sku_value,))
    
    def clear_search(self, system):
        """Clear search and show all results."""
        if system == 'db1':
            self.db1_search_var.set("")
            self.filter_db1_results()
        else:
            self.db2_search_var.set("")
            self.filter_db2_results()
    
    def export_unmatched_report(self):
        """Export unmatched items report to Excel."""
        try:
            from datetime import datetime
            import os
            
            if self.db1_only is None and self.db2_only is None:
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
                
                # Export Database 1-only items
                if self.db1_only is not None and not self.db1_only.empty:
                    self.db1_only.to_excel(writer, sheet_name=f'{self.db1_name} Only', index=False)
                
                # Export Database 2-only items
                if self.db2_only is not None and not self.db2_only.empty:
                    self.db2_only.to_excel(writer, sheet_name=f'{self.db2_name} Only', index=False)
                
                # Create summary sheet
                summary_data = {
                    'Metric': [f'Total {self.db1_name} Items', f'Total {self.db2_name} Items', 'Matched Items', f'{self.db1_name} Only', f'{self.db2_name} Only', 'Match Rate'],
                    'Value': [
                        self.stats_vars['total_db1'].get(),
                        self.stats_vars['total_db2'].get(),
                        self.stats_vars['matched'].get(),
                        self.stats_vars['db1_only'].get(),
                        self.stats_vars['db2_only'].get(),
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
