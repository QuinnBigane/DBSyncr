"""
Colored Table View - Custom table widget supporting individual cell coloring
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional, Callable


class ColoredTableView:
    """Custom table widget that supports individual cell coloring."""
    
    def __init__(self, parent, columns: List[str], backend=None, on_selection_change: Optional[Callable] = None):
        self.parent = parent
        self.columns = columns
        self.all_available_columns = columns.copy()  # Track all possible columns
        self.backend = backend
        self.on_selection_change = on_selection_change
        self.selected_rows = set()
        self.field_mappings = {}
        
        # Get database names from backend
        if self.backend and hasattr(self.backend, 'get_database_names'):
            self.db1_name, self.db2_name = self.backend.get_database_names()
        else:
            self.db1_name, self.db2_name = "DB1", "DB2"
        
        # Data storage
        self.data = []
        self.cell_widgets = {}  # {(row, col): widget}
        self.header_widgets = {}  # {col: widget}
        self.group_header_widgets = []  # Track top-level merged group headers
        
        # Color definitions
        self.colors = {
            'red': '#ffcccc',      # Light red for mapped mismatched data
            'green': '#ccffcc',    # Light green for mapped matching data  
            'blue': '#ccccff',     # Light blue for unmapped data
            'white': '#ffffff',    # Default white
            'header': '#f0f0f0'    # Header background
        }
        
        self.setup_widgets()
    
    def setup_widgets(self):
        """Setup the table widgets."""
        # Main container with scrollbars
        self.main_frame = ttk.Frame(self.parent)
        
        # Canvas and scrollbars for scrolling
        self.canvas = tk.Canvas(self.main_frame, bg='white')
        
        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(self.main_frame, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(self.main_frame, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=h_scrollbar.set)
        
        # Scrollable frame inside canvas
        self.scrollable_frame = tk.Frame(self.canvas, bg='white')
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Grid layout
        self.canvas.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Bind canvas resize
        self.scrollable_frame.bind('<Configure>', self._on_frame_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Bind mouse wheel scrolling when pointer is over the table
        self.scrollable_frame.bind('<Enter>', lambda e: self._bind_mousewheel())
        self.scrollable_frame.bind('<Leave>', lambda e: self._unbind_mousewheel())
        
        # Also support Shift+Wheel for horizontal scroll
        self.scrollable_frame.bind('<Shift-MouseWheel>', self._on_shift_mousewheel)
        
        # Create headers
        self.create_headers()
    
    def _on_frame_configure(self, event=None):
        """Update canvas scroll region when frame size changes."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event=None):
        """Update frame width when canvas size changes."""
        canvas_width = self.canvas.winfo_width()
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    # ----- Scrolling helpers -----
    def _bind_mousewheel(self):
        """Bind mouse wheel events globally while pointer is over the widget."""
        try:
            self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
            self.canvas.bind_all('<Button-4>', self._on_mousewheel)  # Linux scroll up
            self.canvas.bind_all('<Button-5>', self._on_mousewheel)  # Linux scroll down
        except Exception:
            pass
    
    def _unbind_mousewheel(self):
        """Unbind global mouse wheel events when leaving the widget."""
        try:
            self.canvas.unbind_all('<MouseWheel>')
            self.canvas.unbind_all('<Button-4>')
            self.canvas.unbind_all('<Button-5>')
        except Exception:
            pass
    
    def _on_mousewheel(self, event):
        """Handle vertical scrolling for Windows and Linux."""
        if hasattr(event, 'delta') and event.delta:
            # Windows / macOS (delta is positive/negative multiples of 120)
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        else:
            # Linux events
            if getattr(event, 'num', None) == 4:
                self.canvas.yview_scroll(-1, 'units')
            elif getattr(event, 'num', None) == 5:
                self.canvas.yview_scroll(1, 'units')
    
    def _on_shift_mousewheel(self, event):
        """Scroll horizontally when Shift is held while scrolling the wheel."""
        if hasattr(event, 'delta') and event.delta:
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), 'units')
        else:
            if getattr(event, 'num', None) == 4:
                self.canvas.xview_scroll(-1, 'units')
            elif getattr(event, 'num', None) == 5:
                self.canvas.xview_scroll(1, 'units')
    
    def create_headers(self):
        """Create column headers with visual grouping for mapped fields."""
        # First, determine the column groupings
        column_groups = self._get_column_groups()
        
        # Create two-level headers: group headers and individual column headers
        current_col = 0
        
        for group_name, columns in column_groups:
            if len(columns) > 1 and group_name != "Other":
                # Create merged header for mapped fields
                group_header = tk.Label(
                    self.scrollable_frame,
                    text=group_name,
                    bg='#d9d9d9',  # Slightly darker than normal header
                    relief='raised',
                    borderwidth=2,
                    font=('Arial', 10, 'bold'),
                    anchor='center',
                    pady=3
                )
                group_header.grid(row=0, column=current_col, columnspan=len(columns), sticky='ew', padx=0, pady=(1,0))
                # Track for cleanup on header rebuild
                try:
                    self.group_header_widgets.append(group_header)
                except Exception:
                    pass
                
                # Create individual column headers under the group header
                for i, column in enumerate(columns):
                    # Determine border style for grouped columns
                    left_border = 3 if i == 0 else 1  # Bold left border for first column in group
                    right_border = 3 if i == len(columns) - 1 else 1  # Bold right border for last column in group
                    
                    header = tk.Label(
                        self.scrollable_frame,
                        text=column,
                        bg=self.colors['header'],
                        relief='solid',
                        borderwidth=1,
                        font=('Arial', 8, 'normal'),  # Normal weight for sub-headers
                        anchor='center',  # Center align sub-headers
                        padx=3,
                        pady=2
                    )
                    header.grid(row=1, column=current_col + i, sticky='ew', padx=0, pady=(0,1))
                    
                    # Apply custom border styling for grouping
                    if i == 0:  # First column in group
                        header.config(highlightbackground='#666666', highlightcolor='#666666', highlightthickness=2)
                    elif i == len(columns) - 1:  # Last column in group
                        header.config(highlightbackground='#666666', highlightcolor='#666666', highlightthickness=2)
                    
                    self.header_widgets[current_col + i] = header
                    
                    # Set column width
                    width = 50 if column.lower() == 'select' else 100
                    header.config(width=width//7)  # Slightly wider for better text fit
            else:
                # Single column (SKU or ungrouped fields) - spans both header rows
                for i, column in enumerate(columns):
                    header = tk.Label(
                        self.scrollable_frame,
                        text=column,
                        bg=self.colors['header'],
                        relief='raised',
                        borderwidth=2,
                        font=('Arial', 9, 'bold'),
                        anchor='center',  # Center align single headers too
                        padx=3,
                        pady=3
                    )
                    header.grid(row=0, column=current_col + i, rowspan=2, sticky='ew', padx=1, pady=1)
                    self.header_widgets[current_col + i] = header
                    
                    # Set column width
                    width = 50 if column.lower() == 'select' else 100
                    header.config(width=width//7)  # Match the grouped column width
            
            current_col += len(columns)
    
    def _get_column_groups(self) -> List[tuple]:
        """Get column groups for visual organization."""
        if not self.field_mappings:
            return [("Other", self.columns)]
        
        groups = []
        used_columns = set()
        
        # Always put Select first if it exists
        if 'Select' in self.columns:
            groups.append(("Select", ['Select']))
            used_columns.add('Select')
        
        # Ensure NormalizedKey is immediately after Select and before any optional columns
        if 'NormalizedKey' in self.columns:
            groups.append(("NormalizedKey", ['NormalizedKey']))
            used_columns.add('NormalizedKey')
        
        # Always put SKU second as its own group
        if 'sku' in self.columns:
            groups.append(("SKU", ['sku']))
            used_columns.add('sku')
        
        # Group mapped columns using exact matching
        mappings = self.field_mappings.get('field_mappings', {})
        for field_name, mapping in mappings.items():
            if field_name.lower() == 'sku':
                continue  # Already handled
                
            group_columns = self._find_exact_mapped_columns(field_name, mapping)
            # Filter to only include columns that are in current columns and not already used
            group_columns = [col for col in group_columns if col in self.columns and col not in used_columns]
            
            if group_columns:
                # Sort to put custom DB1 before DB2
                group_columns.sort(key=lambda x: (0 if x.startswith(f'{self.db1_name}_') else 1, x))
                groups.append((field_name.title(), group_columns))
                used_columns.update(group_columns)
        
        # Add remaining ungrouped columns
        ungrouped = [col for col in self.columns if col not in used_columns]
        if ungrouped:
            groups.append(("Other", ungrouped))
        
        return groups
    
    def _find_exact_mapped_columns(self, field_name: str, mapping: Dict[str, Any]) -> List[str]:
        """Find columns that exactly match a field mapping using the actual mapping configuration."""        
        mapped_columns = []
        
        # Get the database field names from the mapping (support both new and old formats)
        db1_field = mapping.get('db1_field', mapping.get('netsuite_field', ''))
        db2_field = mapping.get('db2_field', mapping.get('shopify_field', ''))
        
        if db1_field and db2_field:
            # Look for columns with custom database prefixes (new merged database structure)
            db1_column = f'{self.db1_name}_{db1_field}'
            db2_column = f'{self.db2_name}_{db2_field}'
            
            # Check if these columns exist in our available columns
            if db1_column in self.all_available_columns:
                mapped_columns.append(db1_column)
            if db2_column in self.all_available_columns:
                mapped_columns.append(db2_column)
        
        return mapped_columns
    
    def populate_table(self, data: List[Dict[str, Any]]):
        """Populate table with data and apply cell-level coloring."""
        # Store data
        self.data = data
        
        # Clear existing data rows (keep headers)
        for (row, col), widget in self.cell_widgets.items():
            widget.destroy()
        self.cell_widgets.clear()
        
        # Create a mapping from column name to visual column index based on how headers are positioned
        column_to_visual_index = self._get_column_to_visual_index_mapping()
        
        # Create data rows (start at row 2 due to two-level headers)
        for row_idx, row_data in enumerate(data, start=2):  # Start at 2 to skip both header rows
            data_row_idx = row_idx - 2  # Convert to 0-based data index
            for column in self.columns:
                # Get the correct visual column index for this column
                visual_col_idx = column_to_visual_index.get(column, 0)
                
                value = str(row_data.get(column, ''))
                
                # Format value for display (clean SKU formatting but keep original in data)
                display_value = self._format_display_value(column, value)
                
                # Determine cell color considering selection state
                cell_color = self._get_effective_cell_color(column, row_data, data_row_idx)
                
                # Create cell container frame for precise border control
                cell_frame = tk.Frame(
                    self.scrollable_frame,
                    bg=cell_color,
                    relief='solid',
                    borderwidth=1
                )
                cell_frame.grid(row=row_idx, column=visual_col_idx, sticky='nsew', padx=0, pady=0)
                
                # Add thick borders for mapped group boundaries
                if self._is_group_left_boundary(visual_col_idx):
                    # Add thick left border
                    left_border = tk.Frame(cell_frame, bg='#000000', width=3)
                    left_border.pack(side='left', fill='y')
                    
                if self._is_group_right_boundary(visual_col_idx):
                    # Add thick right border
                    right_border = tk.Frame(cell_frame, bg='#000000', width=3)
                    right_border.pack(side='right', fill='y')
                
                # Create the actual cell content
                if column == 'Select':
                    # Create checkbox for Select column
                    checkbox_var = tk.BooleanVar()
                    checkbox_var.set(data_row_idx in self.selected_rows)
                    
                    cell = tk.Checkbutton(
                        cell_frame,
                        variable=checkbox_var,
                        bg=cell_color,
                        activebackground=cell_color,
                        relief='flat',
                        borderwidth=0,
                        command=lambda r=row_idx: self._on_cell_click(r)
                    )
                    cell.pack(fill='both', expand=True)
                    
                    # Store both the frame and checkbox variable for later access
                    self.cell_widgets[(row_idx, visual_col_idx)] = cell_frame
                    if not hasattr(self, 'checkbox_vars'):
                        self.checkbox_vars = {}
                    self.checkbox_vars[data_row_idx] = checkbox_var
                else:
                    # Regular text cell
                    cell = tk.Label(
                        cell_frame,
                        text=display_value,  # Use formatted display value
                        bg=cell_color,
                        relief='flat',
                        borderwidth=0,
                        anchor='w',
                        padx=5,
                        font=('Arial', 9)
                    )
                    cell.pack(fill='both', expand=True)
                    
                    # Store widget reference
                    self.cell_widgets[(row_idx, visual_col_idx)] = cell_frame
                    
                    # Bind click events for selection (only for non-Select columns)
                    cell.bind('<Button-1>', lambda e, r=row_idx: self._on_cell_click(r))
                    cell_frame.bind('<Button-1>', lambda e, r=row_idx: self._on_cell_click(r))
                
                # Set column width
                if column.lower() == 'select':
                    width = 50
                else:
                    width = 100
                cell.config(width=width//7)  # Match header width
        
        # Update scroll region
        self._on_frame_configure()
    
    def _get_column_to_visual_index_mapping(self) -> Dict[str, int]:
        """Create mapping from column name to visual column index based on header layout."""
        column_groups = self._get_column_groups()
        mapping = {}
        current_col = 0
        
        for group_name, columns in column_groups:
            for i, column in enumerate(columns):
                mapping[column] = current_col + i
            current_col += len(columns)
        
        return mapping
    
    def _get_column_name_at_visual_index(self, visual_col_idx: int) -> Optional[str]:
        """Get the column name at a specific visual column index."""
        column_to_visual = self._get_column_to_visual_index_mapping()
        for column_name, visual_idx in column_to_visual.items():
            if visual_idx == visual_col_idx:
                return column_name
        return None
    
    def _is_group_left_boundary(self, visual_col_idx):
        """Check if this visual column index is the leftmost column of a mapped group."""
        # Get the column name at this visual position
        column_name = self._get_column_name_at_visual_index(visual_col_idx)
        if not column_name:
            return False
        
        # Check if this column is in a mapped group using exact mapping
        mapped_field_info = self.get_mapped_field_info(column_name)
        if not mapped_field_info:
            return False
        
        field_name, is_netsuite = mapped_field_info
        
        # Find all columns in this group that are visible and get their visual positions
        group_columns = []
        column_to_visual = self._get_column_to_visual_index_mapping()
        
        for col in self.columns:
            col_mapped_info = self.get_mapped_field_info(col)
            if col_mapped_info and col_mapped_info[0] == field_name:
                group_columns.append((col, column_to_visual.get(col, 0)))
        
        if len(group_columns) > 1:
            # Get the leftmost visual column in this group
            leftmost_visual_idx = min(group_columns, key=lambda x: x[1])[1]
            return visual_col_idx == leftmost_visual_idx
        
        return False
    
    def _is_group_right_boundary(self, visual_col_idx):
        """Check if this visual column index is the rightmost column of a mapped group."""
        # Get the column name at this visual position
        column_name = self._get_column_name_at_visual_index(visual_col_idx)
        if not column_name:
            return False
            
        # Check if this column is in a mapped group using exact mapping
        mapped_field_info = self.get_mapped_field_info(column_name)
        if not mapped_field_info:
            return False
        
        field_name, is_netsuite = mapped_field_info
        
        # Find all columns in this group that are visible and get their visual positions
        group_columns = []
        column_to_visual = self._get_column_to_visual_index_mapping()
        
        for col in self.columns:
            col_mapped_info = self.get_mapped_field_info(col)
            if col_mapped_info and col_mapped_info[0] == field_name:
                group_columns.append((col, column_to_visual.get(col, 0)))
        
        if len(group_columns) > 1:
            # Get the rightmost visual column in this group
            rightmost_visual_idx = max(group_columns, key=lambda x: x[1])[1]
            return visual_col_idx == rightmost_visual_idx
        
        return False

    def get_cell_color(self, column_name: str, row_data: Dict[str, Any]) -> str:
        """Determine the color for a specific cell based on mapping status."""
        # Select field should be transparent
        if column_name.lower() == 'select':
            return self.colors['white']  # Transparent/white background
        
        if not self.field_mappings:
            return self.colors['blue']  # No mappings = blue
        
        # SKU is special - check if any DISPLAYED and mapped fields have mismatches
        if column_name == 'sku':
            return self.get_sku_color(row_data)
        
        # Check if this column is part of a mapped field
        mapped_field_info = self.get_mapped_field_info(column_name)
        
        if not mapped_field_info:
            return self.colors['blue']  # Unmapped field = blue
        
        # This is a mapped field - check for mismatch
        field_name, is_netsuite = mapped_field_info
        mapping = self.field_mappings.get('field_mappings', {}).get(field_name, {})
        
        if self.has_field_mismatch(row_data, mapping):
            return self.colors['red']   # Mapped with mismatch = red
        else:
            return self.colors['green'] # Mapped with match = green
    
    def get_sku_color(self, row_data: Dict[str, Any]) -> str:
        """Get color for SKU field based on whether any DISPLAYED and mapped fields are out of sync."""
        if not self.field_mappings:
            return self.colors['green']
        
        # Check if any DISPLAYED and mapped fields have mismatches
        for field_name, mapping in self.field_mappings.get('field_mappings', {}).items():
            if field_name.lower() == 'sku':
                continue  # Skip SKU itself
            
            # Only consider fields that are both mapped AND currently displayed
            db1_col_displayed = False
            db2_col_displayed = False
            
            for displayed_col in self.columns:
                if displayed_col.lower() == 'select':
                    continue  # Skip select column
                    
                # Check if this displayed column matches a NetSuite or Shopify field for this mapping
                mapped_field_info = self.get_mapped_field_info(displayed_col)
                if mapped_field_info and mapped_field_info[0] == field_name:
                    if mapped_field_info[1]:  # NetSuite field
                        db1_col_displayed = True
                    else:  # Shopify field
                        db2_col_displayed = True
            
            # Only check for mismatch if BOTH sides of the mapping are displayed
            if db1_col_displayed and db2_col_displayed:
                if self.has_field_mismatch(row_data, mapping):
                    return self.colors['red']  # Any displayed mismatch = red
        
        return self.colors['green']  # All displayed matches = green
    
    def get_mapped_field_info(self, column_name: str) -> Optional[tuple]:
        """Check if a column is part of a mapped field and return field info."""
        if not self.field_mappings:
            return None
        
        # Check if this column matches any of the mapped fields
        mappings = self.field_mappings.get('field_mappings', {})
        for field_name, mapping in mappings.items():
            # Support both new and old field mapping formats
            db1_field = mapping.get('db1_field', mapping.get('netsuite_field', ''))
            db2_field = mapping.get('db2_field', mapping.get('shopify_field', ''))
            
            if db1_field and db2_field:
                db1_column = f'{self.db1_name}_{db1_field}'
                db2_column = f'{self.db2_name}_{db2_field}'
                
                if column_name == db1_column:
                    return (field_name, True)  # Database 1 field
                elif column_name == db2_column:
                    return (field_name, False)  # Database 2 field
        
        return None  # Not a mapped field
    
    def has_field_mismatch(self, row_data: Dict[str, Any], mapping: Dict[str, Any]) -> bool:
        """Check if a mapped field has mismatched values."""
        # Support both new and old field mapping formats
        db1_field = mapping.get('db1_field', mapping.get('netsuite_field', ''))
        db2_field = mapping.get('db2_field', mapping.get('shopify_field', ''))
        
        if not db1_field or not db2_field:
            return False
        
        # Build the expected column names with custom database prefix system
        db1_col = f'{self.db1_name}_{db1_field}'
        db2_col = f'{self.db2_name}_{db2_field}'
        
        # Compare values if both columns exist in the data
        if db1_col in row_data and db2_col in row_data:
            db1_value = str(row_data.get(db1_col, '')).strip()
            db2_value = str(row_data.get(db2_col, '')).strip()
            
            # Clean numeric formatting from values (remove .0 from integers)
            db1_value = self._clean_numeric_formatting(db1_value)
            db2_value = self._clean_numeric_formatting(db2_value)
            
            # Handle empty/nan values - if either is empty or "nan", consider it a mismatch
            # unless both are empty/nan
            db1_empty = not db1_value or db1_value.lower() in ['nan', 'none', '']
            db2_empty = not db2_value or db2_value.lower() in ['nan', 'none', '']
            
            if db1_empty and db2_empty:
                return False  # Both empty/nan = no mismatch
            elif db1_empty or db2_empty:
                return True   # One empty, one has value = mismatch
            
            # Both have values - compare them
            try:
                # Try numeric comparison first
                db1_num = float(db1_value)
                db2_num = float(db2_value)
                return abs(db1_num - db2_num) > 0.001  # Allow for small floating point differences
            except ValueError:
                # String comparison for non-numeric values (case-insensitive)
                return db1_value.lower() != db2_value.lower()
        
        return False  # If columns don't exist, no mismatch
    
    def _clean_numeric_formatting(self, value: str) -> str:
        """Clean numeric formatting like .0 suffixes from values for better comparison."""
        if not value or value.lower() in ['nan', 'none', '']:
            return value
        
        # If it's a number with .0 suffix, remove it
        if value.endswith('.0'):
            # Check if the part before .0 is all digits (or negative digits)
            base_part = value[:-2]
            if base_part.isdigit() or (base_part.startswith('-') and base_part[1:].isdigit()):
                return base_part
        
        return value
    
    def _on_cell_click(self, row_idx: int):
        """Handle cell click for row selection."""
        # Convert row_idx back to data index (subtract 2 for header rows)
        data_row_idx = row_idx - 2
        
        # Toggle row selection
        if data_row_idx in self.selected_rows:
            self.selected_rows.remove(data_row_idx)
        else:
            self.selected_rows.add(data_row_idx)
        
        # Update visual selection
        self._update_row_selection_display()
        
        # Notify parent of selection change
        if self.on_selection_change:
            self.on_selection_change(self.selected_rows)
    
    def _update_row_selection_display(self):
        """Update the visual display of selected rows."""
        # Update checkboxes if they exist
        if hasattr(self, 'checkbox_vars'):
            for data_row_idx, checkbox_var in self.checkbox_vars.items():
                checkbox_var.set(data_row_idx in self.selected_rows)
        
        # Update cell colors for affected rows only (more efficient than full refresh)
        self._update_selection_colors()
    
    def _update_selection_colors(self):
        """Update cell background colors to reflect selection state without full refresh."""
        if not hasattr(self, 'data') or not self.data:
            return
        
        # Only update cells that are currently visible
        for (row_idx, col_idx), widget in self.cell_widgets.items():
            # Skip header rows
            if row_idx < 2:
                continue
                
            data_row_idx = row_idx - 2
            if data_row_idx >= len(self.data):
                continue
                
            # Get the column name and row data
            visual_col_idx = 0
            column_name = None
            for col_name in self.columns:
                if visual_col_idx == col_idx:
                    column_name = col_name
                    break
                visual_col_idx += 1
            
            if column_name:
                row_data = self.data[data_row_idx]
                new_color = self._get_effective_cell_color(column_name, row_data, data_row_idx)
                
                # Update the widget's background color
                try:
                    if hasattr(widget, 'configure'):
                        widget.configure(bg=new_color)
                except tk.TclError:
                    pass  # Some widgets may not support bg option
                
                # For frames containing checkboxes, update all children
                for child in widget.winfo_children():
                    try:
                        if hasattr(child, 'configure'):
                            # Try to configure background and activebackground if supported
                            child.configure(bg=new_color)
                            # Only set activebackground for widgets that support it (like Checkbutton)
                            if isinstance(child, tk.Checkbutton):
                                child.configure(activebackground=new_color)
                    except tk.TclError:
                        pass  # Some widgets may not support these options
    
    def _format_display_value(self, column: str, value: str) -> str:
        """Format value for display while preserving original data."""
        if column == 'sku':
            # Clean numeric SKU formatting for display only
            if value.endswith('.0') and value[:-2].isdigit():
                return value[:-2]
        return value
    
    def _get_effective_cell_color(self, column: str, row_data: Dict[str, Any], data_row_idx: int) -> str:
        """Get cell color considering both mapping status and selection state."""
        base_color = self.get_cell_color(column, row_data)
        
        # If row is selected, darken the color to show selection
        if data_row_idx in self.selected_rows:
            if base_color == '#ffcccc':  # Red (mapped mismatch)
                return '#ffaaaa'  # Darker red
            elif base_color == '#ccffcc':  # Green (mapped match)
                return '#aaffaa'  # Darker green
            elif base_color == '#ccccff':  # Blue (unmapped)
                return '#aaaaff'  # Darker blue
            else:  # White or other
                return '#e0e0e0'  # Light gray for selection
        
        return base_color
    
    def update_columns(self, new_columns: List[str]):
        """Update the column structure."""
        self.columns = new_columns
        # Only update all_available_columns if the new set is larger or we don't have any yet
        if not hasattr(self, 'all_available_columns') or len(new_columns) > len(self.all_available_columns):
            self.all_available_columns = new_columns.copy()
        else:
            # Merge with existing available columns to preserve all known columns
            self.all_available_columns = list(set(self.all_available_columns) | set(new_columns))
        # Clear and recreate headers
        for widget in self.header_widgets.values():
            widget.destroy()
        self.header_widgets.clear()
        for widget in self.group_header_widgets:
            try:
                widget.destroy()
            except Exception:
                pass
        self.group_header_widgets = []
        
        self.create_headers()
        
        # Repopulate with current data
        if self.data:
            self.populate_table(self.data)
    
    def update_column_visibility(self, visible_columns: List[str]):
        """Update which columns are visible, ensuring SKU is always first."""
        # Update all_available_columns to include any new columns being requested
        self.all_available_columns = list(set(self.all_available_columns) | set(visible_columns))
        
        # Filter visible columns to only include columns that exist in our available set
        filtered_columns = [col for col in visible_columns if col in self.all_available_columns]
        # Ensure Select and NormalizedKey are first
        filtered_columns = self._ensure_select_and_normalized_key_first(filtered_columns)
        if filtered_columns != self.columns:
            self._update_visible_columns(filtered_columns)
    
    def _update_visible_columns(self, visible_columns: List[str]):
        """Update only the visible columns without changing the available column set."""
        self.columns = visible_columns
        
        # Clear and recreate headers
        for widget in self.header_widgets.values():
            widget.destroy()
        self.header_widgets.clear()
        for widget in self.group_header_widgets:
            try:
                widget.destroy()
            except Exception:
                pass
        self.group_header_widgets = []
        
        self.create_headers()
        
        # Repopulate with current data
        if self.data:
            self.populate_table(self.data)
    
    def set_field_mappings(self, field_mappings: Dict[str, Any]):
        """Set field mappings for coloring logic."""
        self.field_mappings = field_mappings
        # Recreate headers since column groupings may have changed
        self.create_headers()
        # Repopulate to update colors
        if self.data:
            self.populate_table(self.data)
    
    def get_frame(self):
        """Get the main frame widget."""
        return self.main_frame
    
    def select_all_rows(self):
        """Select all rows."""
        self.selected_rows = set(range(len(self.data)))  # Use 0-based indexing
        if self.on_selection_change:
            self.on_selection_change(self.selected_rows)
    
    def deselect_all_rows(self):
        """Deselect all rows."""
        self.selected_rows.clear()
        if self.on_selection_change:
            self.on_selection_change(self.selected_rows)
    
    def get_selected_data(self) -> List[Dict[str, Any]]:
        """Get data for selected rows."""
        selected_data = []
        for row_idx in self.selected_rows:
            if 0 <= row_idx < len(self.data):  # Use 0-based indexing for data array
                selected_data.append(self.data[row_idx])
        return selected_data

    # Additional methods to maintain compatibility with existing code
    def group_columns_by_mappings(self, columns: List[str]) -> List[str]:
        """Group columns so mapped fields appear together, with SKU always first."""
        if not self.field_mappings:
            # If no mappings, just filter out status columns but put SKU first
            filtered_columns = [col for col in columns if not self.is_status_column(col)]
            return self._ensure_select_and_sku_first(filtered_columns)
        
        grouped_columns = []
        used_columns = set()
        
        # Always put Select first if it exists
        if 'Select' in columns:
            grouped_columns.append('Select')
            used_columns.add('Select')
        
        # Always put SKU second if it exists
        if 'sku' in columns:
            grouped_columns.append('sku')
            used_columns.add('sku')
        
        # Then add all mapped column pairs (excluding SKU which is already added)
        mappings = self.field_mappings.get('field_mappings', {})
        mapped_groups = self.get_mapped_column_groups(columns, mappings)
        
        for group in mapped_groups:
            for col in group:
                if col in columns and col not in used_columns and col not in ['Select', 'sku']:
                    grouped_columns.append(col)
                    used_columns.add(col)
        
        # Then add remaining unmapped columns (excluding status columns)
        for col in columns:
            if col not in used_columns and not self.is_status_column(col):
                grouped_columns.append(col)
        
        return grouped_columns
    
    def _ensure_select_and_normalized_key_first(self, columns: List[str]) -> List[str]:
        """Ensure Select column is first, then NormalizedKey column."""
        result = []
        
        # Add Select first if it exists
        if 'Select' in columns:
            result.append('Select')
        
        # Add NormalizedKey second if it exists
        if 'NormalizedKey' in columns:
            result.append('NormalizedKey')
            
        # Add all other columns
        result.extend([col for col in columns if col not in ['Select', 'NormalizedKey']])
        return result
    
    def get_mapped_column_groups(self, columns: List[str], mappings: Dict[str, Any]) -> List[List[str]]:
        """Get groups of related columns based on field mappings."""
        groups = []
        
        for field_name, mapping in mappings.items():
            netsuite_field = mapping.get('netsuite_field', '')
            shopify_field = mapping.get('shopify_field', '')
            
            group_columns = []
            
            # Find NetSuite and Shopify columns for this mapping
            for col in columns:
                col_normalized = col.lower().replace('_', ' ').replace(f'{self.db1_name.lower()} ', '').replace(f'{self.db2_name.lower()} ', '')
                if col.startswith(f'{self.db1_name}_') and netsuite_field.lower() in col_normalized:
                    group_columns.append(col)
                elif col.startswith(f'{self.db2_name}_') and shopify_field.lower() in col_normalized:
                    group_columns.append(col)
            
            if group_columns:
                groups.append(sorted(group_columns))  # Sort to put custom DB1 before DB2
        
        return groups
    
    def is_status_column(self, column_name: str) -> bool:
        """Check if a column is a status column that should be filtered out."""
        status_keywords = ['status', 'sync', 'synced', 'unsynced']
        column_lower = column_name.lower()
        return any(keyword in column_lower for keyword in status_keywords)