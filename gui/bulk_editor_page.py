"""
Bulk Editor Page
GUI page for bulk editing of product data.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from .colored_table_view import ColoredTableView


class BulkEditorPage:
    """Bulk editor page for mass data editing."""
    
    def __init__(self, parent, backend, status_callback):
        self.parent = parent
        self.backend = backend
        self.update_status = status_callback
        
        # Get database names from backend
        if self.backend and hasattr(self.backend, 'get_database_names'):
            self.db1_name, self.db2_name = self.backend.get_database_names()
        else:
            self.db1_name, self.db2_name = "DB1", "DB2"
        
        # Data variables
        self.current_data = None
        self.filtered_data = None  # Data after applying filters
        self.selected_skus = set()
        self.column_vars = {}  # For column visibility tracking
        
        # Pagination variables
        self.current_page = 0
        self.items_per_page = 100
        self.total_filtered_items = 0
        
        # Filter variables
        self.hide_synced_data = tk.BooleanVar(value=False)
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        self.setup_interface()
    
    def setup_interface(self):
        """Setup the bulk editor interface."""
        # Main container with padding
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Search and filter section
        self.create_search_filter_section(main_container)
        
        # Bulk actions section
        self.create_bulk_actions_section(main_container)
        
        # Data table section
        self.create_data_table_section(main_container)
        
        # Load initial data in background to improve perceived performance
        self.parent.after_idle(self.refresh_data)
    
    def create_search_filter_section(self, parent):
        """Create search and filter controls."""
        filter_frame = ttk.LabelFrame(parent, text="Search & Filter", padding=10)
        filter_frame.pack(fill='x', pady=(0, 10))
        
        # Search row
        search_row = ttk.Frame(filter_frame)
        search_row.pack(fill='x', pady=(0, 5))
        
        ttk.Label(search_row, text="Search Key:").pack(side='left')
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_changed)
        search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=20)
        search_entry.pack(side='left', padx=(5, 10))
        
        ttk.Button(search_row, text="Clear", command=self.clear_search).pack(side='left', padx=(5, 10))
        
        # Add Configure Columns button to search row
        ttk.Button(search_row, text="Configure Columns...", command=self.open_column_visibility_popup).pack(side='right')
        
        # Filter row
        filter_row = ttk.Frame(filter_frame)
        filter_row.pack(fill='x', pady=(5, 0))
        
        ttk.Label(filter_row, text="Data Status:").pack(side='left')
        self.status_filter = ttk.Combobox(filter_row, values=["All Matched", "NS Data Complete", "SF Data Complete", "Both Complete"], 
                                          state="readonly", width=15)
        self.status_filter.set("All Matched")
        self.status_filter.pack(side='left', padx=(5, 10))
        self.status_filter.bind("<<ComboboxSelected>>", self.on_filter_changed)
        
        # Hide synced data button
        hide_synced_btn = ttk.Checkbutton(filter_row, text="Hide Sync'd Data", 
                                         variable=self.hide_synced_data,
                                         command=self.apply_filters)
        hide_synced_btn.pack(side='left', padx=(10, 0))
        
        # Show count and pagination row
        pagination_row = ttk.Frame(filter_frame)
        pagination_row.pack(fill='x', pady=(5, 0))
        
        # Item counter on left
        self.item_counter_var = tk.StringVar()
        self.item_counter_var.set("Showing 0-0 of 0 items")
        ttk.Label(pagination_row, textvariable=self.item_counter_var).pack(side='left')
        
        # Pagination controls in center
        pagination_controls = ttk.Frame(pagination_row)
        pagination_controls.pack(side='left', padx=(20, 0))
        
        self.prev_btn = ttk.Button(pagination_controls, text="◀ Previous", command=self.previous_page, state='disabled')
        self.prev_btn.pack(side='left', padx=(0, 5))
        
        self.page_label_var = tk.StringVar()
        self.page_label_var.set("Page 1")
        ttk.Label(pagination_controls, textvariable=self.page_label_var).pack(side='left', padx=(5, 5))
        
        self.next_btn = ttk.Button(pagination_controls, text="Next ▶", command=self.next_page, state='disabled')
        self.next_btn.pack(side='left', padx=(5, 0))
        
        # Show count on right
        self.show_var = tk.StringVar()
        self.show_combo = ttk.Combobox(pagination_row, textvariable=self.show_var, values=["100", "250", "500", "1000", "All"], 
                                       state="readonly", width=8)
        self.show_combo.set("100")
        self.show_combo.pack(side='right', padx=(5, 0))
        self.show_combo.bind("<<ComboboxSelected>>", self.on_show_changed)
        ttk.Label(pagination_row, text="Show:").pack(side='right')
    
    def create_bulk_actions_section(self, parent):
        """Create selection and sync controls."""
        actions_frame = ttk.LabelFrame(parent, text="Selection & Sync", padding=10)
        actions_frame.pack(fill='x', pady=(0, 10))
        
        # Top row with selection controls
        selection_row = ttk.Frame(actions_frame)
        selection_row.pack(fill='x', pady=(0, 5))
        
        # Selection count and basic controls
        ttk.Button(selection_row, text="Select All", command=self.select_all).pack(side='left', padx=(0, 5))
        ttk.Button(selection_row, text="Deselect All", command=self.deselect_all).pack(side='left', padx=(0, 10))
        
        self.selected_count_var = tk.StringVar()
        self.selected_count_var.set("Selected: 0")
        ttk.Label(selection_row, textvariable=self.selected_count_var).pack(side='left', padx=(0, 10))
        
        # Export button on right
        ttk.Button(selection_row, text="Export Selection", command=self.export_selection).pack(side='right')
        
        # Bottom row with sync controls
        sync_row = ttk.Frame(actions_frame)
        sync_row.pack(fill='x', pady=(5, 0))
        
        ttk.Label(sync_row, text="Sync Selected Items:").pack(side='left', padx=(0, 10))
        ttk.Button(sync_row, text=f"Sync to {self.db1_name}", command=lambda: self.sync_selected("db1")).pack(side='left', padx=(0, 5))
        ttk.Button(sync_row, text=f"Sync to {self.db2_name}", command=lambda: self.sync_selected("db2")).pack(side='left', padx=(0, 5))
    
    def create_data_table_section(self, parent):
        """Create the data table with color coding."""
        table_frame = ttk.LabelFrame(parent, text="Data Table", padding=5)
        table_frame.pack(fill='both', expand=True)
        
        # Get ALL available columns from the backend data
        try:
            data = self.backend.get_combined_data()
            if data is not None:
                all_available_columns = ['Select'] + list(data.columns)
            else:
                # Get available columns from backend field mappings
                all_available_columns = self.get_available_columns_from_mappings()
        except Exception as e:
            # Get available columns from backend field mappings
            all_available_columns = self.get_available_columns_from_mappings()
        
        # Get default visible columns from mappings
        default_visible_columns = self.get_default_visible_columns()
        
        # Create colored table view with ALL available columns for better field mapping visualization
        self.table_view = ColoredTableView(
            parent=table_frame,
            columns=all_available_columns,  # Pass all available columns
            backend=self.backend,  # Pass backend for database names
            on_selection_change=self.on_table_selection_change
        )
        
        # Set initial visible columns to just the mapped ones
        self.table_view.update_column_visibility(default_visible_columns)
        
        # Pack the table view
        self.table_view.get_frame().pack(fill='both', expand=True)
        
        # Set field mappings for color coding and merged headers
        field_mappings = self.backend.get_field_mappings_config()
        self.table_view.set_field_mappings(field_mappings)
        
        # Initialize column visibility for ALL database fields
        self.initialize_column_visibility()
    
    def initialize_column_visibility(self):
        """Initialize column visibility state for ALL available columns in the database."""
        # Get available columns from actual data or mappings
        all_columns = self.get_available_columns_from_mappings()
        
        # Try to get actual data to see what columns are available
        try:
            data = self.backend.get_combined_data()
            if data is not None:
                actual_columns = list(data.columns)
                # Use actual columns if available, otherwise fall back to mapping-based columns
                all_columns = actual_columns
        except Exception as e:
            pass  # Use mapping-based columns if data not available
        
        # Initialize visibility state for all columns
        self.column_vars = {}
        always_visible = ['Select', 'NormalizedKey']  # Only these are truly always visible
        
        # Get default visible columns from mappings
        default_visible_columns = self.get_default_visible_columns()
        
        for col in all_columns:
            if col not in always_visible:
                # Default: show mapped fields, hide other fields initially
                default_visible = col in default_visible_columns
                self.column_vars[col] = tk.BooleanVar(value=default_visible)
    
    def get_available_columns_from_mappings(self):
        """Get available columns based on the new normalized database structure."""
        columns = ['Select', 'NormalizedKey', f'{self.db1_name}_Key', f'{self.db2_name}_Key']  # Always include these
        
        try:
            # Get sample data to see what columns are available
            data = self.backend.get_combined_data()
            if data is not None and not data.empty:
                # Add all DB1_ and DB2_ columns from actual data
                for col in data.columns:
                    if col.startswith('DB1_') or col.startswith('DB2_'):
                        columns.append(col)
            else:
                # Fallback: add common expected columns
                common_db1_fields = ['Internal ID', 'Name', 'Purchase Price', 'Weight', 'Available', 'Base Price']
                common_db2_fields = ['ID', 'Title', 'Variant Price', 'Variant Cost', 'Status', 'Published']
                
                for field in common_db1_fields:
                    columns.append(f'DB1_{field}')
                for field in common_db2_fields:
                    columns.append(f'DB2_{field}')
                
        except Exception as e:
            pass
        
        return columns
    
    def get_default_visible_columns(self):
        """Get default visible columns for the normalized database structure."""
        # By default, only show the required columns - users can add mapped fields via column config
        return ['Select', 'NormalizedKey']
    
    def open_column_visibility_popup(self):
        """Open popup window for configuring column visibility."""
        popup = tk.Toplevel(self.parent)
        popup.title("Configure Column Visibility")
        popup.geometry("800x700")  # Wider to accommodate content better
        popup.resizable(True, True)
        popup.transient(self.parent.winfo_toplevel())
        popup.grab_set()
        
        # Main frame with padding
        main_frame = ttk.Frame(popup, padding=15)
        main_frame.pack(fill='both', expand=True)
        
        # Instructions
        ttk.Label(main_frame, text="Select which columns to show in the table:",
                 font=('TkDefaultFont', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Note about always visible columns
        ttk.Label(main_frame, text="Note: Select and NormalizedKey columns are always visible",
                 font=('TkDefaultFont', 8), foreground='gray').pack(anchor='w', pady=(0, 15))
        
        # Create a frame for the scrollable content
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Create canvas and scrollbar for scrolling
        canvas = tk.Canvas(content_frame, bg='white')
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure scrolling
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        scrollable_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<MouseWheel>", on_mousewheel)
        popup.bind("<MouseWheel>", on_mousewheel)  # Also bind to popup window
        
        # Create window in canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Configure canvas scrolling
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Configure canvas window width to match canvas
        def configure_canvas_window(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", configure_canvas_window)
        
        # Create organized column categories in the scrollable frame
        self.create_column_categories(scrollable_frame)
        
        # Buttons frame - fixed at bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        # Quick action buttons
        ttk.Button(button_frame, text="Show All", command=lambda: self.set_all_columns(True)).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="Hide All", command=lambda: self.set_all_columns(False)).pack(side='left')
        
        # Dialog buttons
        ttk.Button(button_frame, text="Cancel", command=popup.destroy).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Apply", command=lambda: self.apply_column_changes(popup)).pack(side='right')
        
        # Focus and update scroll region after everything is created
        popup.focus_set()
        popup.after(100, lambda: canvas.configure(scrollregion=canvas.bbox("all")))
    
    def create_column_categories(self, parent):
        """Create column categories with mapped fields at top and grouped display."""
        # Get all available columns from the actual data
        all_available_columns = []
        try:
            data = self.backend.get_combined_data()
            if data is not None:
                all_available_columns = [col for col in data.columns if col in self.column_vars]
        except Exception as e:
            print(f"Error getting columns: {e}")
        
        if not all_available_columns:
            ttk.Label(parent, text="No additional columns available").pack()
            return
        
        # Get mapped field pairs from field mappings configuration
        mapped_field_pairs = []
        try:
            field_mappings = self.backend.get_field_mappings()
            if isinstance(field_mappings, dict):
                if 'field_mappings' in field_mappings:
                    mappings = field_mappings['field_mappings']
                else:
                    mappings = field_mappings
                
                # Add configured mapped fields (but NOT the DB keys - they'll be individual)
                for mapping_name, mapping_config in mappings.items():
                    if isinstance(mapping_config, dict):
                        ns_field = mapping_config.get('db1_field', mapping_config.get('netsuite_field', ''))
                        sf_field = mapping_config.get('db2_field', mapping_config.get('shopify_field', ''))
                        if ns_field and sf_field:
                            db1_col = f'{self.db1_name}_{ns_field}'
                            db2_col = f'{self.db2_name}_{sf_field}'
                            
                            # Check if columns exist in data, if not try to find similar columns
                            db1_found = db1_col in all_available_columns
                            db2_found = db2_col in all_available_columns
                            
                            # If exact match not found, try to find columns that end with the field name
                            if not db1_found:
                                for col in all_available_columns:
                                    if col.endswith(ns_field) and ('netsuite' in col.lower() or self.db1_name.lower() in col.lower()):
                                        db1_col = col
                                        db1_found = True
                                        break
                            
                            if not db2_found:
                                for col in all_available_columns:
                                    if col.endswith(sf_field) and ('shopify' in col.lower() or self.db2_name.lower() in col.lower()):
                                        db2_col = col
                                        db2_found = True
                                        break
                            
                            if db1_found and db2_found:
                                mapped_field_pairs.append({
                                    'name': mapping_name,
                                    'db1_field': db1_col,
                                    'db2_field': db2_col,
                                    'description': f'{ns_field} ↔ {sf_field}'
                                })
        except Exception as e:
            print(f"Error loading mapped fields: {e}")
        
        # 1. MAPPED FIELDS SECTION (at the top)
        if mapped_field_pairs:
            mapped_frame = ttk.LabelFrame(parent, text=f"Mapped Fields ({len(mapped_field_pairs)} pairs)", padding=10)
            mapped_frame.pack(fill='x', pady=(0, 10))
            
            for pair in mapped_field_pairs:
                pair_frame = ttk.Frame(mapped_frame)
                pair_frame.pack(fill='x', pady=2)
                
                # Create a single checkbox that controls both fields
                pair_var = tk.BooleanVar()
                
                # Set initial state based on whether both fields are currently visible
                db1_visible = self.column_vars[pair['db1_field']].get()
                db2_visible = self.column_vars[pair['db2_field']].get()
                pair_var.set(db1_visible and db2_visible)
                
                def toggle_pair(pair_info=pair, var=pair_var):
                    """Toggle both fields in the pair together."""
                    state = var.get()
                    self.column_vars[pair_info['db1_field']].set(state)
                    self.column_vars[pair_info['db2_field']].set(state)
                
                pair_var.trace('w', lambda *args, pair_info=pair, var=pair_var: toggle_pair(pair_info, var))
                
                checkbox = ttk.Checkbutton(
                    pair_frame,
                    text=f"{pair['name']} - {pair['description']}",
                    variable=pair_var
                )
                checkbox.pack(anchor='w')
        
        # 2. INDIVIDUAL FIELDS SECTIONS
        # Categorize remaining columns (excluding those in mapped pairs)
        mapped_columns = set()
        for pair in mapped_field_pairs:
            mapped_columns.add(pair['db1_field'])
            mapped_columns.add(pair['db2_field'])
        
        categories = {
            'Key Fields': [],
            f'{self.db1_name} Fields': [],
            f'{self.db2_name} Fields': []
        }
        
        # Categorize all available columns (excluding those in mapped pairs)
        for col in all_available_columns:
            if col in mapped_columns:
                continue  # Skip mapped fields as they're handled above
            elif col in ['NormalizedKey', f'{self.db1_name}_Key', f'{self.db2_name}_Key']:
                categories['Key Fields'].append(col)
            elif col.startswith(f'{self.db1_name}_'):
                categories[f'{self.db1_name} Fields'].append(col)
            elif col.startswith(f'{self.db2_name}_'):
                categories[f'{self.db2_name} Fields'].append(col)
        
        # Create sections for each category
        for category_name, column_list in categories.items():
            if column_list:  # Only show categories with available columns
                category_frame = ttk.LabelFrame(parent, text=f"{category_name} ({len(column_list)} fields)", padding=10)
                category_frame.pack(fill='x', pady=(0, 10))
                
                # Create checkboxes for this category in a more compact layout
                for col in sorted(column_list):  # Sort alphabetically for easier finding
                    friendly_name = self.get_friendly_name(col)
                    checkbox = ttk.Checkbutton(
                        category_frame,
                        text=friendly_name,
                        variable=self.column_vars[col]
                    )
                    checkbox.pack(anchor='w', pady=1)  # Reduced padding for more compact layout
    
    def get_friendly_name(self, column_name):
        """Generate a friendly display name for a column."""
        # Handle special key fields
        if column_name == 'NormalizedKey':
            return "Normalized Key"
        elif column_name == f'{self.db1_name}_Key':
            return f"{self.db1_name} Key ({self.db1_name}_Key)"
        elif column_name == f'{self.db2_name}_Key':
            return f"{self.db2_name} Key ({self.db2_name}_Key)"
        
        # Remove the database prefix and add system identifier
        if column_name.startswith(f'{self.db1_name}_'):
            base_name = column_name[len(f'{self.db1_name}_'):]
            system = f"({self.db1_name})"
        elif column_name.startswith(f'{self.db2_name}_'):
            base_name = column_name[len(f'{self.db2_name}_'):]
            system = f"({self.db2_name})"
        elif column_name.startswith(('ns_', 'sf_')):
            # Handle legacy prefixes if any remain
            base_name = column_name[3:]
            system = "(Legacy)"
        else:
            base_name = column_name
            system = ""
        
        # Handle metafields specially
        if 'Metafield:' in base_name:
            # Extract the metafield name
            if '[' in base_name:
                name_part = base_name.split('[')[0].replace('Metafield: ', '').replace('Variant Metafield: ', '')
                type_part = base_name.split('[')[1].replace(']', '')
                return f"{name_part} ({type_part}) {system}"
            else:
                clean_name = base_name.replace('Metafield: ', '').replace('Variant Metafield: ', '')
                return f"{clean_name} {system}"
        
        # Default: return the base name with system identifier
        return f"{base_name} {system}" if system else base_name
    
    def set_all_columns(self, visible):
        """Set all columns to visible or hidden."""
        for var in self.column_vars.values():
            var.set(visible)
    
    def apply_column_changes(self, popup):
        """Apply column visibility changes and close popup."""
        # Show status during update
        self.update_status("Updating column visibility...")
        
        # Update visibility
        self.update_column_visibility()
        
        # Re-apply filters so Hide Sync'd Data uses the newly visible columns
        self.apply_filters()
        
        # Close popup
        popup.destroy()
        
        # Update status
        visible_count = len([col for col, var in self.column_vars.items() if var.get()]) + 2  # +2 for Select and NormalizedKey
        self.update_status(f"Showing {visible_count} columns")
    
    def update_column_visibility(self):
        """Update which columns are visible in the table."""
        visible_columns = ['Select', 'NormalizedKey']  # Always show these
        
        for col, var in self.column_vars.items():
            if var.get():
                visible_columns.append(col)
        
        # Update the table view
        self.table_view.update_column_visibility(visible_columns)
    
    def refresh_data(self):
        """Refresh the data display."""
        self.update_status("Loading matched SKUs...")
        try:
            # Check if backend is ready
            if not hasattr(self.backend, 'get_combined_data'):
                self.update_status("Backend not ready yet...")
                # Schedule another attempt in 1 second
                self.parent.after(1000, self.refresh_data)
                return
            
            # Reset pagination and filters when refreshing
            self.current_page = 0
            self.filtered_data = None
            
            # Load data and apply current filters
            combined_data = self.backend.get_combined_data()
            if combined_data is not None:
                self.apply_filters()  # This will set filtered_data and call populate_table
                self.update_status(f"Matched SKUs loaded: {self.total_filtered_items} items")
            else:
                self.update_status("Waiting for data to load...")
                # Schedule another attempt in 1 second
                self.parent.after(1000, self.refresh_data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.update_status(f"Error refreshing data: {str(e)}")
            # Don't show error popup immediately, might just be timing issue
            # Schedule another attempt in 2 seconds
            self.parent.after(2000, self.refresh_data)
    
    def populate_table(self):
        """Populate the table view with current filtered and paginated data."""
        # Use filtered data if available, otherwise fall back to current_data
        source_data = self.filtered_data if self.filtered_data is not None else self.current_data
        
        if source_data is None or len(source_data) == 0:
            # Handle empty data - check if this is because there are no matched SKUs
            if self.backend.get_combined_data() is not None:
                total_records = len(self.backend.get_combined_data())
                if total_records > 0:
                    # There is data, but no matched SKUs
                    self.table_view.populate_table([])
                    self.item_counter_var.set(f"No matched SKUs found (Total records: {total_records})")
                    self.update_status("No SKUs exist in both databases. Check data quality or linking configuration.")
                else:
                    # No data at all
                    self.table_view.populate_table([])
                    self.item_counter_var.set("No data available")
                    self.update_status("No data loaded")
            else:
                # Backend data not available
                self.table_view.populate_table([])
                self.item_counter_var.set("No data available")
                self.update_status("No data loaded")
            self.update_pagination_controls()
            return
        
        # Apply pagination
        if self.items_per_page == float('inf'):
            # Show all items
            display_data = source_data
        else:
            # Show current page
            start_idx = self.current_page * self.items_per_page
            end_idx = start_idx + self.items_per_page
            display_data = source_data.iloc[start_idx:end_idx]
        
        # Show loading status for larger datasets
        if len(display_data) > 50:
            self.update_status(f"Loading page {self.current_page + 1}...")
        
        # Convert DataFrame to list of dictionaries for ColoredTableView
        data_list = []
        for i, (_, row) in enumerate(display_data.iterrows()):
            row_dict = row.to_dict()
            # Add Select column data using NormalizedKey instead of sku
            normalized_key = str(row_dict.get('NormalizedKey', ''))
            row_dict['Select'] = "✓" if normalized_key in self.selected_skus else ""
            data_list.append(row_dict)
        
        # Populate the table view
        self.table_view.populate_table(data_list)
        
        # Update pagination controls and counter
        self.update_pagination_controls()
    
    def on_table_selection_change(self, selected_rows):
        """Handle table selection changes."""
        # Use filtered data if available, otherwise fall back to current_data
        source_data = self.filtered_data if self.filtered_data is not None else self.current_data
        
        if source_data is None:
            return
        
        # Get currently displayed data (with pagination)
        if self.items_per_page == float('inf'):
            display_data = source_data
        else:
            start_idx = self.current_page * self.items_per_page
            end_idx = start_idx + self.items_per_page
            display_data = source_data.iloc[start_idx:end_idx]
        
        # Clear current selection for this page only
        # Note: We could maintain selections across pages, but for simplicity clearing per page
        current_page_skus = set()
        for row_idx in selected_rows:
            if row_idx < len(display_data):
                normalized_key = str(display_data.iloc[row_idx]['NormalizedKey'])
                current_page_skus.add(normalized_key)
        
        # Remove old selections from this page and add new ones
        if hasattr(self, '_current_page_skus'):
            self.selected_skus -= self._current_page_skus
        self.selected_skus.update(current_page_skus)
        self._current_page_skus = current_page_skus
        
        self.update_selection_display()
    
    def on_tree_click(self, event):
        """Handle tree click events (deprecated - using ColoredTableView now)."""
        pass
    
    def on_tree_double_click(self, event):
        """Handle tree double-click events (deprecated - using ColoredTableView now)."""
        pass
    
    def toggle_selection(self, sku):
        """Toggle selection status of a SKU (legacy method for compatibility)."""
        if sku in self.selected_skus:
            self.selected_skus.remove(sku)
        else:
            self.selected_skus.add(sku)
        
        self.update_selection_display()
        self.populate_table()  # Refresh display
    
    def select_all(self):
        """Select all visible records on current page."""
        # Use filtered data if available, otherwise fall back to current_data
        source_data = self.filtered_data if self.filtered_data is not None else self.current_data
        
        if source_data is None:
            return
        
        # Get currently displayed data (with pagination)
        if self.items_per_page == float('inf'):
            display_data = source_data
        else:
            start_idx = self.current_page * self.items_per_page
            end_idx = start_idx + self.items_per_page
            display_data = source_data.iloc[start_idx:end_idx]
        
        # Add all visible SKUs to selection
        for _, row in display_data.iterrows():
            normalized_key = str(row.get('NormalizedKey', ''))
            if normalized_key:
                self.selected_skus.add(normalized_key)
        
        # Update table view selection
        self.table_view.select_all_rows()
        self.update_selection_display()
        self.populate_table()  # Refresh to show selection
    
    def deselect_all(self):
        """Deselect all records (global, not just current page)."""
        self.selected_skus.clear()
        if hasattr(self, '_current_page_skus'):
            self._current_page_skus = set()
        
        # Update table view selection
        self.table_view.deselect_all_rows()
        self.update_selection_display()
        self.populate_table()  # Refresh to show deselection
    
    def update_selection_display(self):
        """Update the selection count display."""
        self.selected_count_var.set(f"Selected: {len(self.selected_skus)}")
    
    def sync_selected(self, target_system):
        """Sync selected records to target system with field selection."""
        if not self.selected_skus:
            messagebox.showwarning("No Selection", "Please select records to sync.")
            return
        
        # Get available fields for syncing
        available_fields = self.get_syncable_fields()
        if not available_fields:
            messagebox.showerror("No Fields", "No syncable fields found.")
            return
        
        # Show field selection dialog
        selected_fields = self.show_field_selection_dialog(target_system, available_fields)
        if not selected_fields:
            return  # User cancelled or no fields selected
        
        # Confirm sync operation
        direction = f"{self.db1_name} → {self.db2_name}" if target_system == "db2" else f"{self.db2_name} → {self.db1_name}"
        field_list = ", ".join(selected_fields)
        message = f"Sync {len(self.selected_skus)} items {direction}\nFields: {field_list}\n\nProceed?"
        
        if not messagebox.askyesno("Confirm Sync", message):
            return
        
        # Perform sync operation
        try:
            self.update_status(f"Syncing {len(self.selected_skus)} items to {target_system.title()}...")
            
            success_count = 0
            error_count = 0
            error_details = []
            
            # Get source and target data for field values
            source_data = self.filtered_data if self.filtered_data is not None else self.current_data
            if source_data is None:
                messagebox.showerror("Error", "No data available for sync")
                return
            
            for sku in self.selected_skus:
                try:
                    # Use original SKU format from data (don't clean it)
                    # Find the record for this SKU in the display data
                    sku_records = source_data[source_data['NormalizedKey'].astype(str) == str(sku)]
                    if sku_records.empty:
                        error_count += 1
                        error_details.append(f"SKU {sku}: Record not found")
                        continue
                    record = sku_records.iloc[0]

                    # Sync each selected field
                    field_success = True
                    for field_mapping in selected_fields:
                        # Get field info
                        field_info = next((f for f in available_fields if f['mapping_name'] == field_mapping), None)
                        if not field_info:
                            continue

                        try:
                            # Get the source value based on sync direction and dynamic DB names
                            if target_system == "db2":
                                # DB1 → DB2
                                db1_field = field_info.get('db1_field', field_info.get('netsuite_field', ''))
                                source_col = f"{self.db1_name}_{db1_field}"
                                source_value = record.get(source_col)
                            else:
                                # DB2 → DB1
                                db2_field = field_info.get('db2_field', field_info.get('shopify_field', ''))
                                source_col = f"{self.db2_name}_{db2_field}"
                                source_value = record.get(source_col)

                            # Skip if source value is NaN or empty
                            if pd.isna(source_value) or source_value == "" or str(source_value).lower() == "nan":
                                continue

                            # Update the record using backend method with original NormalizedKey
                            success, msg = self.backend.update_record(
                                link_value=str(sku),  # Use NormalizedKey
                                field=field_mapping,
                                value=source_value,
                                system=target_system
                            )

                            if not success:
                                field_success = False
                                error_details.append(f"SKU {sku}, Field {field_mapping}: {msg}")

                        except Exception as field_error:
                            field_success = False
                            error_details.append(f"SKU {sku}, Field {field_mapping}: {str(field_error)}")

                    if field_success:
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    error_count += 1
                    error_details.append(f"SKU {sku}: {str(e)}")
            
            # Save the updated data
            if success_count > 0:
                save_success, save_msg = self.backend.save_data()
                if not save_success:
                    messagebox.showerror("Save Error", f"Updates applied but failed to save: {save_msg}")
            
            # Show results
            if error_count == 0:
                messagebox.showinfo("Sync Complete", 
                                   f"Successfully synced {success_count} items to {target_system.title()}")
            else:
                # Show detailed error information
                error_summary = f"Synced {success_count} items successfully\n{error_count} items failed\n\n"
                if len(error_details) <= 10:
                    error_summary += "Errors:\n" + "\n".join(error_details)
                else:
                    error_summary += f"First 10 errors:\n" + "\n".join(error_details[:10])
                    error_summary += f"\n... and {len(error_details) - 10} more errors"
                
                messagebox.showwarning("Sync Complete with Errors", error_summary)
            
            # Refresh data to show changes
            self.refresh_data()
            
        except Exception as e:
            messagebox.showerror("Sync Error", f"Error during sync operation: {str(e)}")
        finally:
            self.update_status("Sync operation completed")
    
    def get_syncable_fields(self):
        """Get list of fields that can be synced between systems."""
        syncable_fields = []
        
        try:
            # Get field mappings to determine which fields can be synced
            field_mappings = self.backend.get_field_mappings()
            
            if isinstance(field_mappings, dict):
                mappings = field_mappings.get('field_mappings', field_mappings)
                for mapping_name, mapping_config in mappings.items():
                    if isinstance(mapping_config, dict):
                        ns_field = mapping_config.get('netsuite_field', '')
                        sf_field = mapping_config.get('shopify_field', '')
                        if ns_field and sf_field:
                            syncable_fields.append({
                                'display_name': mapping_name.replace('_', ' ').title(),
                                'netsuite_field': ns_field,
                                'shopify_field': sf_field,
                                'mapping_name': mapping_name
                            })
            
            # Add some common fields if mappings don't exist
            if not syncable_fields:
                common_fields = [
                    {'display_name': 'Weight', 'netsuite_field': 'Weight', 'shopify_field': 'Variant Weight', 'mapping_name': 'weight'},
                    {'display_name': 'Price', 'netsuite_field': 'Base Price', 'shopify_field': 'Variant Price', 'mapping_name': 'price'},
                    {'display_name': 'MPN', 'netsuite_field': 'MPN (c)', 'shopify_field': 'Variant Barcode', 'mapping_name': 'mpn'}
                ]
                syncable_fields.extend(common_fields)
        
        except Exception as e:
            print(f"Error getting syncable fields: {e}")
        
        return syncable_fields
    
    def show_field_selection_dialog(self, target_system, available_fields):
        """Show dialog for selecting which fields to sync."""
        dialog = tk.Toplevel(self.parent)
        dialog.title(f"Select Fields to Sync to {target_system.title()}")
        dialog.geometry("500x400")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+{}+{}".format(
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        selected_fields = []
        field_vars = {}
        
        # Header
        header_frame = ttk.Frame(dialog)
        header_frame.pack(fill='x', padx=20, pady=10)
        
        direction = "NetSuite → Shopify" if target_system == "shopify" else "Shopify → NetSuite"
        ttk.Label(header_frame, text=f"Sync Direction: {direction}", font=('Arial', 12, 'bold')).pack()
        ttk.Label(header_frame, text="Select which fields to sync:", font=('Arial', 10)).pack(pady=(5, 0))
        
        # Scrollable field list
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add checkboxes for each field
        for field in available_fields:
            field_var = tk.BooleanVar()
            field_vars[field['mapping_name']] = field_var
            
            field_frame = ttk.Frame(scrollable_frame)
            field_frame.pack(fill='x', pady=2)
            
            checkbox = ttk.Checkbutton(field_frame, text=field['display_name'], variable=field_var)
            checkbox.pack(side='left')
            
            # Show source → target mapping
            if target_system == "shopify":
                mapping_text = f"  ({field['netsuite_field']} → {field['shopify_field']})"
            else:
                mapping_text = f"  ({field['shopify_field']} → {field['netsuite_field']})"
            
            ttk.Label(field_frame, text=mapping_text, foreground='gray').pack(side='left')
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill='x', padx=20, pady=10)
        
        def on_select_all():
            for var in field_vars.values():
                var.set(True)
        
        def on_deselect_all():
            for var in field_vars.values():
                var.set(False)
        
        def on_ok():
            nonlocal selected_fields
            selected_fields = [mapping_name for mapping_name, var in field_vars.items() if var.get()]
            if not selected_fields:
                messagebox.showwarning("No Fields Selected", "Please select at least one field to sync.")
                return
            dialog.destroy()
        
        def on_cancel():
            nonlocal selected_fields
            selected_fields = []
            dialog.destroy()
        
        ttk.Button(button_frame, text="Select All", command=on_select_all).pack(side='left')
        ttk.Button(button_frame, text="Deselect All", command=on_deselect_all).pack(side='left', padx=(5, 0))
        
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side='right')
        ttk.Button(button_frame, text="OK", command=on_ok).pack(side='right', padx=(0, 5))
        
        # Wait for dialog to close
        dialog.wait_window()
        
        return selected_fields
    
    def export_selection(self):
        """Export selected records."""
        if not self.selected_skus:
            messagebox.showwarning("No Selection", "Please select records to export.")
            return
        
        # Filter data for selected SKUs
        if self.current_data is not None:
            selected_data = self.current_data[self.current_data['sku'].astype(str).isin(self.selected_skus)]
            
            # Save to temporary dataframe and export
            try:
                export_filename = f"bulk_export_selection_{len(self.selected_skus)}_records"
                # We'll need to temporarily set the backend's combined_data to our selection
                original_data = self.backend.combined_data
                self.backend.combined_data = selected_data
                
                success, message = self.backend.export_data('csv', export_filename)
                
                # Restore original data
                self.backend.combined_data = original_data
                
                if success:
                    self.update_status(message)
                    messagebox.showinfo("Export Complete", message)
                else:
                    messagebox.showerror("Export Failed", f"Failed to export: {message}")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Error exporting data: {str(e)}")
    
    def on_search_changed(self, *args):
        """Handle search text changes with debouncing."""
        # Cancel any pending search
        if hasattr(self, '_search_timer'):
            self.parent.after_cancel(self._search_timer)
        
        # Schedule search after brief delay to avoid excessive filtering
        self._search_timer = self.parent.after(300, self.apply_filters)  # 300ms delay
    
    def on_filter_changed(self, event=None):
        """Handle filter changes."""
        self.apply_filters()
    
    def on_show_changed(self, event=None):
        """Handle show limit changes."""
        show_value = self.show_var.get()
        if show_value == "All":
            self.items_per_page = float('inf')
        else:
            self.items_per_page = int(show_value)
        
        # Reset to first page and refresh
        self.current_page = 0
        self.populate_table()
    
    def apply_filters(self):
        """Apply search and filter criteria."""
        if self.backend.get_combined_data() is None:
            return
        
        # Start with all data
        filtered_data = self.backend.get_combined_data().copy()
        
        # Filter to show only matched records (items that exist in both databases)
        # With the fixed merge logic, matched items will have both key columns populated
        db1_key_col = f'{self.db1_name}_Key'
        db2_key_col = f'{self.db2_name}_Key'
        filtered_data = filtered_data[
            filtered_data[db1_key_col].notna() & filtered_data[db2_key_col].notna()
        ]
        
        # Apply search filter
        search_text = self.search_var.get().strip()
        if search_text:
            filtered_data = filtered_data[filtered_data['NormalizedKey'].astype(str).str.contains(search_text, case=False, na=False)]
        
        # Apply status filter (now only applies to matched items)
        status_filter = self.status_filter.get()
        if status_filter != "All Matched":
            # Find weight columns in the new structure using configured DB names
            db1_weight_cols = [col for col in filtered_data.columns if col.startswith(f'{self.db1_name}_') and 'Weight' in col]
            db2_weight_cols = [col for col in filtered_data.columns if col.startswith(f'{self.db2_name}_') and 'Weight' in col]
            
            if db1_weight_cols and db2_weight_cols:
                db1_weight_col = db1_weight_cols[0]  # Use first weight column found
                db2_weight_col = db2_weight_cols[0]  # Use first weight column found
                
                if status_filter == "NS Data Complete":
                    # Show matched items where NetSuite has more complete data
                    filtered_data = filtered_data[filtered_data[db1_weight_col].notna() & filtered_data[db2_weight_col].isna()]
                elif status_filter == "SF Data Complete":
                    # Show matched items where Shopify has more complete data  
                    filtered_data = filtered_data[filtered_data[db2_weight_col].notna() & filtered_data[db1_weight_col].isna()]
                elif status_filter == "Both Complete":
                    # Show matched items where both systems have weight data (fully populated)
                    filtered_data = filtered_data[filtered_data[db1_weight_col].notna() & filtered_data[db2_weight_col].notna()]
        
        # Apply hide synced data filter
        if self.hide_synced_data.get():
            # Hide rows where both NetSuite and Shopify have the same data
            filtered_data = self._filter_out_synced_data(filtered_data)
        
        # Store filtered data and reset pagination
        self.filtered_data = filtered_data
        self.total_filtered_items = len(filtered_data)
        self.current_page = 0
        
        # Update display
        self.populate_table()
        self.update_pagination_controls()
        
        # Update status
        total_records = len(self.backend.get_combined_data()) if self.backend.get_combined_data() is not None else 0
        self.update_status(f"Showing matched SKUs: {self.total_filtered_items} of {total_records} total records")

    def _normalize_text_series(self, s: pd.Series) -> pd.Series:
        """Normalize a series to trimmed lowercase strings with NaN/None treated as empty."""
        st = s.astype(str).str.strip()
        st = st.replace({"nan": "", "None": "", "NaN": ""})
        return st

    def _series_equal_with_tolerance(self, left: pd.Series, right: pd.Series) -> pd.Series:
        """Compare two series with numeric tolerance and text normalization; returns a boolean equality series."""
        # Try numeric comparison first
        lnum = pd.to_numeric(left, errors='coerce')
        rnum = pd.to_numeric(right, errors='coerce')
        num_mask = lnum.notna() & rnum.notna()
        num_equal = pd.Series(False, index=left.index)
        if num_mask.any():
            num_equal.loc[num_mask] = np.isclose(lnum[num_mask], rnum[num_mask], rtol=0, atol=1e-9)
        # Fallback to normalized string comparison for non-numerics
        text_mask = ~num_mask
        text_equal = pd.Series(False, index=left.index)
        if text_mask.any():
            ltxt = self._normalize_text_series(left[text_mask]).str.lower()
            rtxt = self._normalize_text_series(right[text_mask]).str.lower()
            text_equal.loc[text_mask] = ltxt.eq(rtxt)
        return num_equal | text_equal

    def _get_visible_comparable_pairs(self, data: pd.DataFrame) -> list:
        """Return list of (db1_col, db2_col) pairs that are visible and represent the same mapped field."""
        if not hasattr(self, 'table_view'):
            return []
        visible_columns = set(self.table_view.columns)
        prefix1 = f"{self.db1_name}_"
        prefix2 = f"{self.db2_name}_"

        # 1) Use configured mappings to pair columns even when base names differ
        pairs = []
        try:
            mappings = self.backend.get_field_mappings() or {}
            if isinstance(mappings, dict) and 'field_mappings' in mappings:
                mappings = mappings['field_mappings']
        except Exception:
            mappings = {}

        if isinstance(mappings, dict):
            for mp in mappings.values():
                if not isinstance(mp, dict):
                    continue
                ns_field = mp.get('netsuite_field', '')
                sf_field = mp.get('shopify_field', '')
                if not ns_field or not sf_field:
                    continue
                left_col = f"{self.db1_name}_{ns_field}"
                right_col = f"{self.db2_name}_{sf_field}"
                if (
                    left_col in data.columns and right_col in data.columns and
                    left_col in visible_columns and right_col in visible_columns
                ):
                    pairs.append((left_col, right_col))

        # 2) Additionally pair by base name when both sides share identical base
        visible_db1 = [c for c in visible_columns if c.startswith(prefix1)]
        visible_db2 = [c for c in visible_columns if c.startswith(prefix2)]
        base_db1 = {c[len(prefix1):]: c for c in visible_db1}
        base_db2 = {c[len(prefix2):]: c for c in visible_db2}
        for base, left_col in base_db1.items():
            if base in base_db2:
                right_col = base_db2[base]
                if left_col in data.columns and right_col in data.columns:
                    pair = (left_col, right_col)
                    if pair not in pairs:
                        pairs.append(pair)

        return pairs
    
    def clean_sku(self, value):
        """Clean SKU value for comparison (same logic as unmatched items page)."""
        if pd.isna(value) or value in ['', 'nan', 'None']:
            return None
        
        # Convert to string and strip whitespace
        sku = str(value).strip()
        
        # Remove .0 suffix from numeric strings
        if sku.endswith('.0') and sku[:-2].replace('.', '').isdigit():
            sku = sku[:-2]
        
        return sku if sku else None
    
    def _filter_out_synced_data(self, data):
        """Filter out rows where NetSuite and Shopify data is synchronized, based ONLY on visible columns."""
        pairs = self._get_visible_comparable_pairs(data)
        sync_conditions = []
        for left_col, right_col in pairs:
            left_missing = data[left_col].isna() | self._normalize_text_series(data[left_col]).eq("")
            right_missing = data[right_col].isna() | self._normalize_text_series(data[right_col]).eq("")
            equal = self._series_equal_with_tolerance(data[left_col], data[right_col])
            condition = left_missing | right_missing | (~equal)
            sync_conditions.append(condition)

        if not sync_conditions:
            # Nothing comparable is visible; don't filter out anything
            return data

        combined_condition = sync_conditions[0]
        for condition in sync_conditions[1:]:
            combined_condition = combined_condition | condition
        return data[combined_condition]
    
    def next_page(self):
        """Navigate to next page."""
        if self.filtered_data is None:
            return
            
        max_page = (self.total_filtered_items - 1) // self.items_per_page if self.items_per_page != float('inf') else 0
        if self.current_page < max_page:
            self.current_page += 1
            self.populate_table()
            self.update_pagination_controls()
    
    def previous_page(self):
        """Navigate to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self.populate_table()
            self.update_pagination_controls()
    
    def update_pagination_controls(self):
        """Update pagination button states and labels."""
        if self.filtered_data is None or self.items_per_page == float('inf'):
            # Disable pagination when showing all items
            self.prev_btn.config(state='disabled')
            self.next_btn.config(state='disabled')
            self.page_label_var.set("All items")
            return
        
        total_pages = max(1, (self.total_filtered_items + self.items_per_page - 1) // self.items_per_page)
        current_page_display = self.current_page + 1
        
        # Update button states
        self.prev_btn.config(state='normal' if self.current_page > 0 else 'disabled')
        self.next_btn.config(state='normal' if self.current_page < total_pages - 1 else 'disabled')
        
        # Update page label
        self.page_label_var.set(f"Page {current_page_display} of {total_pages}")
        
        # Update item counter
        start_item = (self.current_page * self.items_per_page) + 1
        end_item = min((self.current_page + 1) * self.items_per_page, self.total_filtered_items)
        
        if self.total_filtered_items == 0:
            self.item_counter_var.set("No items found")
        else:
            # Calculate detailed breakdown
            data_breakdown = self._get_data_breakdown()
            self.item_counter_var.set(f"Showing {start_item}-{end_item} of {self.total_filtered_items} items {data_breakdown}")
    
    def _get_data_breakdown(self):
        """Get breakdown of data sources for display."""
        if self.filtered_data is None:
            return ""
        
        # Since we're only showing matched items, all items have both NS and SF data
        # But we can still show breakdown of sync status or conflicts
        total_items = len(self.filtered_data)
        
        # For matched items, we can show if they have sync conflicts
        synced_count = 0
        conflict_count = 0
        
        # Determine sync status based on visible DB1_/DB2_ column pairs only
        try:
            df = self.filtered_data
            pairs = self._get_visible_comparable_pairs(df)
            if not pairs:
                return f"(Matched: {total_items})"

            # Not Synced if any visible pair is missing OR differs; Synced otherwise
            not_synced = pd.Series(False, index=df.index)
            for left_col, right_col in pairs:
                left_missing = df[left_col].isna() | self._normalize_text_series(df[left_col]).eq("")
                right_missing = df[right_col].isna() | self._normalize_text_series(df[right_col]).eq("")
                equal = self._series_equal_with_tolerance(df[left_col], df[right_col])
                not_synced = not_synced | left_missing | right_missing | (~equal)

            conflict_count = int(not_synced.sum())
            synced_count = int(total_items - conflict_count)
        except:
            # If we can't determine sync status, just show total matched items
            return f"(Matched: {total_items})"
        
        breakdown_parts = []
        if synced_count > 0:
            breakdown_parts.append(f"Synced: {synced_count}")
        if conflict_count > 0:
            breakdown_parts.append(f"Conflicts: {conflict_count}")
        
        if breakdown_parts:
            return f"({', '.join(breakdown_parts)})"
        return f"(Matched: {total_items})"

    def clear_search(self):
        """Clear search and filters."""
        self.search_var.set("")
        # Reset to the valid default option for this combobox
        self.status_filter.set("All Matched")
        if hasattr(self, 'weight_min_var'):
            self.weight_min_var.set("")
        if hasattr(self, 'weight_max_var'):
            self.weight_max_var.set("")
        self.apply_filters()
    
    def sort_by_column(self, column):
        """Sort data by selected column."""
        # This would implement column sorting
        pass
    
    def edit_individual_record(self, sku):
        """Individual editor has been deprecated - use bulk editor for all editing."""
        messagebox.showinfo("Feature Deprecated", f"Individual editing has been deprecated. Please use the bulk editor to edit SKU: {sku}")
    
    def on_tab_selected(self):
        """Called when this tab is selected."""
        self.refresh_data()
    
    def cleanup(self):
        """Cleanup background tasks and timers."""
        # Cancel any pending search timers
        if hasattr(self, '_search_timer'):
            try:
                self.parent.after_cancel(self._search_timer)
            except:
                pass
        
        # Clear any other pending after() callbacks that might reference this page
        print("BulkEditorPage: Cleanup completed")
