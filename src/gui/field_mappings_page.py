"""
Field Mappings Page
GUI page for managing field mappings between databases.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any
import os
from services.service_factory import ServiceFactory


class FieldMappingsPage:
    """Field mappings page for managing data field relationships."""

    def __init__(self, parent, backend, status_callback):
        self.parent = parent
        self.backend = backend
        self.update_status = status_callback

        # Get services
        self.config_service = ServiceFactory.create_configuration_service()

        # Get database names from backend
        if self.backend and hasattr(self.backend, 'get_database_names'):
            self.db1_name, self.db2_name = self.backend.get_database_names()
        else:
            self.db1_name, self.db2_name = "Database 1", "Database 2"

        # Current mappings
        self.current_mappings = {}
        self.available_fields = {'db1': [], 'db2': []}

        # Create main frame
        self.frame = ttk.Frame(parent)
        self.setup_interface()
    
    def setup_interface(self):
        """Setup the simplified field mappings interface for non-technical users."""
        # Create scrollable frame
        self.create_scrollable_frame()
        
        # Title
        title_label = ttk.Label(self.scrollable_frame, text="Database Configuration", font=('Arial', 16, 'bold'))
        title_label.pack(anchor='w', pady=(0, 20))
        
        # Data source configuration section
        self.create_data_source_section(self.scrollable_frame)
        
        # Database name configuration section
        self.create_database_name_section(self.scrollable_frame)
        
        # Simple explanation
        self.create_simple_info_section(self.scrollable_frame)
        
        # Linking field section
        self.create_linking_field_section(self.scrollable_frame)
        
        # Shared data fields section
        self.create_shared_fields_section(self.scrollable_frame)
        
        # Load initial data
        self.refresh_data()
    
    def create_scrollable_frame(self):
        """Create a scrollable frame for the field mappings page."""
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self.frame, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create window in canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True, padx=(15, 0), pady=15)
        self.scrollbar.pack(side="right", fill="y", padx=(0, 15), pady=15)
        
        # Bind mousewheel to scroll while pointer is over page; use bind_all during hover for reliability
        self.scrollable_frame.bind('<Enter>', lambda e: self._bind_mousewheel())
        self.scrollable_frame.bind('<Leave>', lambda e: self._unbind_mousewheel())
        
        # Bind canvas resize to adjust scrollable frame width
        self.canvas.bind("<Configure>", self._on_canvas_configure)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        if event.delta:
            # Windows
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            # Linux
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
    
    def _bind_mousewheel(self):
        """Bind mouse wheel globally while pointer is over the page."""
        try:
            self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
            self.canvas.bind_all('<Button-4>', self._on_mousewheel)
            self.canvas.bind_all('<Button-5>', self._on_mousewheel)
        except Exception:
            pass
    
    def _unbind_mousewheel(self):
        """Unbind global mouse wheel on leave."""
        try:
            self.canvas.unbind_all('<MouseWheel>')
            self.canvas.unbind_all('<Button-4>')
            self.canvas.unbind_all('<Button-5>')
        except Exception:
            pass
    
    def _on_canvas_configure(self, event):
        """Handle canvas resize to adjust scrollable frame width."""
        # Update the scrollable frame width to match canvas width
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def create_simple_info_section(self, parent):
        """Create simple explanation section."""
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill='x', pady=(0, 20))
        
        info_text = ("To sync data between your databases, we need to tell the system which fields contain the same information.\n"
                    "There are two types of connections we need to set up:")
        
        info_label = ttk.Label(info_frame, text=info_text, justify='left', wraplength=800, font=('Arial', 10))
        info_label.pack(anchor='w')
        
        # Two key concepts
        concepts_frame = ttk.Frame(info_frame)
        concepts_frame.pack(fill='x', pady=(10, 0))
        
        concept1 = ttk.Label(concepts_frame, text="1. Linking Field: The field that identifies the same item in both databases (like SKU or Product ID)", 
                           justify='left', wraplength=800, font=('Arial', 9))
        concept1.pack(anchor='w', pady=(5, 2))
        
        concept2 = ttk.Label(concepts_frame, text="2. Shared Data Fields: Fields that contain the same type of information (like Weight, Price, Name)", 
                           justify='left', wraplength=800, font=('Arial', 9))
        concept2.pack(anchor='w', pady=(2, 5))
    
    def create_data_source_section(self, parent):
        """Create data source file configuration section."""
        data_source_frame = ttk.LabelFrame(parent, text="Step 0: Select Data Files", padding=15)
        data_source_frame.pack(fill='x', pady=(0, 20))
        
        # Explanation
        source_info = ttk.Label(data_source_frame, 
                               text=f"First, select your {self.db1_name} and {self.db2_name} data files (Excel files recommended):",
                               font=('Arial', 10))
        source_info.pack(anchor='w', pady=(0, 15))
        
        # File selection grid
        files_frame = ttk.Frame(data_source_frame)
        files_frame.pack(fill='x')
        
        # Database 1 file
        db1_file_frame = ttk.Frame(files_frame)
        db1_file_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(db1_file_frame, text=f"{self.db1_name} Data File:", font=('Arial', 10, 'bold')).pack(anchor='w')
        
        db1_file_select_frame = ttk.Frame(db1_file_frame)
        db1_file_select_frame.pack(fill='x', pady=(5, 0))
        
        self.ns_file_var = tk.StringVar()
        self.ns_file_entry = ttk.Entry(db1_file_select_frame, textvariable=self.ns_file_var, state="readonly")
        self.ns_file_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        db1_browse_btn = ttk.Button(db1_file_select_frame, text="Browse...", 
                                  command=lambda: self.browse_file('db1'))
        db1_browse_btn.pack(side='right')
        
        # Database 2 file
        db2_file_frame = ttk.Frame(files_frame)
        db2_file_frame.pack(fill='x', pady=(0, 15))
        
        ttk.Label(db2_file_frame, text=f"{self.db2_name} Data File:", font=('Arial', 10, 'bold')).pack(anchor='w')
        
        db2_file_select_frame = ttk.Frame(db2_file_frame)
        db2_file_select_frame.pack(fill='x', pady=(5, 0))
        
        self.sf_file_var = tk.StringVar()
        self.sf_file_entry = ttk.Entry(db2_file_select_frame, textvariable=self.sf_file_var, state="readonly")
        self.sf_file_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        db2_browse_btn = ttk.Button(db2_file_select_frame, text="Browse...", 
                                  command=lambda: self.browse_file('db2'))
        db2_browse_btn.pack(side='right')
        
        # Save data sources button
        save_sources_btn = ttk.Button(files_frame, text="Save File Configuration", 
                                     command=self.save_data_sources, style="Accent.TButton")
        save_sources_btn.pack(pady=(10, 0))
    
    def create_database_name_section(self, parent):
        """Create database name configuration section."""
        db_name_frame = ttk.LabelFrame(parent, text="Step 0.5: Configure Database Names", padding=15)
        db_name_frame.pack(fill='x', pady=(0, 20))
        
        # Explanation
        name_info = ttk.Label(db_name_frame,
                             text="Customize the display names for your databases (optional):",
                             font=('Arial', 10))
        name_info.pack(anchor='w', pady=(0, 15))
        
        # Database names grid
        names_frame = ttk.Frame(db_name_frame)
        names_frame.pack(fill='x')
        
        # Database 1 name
        db1_frame = ttk.Frame(names_frame)
        db1_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(db1_frame, text="Database 1 Name:", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.db1_name_var = tk.StringVar(value=self.db1_name)
        self.db1_name_entry = ttk.Entry(db1_frame, textvariable=self.db1_name_var, width=30)
        self.db1_name_entry.pack(anchor='w', pady=(5, 0))
        
        # Database 2 name
        db2_frame = ttk.Frame(names_frame)
        db2_frame.pack(fill='x', pady=(0, 15))
        
        ttk.Label(db2_frame, text="Database 2 Name:", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.db2_name_var = tk.StringVar(value=self.db2_name)
        self.db2_name_entry = ttk.Entry(db2_frame, textvariable=self.db2_name_var, width=30)
        self.db2_name_entry.pack(anchor='w', pady=(5, 0))
        
        # Save database names button
        save_names_btn = ttk.Button(names_frame, text="Save Database Names", 
                                   command=self.save_database_names, style="Accent.TButton")
        save_names_btn.pack(pady=(10, 0))
    
    def create_linking_field_section(self, parent):
        """Create linking field configuration section."""
        linking_frame = ttk.LabelFrame(parent, text="Step 1: Set Up Linking Field", padding=15)
        linking_frame.pack(fill='x', pady=(0, 20))
        
        # Explanation
        link_info = ttk.Label(linking_frame, 
                             text="Choose the fields that contain the same unique identifier in both databases:",
                             font=('Arial', 10))
        link_info.pack(anchor='w', pady=(0, 15))
        
        # Linking fields setup
        link_setup_frame = ttk.Frame(linking_frame)
        link_setup_frame.pack(fill='x')
        
        # Database 1 side
        db1_frame = ttk.Frame(link_setup_frame)
        db1_frame.pack(side='left', fill='x', expand=True, padx=(0, 20))
        
        ttk.Label(db1_frame, text=f"{self.db1_name} Field:", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.ns_linking_var = tk.StringVar()
        self.ns_linking_combo = ttk.Combobox(db1_frame, textvariable=self.ns_linking_var, width=25, state="readonly")
        self.ns_linking_combo.pack(fill='x', pady=(5, 0))
        
        # Database 2 side
        db2_frame = ttk.Frame(link_setup_frame)
        db2_frame.pack(side='left', fill='x', expand=True)
        
        ttk.Label(db2_frame, text=f"{self.db2_name} Field:", font=('Arial', 10, 'bold')).pack(anchor='w')
        self.sf_linking_var = tk.StringVar()
        self.sf_linking_combo = ttk.Combobox(db2_frame, textvariable=self.sf_linking_var, width=25, state="readonly")
        self.sf_linking_combo.pack(fill='x', pady=(5, 0))
        
        # Save linking button
        save_link_frame = ttk.Frame(linking_frame)
        save_link_frame.pack(fill='x', pady=(15, 0))
        
        ttk.Button(save_link_frame, text="Save Linking Field", command=self.save_linking_field,
                  style='Accent.TButton').pack(side='left')
        
        # Current linking status
        self.linking_status_var = tk.StringVar()
        self.linking_status_label = ttk.Label(save_link_frame, textvariable=self.linking_status_var, 
                                             font=('Arial', 9), foreground='green')
        self.linking_status_label.pack(side='left', padx=(15, 0))
    
    def create_shared_fields_section(self, parent):
        """Create shared data fields configuration section."""
        shared_frame = ttk.LabelFrame(parent, text="Step 2: Set Up Shared Data Fields", padding=15)
        shared_frame.pack(fill='both', expand=True)
        
        # Explanation
        shared_info = ttk.Label(shared_frame, 
                               text="Connect fields that contain the same type of data in both databases:",
                               font=('Arial', 10))
        shared_info.pack(anchor='w', pady=(0, 15))
        
        # Add new mapping section
        add_mapping_frame = ttk.Frame(shared_frame)
        add_mapping_frame.pack(fill='x', pady=(0, 15))
        
        # Database 1 field
        ttk.Label(add_mapping_frame, text=f"{self.db1_name} Field:").grid(row=0, column=0, sticky='w', padx=(0, 5))
        self.ns_field_var = tk.StringVar()
        self.ns_field_combo = ttk.Combobox(add_mapping_frame, textvariable=self.ns_field_var, width=20, state="readonly")
        self.ns_field_combo.grid(row=0, column=1, padx=(0, 15))
        
        # Database 2 field
        ttk.Label(add_mapping_frame, text=f"{self.db2_name} Field:").grid(row=0, column=2, sticky='w', padx=(0, 5))
        self.sf_field_var = tk.StringVar()
        self.sf_field_combo = ttk.Combobox(add_mapping_frame, textvariable=self.sf_field_var, width=20, state="readonly")
        self.sf_field_combo.grid(row=0, column=3, padx=(0, 15))
        
        # Description
        ttk.Label(add_mapping_frame, text="Description:").grid(row=0, column=4, sticky='w', padx=(0, 5))
        self.mapping_desc_var = tk.StringVar()
        desc_entry = ttk.Entry(add_mapping_frame, textvariable=self.mapping_desc_var, width=25)
        desc_entry.grid(row=0, column=5, padx=(0, 15))
        
        # Add button
        ttk.Button(add_mapping_frame, text="Add Field Mapping", command=self.add_field_mapping).grid(row=0, column=6)
        
        # Current mappings list
        mappings_list_frame = ttk.Frame(shared_frame)
        mappings_list_frame.pack(fill='both', expand=True)
        
        ttk.Label(mappings_list_frame, text="Current Field Mappings:", font=('Arial', 10, 'bold')).pack(anchor='w', pady=(0, 10))
        
        # Simple mappings display
        columns = (f'{self.db1_name} Field', f'{self.db2_name} Field', 'Description')
        self.mappings_tree = ttk.Treeview(mappings_list_frame, columns=columns, show='headings', height=8)
        
        # Configure columns
        self.mappings_tree.heading(f'{self.db1_name} Field', text=f'{self.db1_name} Field')
        self.mappings_tree.heading(f'{self.db2_name} Field', text=f'{self.db2_name} Field')
        self.mappings_tree.heading('Description', text='Description')
        
        self.mappings_tree.column(f'{self.db1_name} Field', width=200, anchor='w')
        self.mappings_tree.column(f'{self.db2_name} Field', width=200, anchor='w')
        self.mappings_tree.column('Description', width=300, anchor='w')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(mappings_list_frame, orient='vertical', command=self.mappings_tree.yview)
        self.mappings_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.mappings_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Mapping controls
        controls_frame = ttk.Frame(shared_frame)
        controls_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(controls_frame, text="Remove Selected", command=self.remove_selected_mapping).pack(side='left', padx=(0, 10))
        ttk.Button(controls_frame, text="Clear All Mappings", command=self.clear_all_mappings).pack(side='left')
        
        # Status at bottom
        self.status_var = tk.StringVar()
        self.status_var.set("Loaded 0 field mappings")
        status_label = ttk.Label(shared_frame, textvariable=self.status_var, font=('Arial', 9))
        status_label.pack(anchor='w', pady=(15, 0))
    
    def save_linking_field(self):
        """Save the linking field configuration."""
        ns_field = self.ns_linking_var.get()
        sf_field = self.sf_linking_var.get()
        
        if not ns_field or not sf_field:
            messagebox.showwarning("Missing Fields", f"Please select both {self.db1_name} and {self.db2_name} linking fields.")
            return
        
        try:
            # Update the backend configuration
            success = self.backend.update_linking_field(ns_field, sf_field)
            if success:
                self.linking_status_var.set(f"✓ Linked: {ns_field} ↔ {sf_field}")
                self.update_status("Linking field saved successfully")
            else:
                messagebox.showerror("Error", "Failed to save linking field configuration.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save linking field: {str(e)}")
    
    def save_database_names(self):
        """Save the database names configuration."""
        db1_name = self.db1_name_var.get().strip()
        db2_name = self.db2_name_var.get().strip()

        if not db1_name or not db2_name:
            messagebox.showwarning("Missing Names", "Please provide names for both databases.")
            return

        try:
            # Save using configuration service
            success = self.config_service.save_database_names(db1_name, db2_name)
            if success:
                self.db1_name = db1_name
                self.db2_name = db2_name
                # Update all UI labels that use database names
                self.update_database_name_labels()
                self.update_status("Database names saved successfully")
                messagebox.showinfo("Success", "Database names updated successfully!")
            else:
                messagebox.showerror("Error", "Failed to save database names.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save database names: {str(e)}")
    
    def update_database_name_labels(self):
        """Update UI labels that display database names."""
        # This method can be expanded to update all labels that show database names
        # For now, a restart might be needed for full effect, but the core config is saved
        pass
    
    def add_field_mapping(self):
        """Add a new field mapping."""
        ns_field = self.ns_field_var.get()
        sf_field = self.sf_field_var.get()
        description = self.mapping_desc_var.get()
        
        if not ns_field or not sf_field:
            messagebox.showwarning("Missing Fields", f"Please select both {self.db1_name} and {self.db2_name} fields.")
            return
        
        if not description:
            description = f"Maps {ns_field} to {sf_field}"
        
        try:
            # Check if mapping already exists
            for item in self.mappings_tree.get_children():
                values = self.mappings_tree.item(item, 'values')
                if values[0] == ns_field and values[1] == sf_field:
                    messagebox.showwarning("Duplicate Mapping", "This field mapping already exists.")
                    return
            
            # Add to tree
            self.mappings_tree.insert('', 'end', values=(ns_field, sf_field, description))
            
            # Save to backend
            success = self.backend.add_field_mapping(ns_field, sf_field, description)
            if success:
                # Clear form
                self.ns_field_var.set('')
                self.sf_field_var.set('')
                self.mapping_desc_var.set('')
                
                # Update status
                count = len(self.mappings_tree.get_children())
                self.status_var.set(f"Loaded {count} field mappings")
                self.update_status(f"Added field mapping: {ns_field} → {sf_field}")
            else:
                messagebox.showerror("Error", "Failed to save field mapping.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add field mapping: {str(e)}")
    
    def remove_selected_mapping(self):
        """Remove the selected field mapping."""
        selected = self.mappings_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a field mapping to remove.")
            return
        
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to remove this field mapping?"):
            for item in selected:
                values = self.mappings_tree.item(item, 'values')
                ns_field, sf_field, description = values
                
                # Remove from tree
                self.mappings_tree.delete(item)
                
                # Remove from backend
                try:
                    self.backend.remove_field_mapping(ns_field, sf_field)
                    self.update_status(f"Removed field mapping: {ns_field} → {sf_field}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to remove mapping: {str(e)}")
            
            # Update status
            count = len(self.mappings_tree.get_children())
            self.status_var.set(f"Loaded {count} field mappings")
    
    def clear_all_mappings(self):
        """Clear all field mappings."""
        if not self.mappings_tree.get_children():
            messagebox.showinfo("No Mappings", "There are no field mappings to clear.")
            return
        
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to remove ALL field mappings?"):
            try:
                # Clear from backend
                self.backend.clear_all_field_mappings()
                
                # Clear from tree
                self.mappings_tree.delete(*self.mappings_tree.get_children())
                
                # Update status
                self.status_var.set("Loaded 0 field mappings")
                self.update_status("All field mappings cleared")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear mappings: {str(e)}")
    
    def refresh_data(self):
        """Refresh all data and populate interface."""
        try:
            # Load configured data sources first
            self.load_configured_data_sources()
            
            # Load database names
            self.load_database_names()
            
            # Load available fields from backend
            self.load_available_fields()
            
            # Load current linking configuration
            self.load_linking_configuration()
            
            # Load current field mappings
            self.load_field_mappings()
            
            self.update_status("Field mappings data refreshed")
            
        except Exception as e:
            self.update_status(f"Error refreshing data: {str(e)}")
    
    def load_available_fields(self):
        """Load available fields from both systems."""
        try:
            # Get fields from configuration service
            available_fields = self.config_service.get_available_fields(self.backend)

            # Populate comboboxes
            self.ns_linking_combo['values'] = available_fields.get('db1', [])
            self.ns_field_combo['values'] = available_fields.get('db1', [])

            self.sf_linking_combo['values'] = available_fields.get('db2', [])
            self.sf_field_combo['values'] = available_fields.get('db2', [])

        except Exception as e:
            # Fallback to empty lists
            self.ns_linking_combo['values'] = []
            self.ns_field_combo['values'] = []
            self.sf_linking_combo['values'] = []
            self.sf_field_combo['values'] = []
    
    def load_linking_configuration(self):
        """Load current linking field configuration."""
        try:
            linking_config = self.backend.get_linking_configuration()
            if linking_config and "primary_link" in linking_config:
                primary_link = linking_config["primary_link"]
                
                # Handle both old format (netsuite/shopify) and new format (db1/db2)
                db1_field = primary_link.get('db1', primary_link.get('netsuite', ''))
                db2_field = primary_link.get('db2', primary_link.get('shopify', ''))
                
                self.ns_linking_var.set(db1_field)
                self.sf_linking_var.set(db2_field)
                
                if db1_field and db2_field:
                    self.linking_status_var.set(f"✓ Linked: {db1_field} ↔ {db2_field}")
                else:
                    self.linking_status_var.set("No linking field configured")
            else:
                self.linking_status_var.set("No linking field configured")
                
        except Exception as e:
            self.linking_status_var.set("Error loading linking configuration")
    
    def load_database_names(self):
        """Load database names from configuration service."""
        try:
            # Get database names from configuration service
            self.db1_name, self.db2_name = self.config_service.load_database_names()

            # Update the UI variables
            if hasattr(self, 'db1_name_var'):
                self.db1_name_var.set(self.db1_name)
            if hasattr(self, 'db2_name_var'):
                self.db2_name_var.set(self.db2_name)

        except Exception as e:
            # Use defaults if loading fails
            self.db1_name = "Database 1"
            self.db2_name = "Database 2"
    
    def load_field_mappings(self):
        """Load current field mappings."""
        try:
            # Clear existing items
            self.mappings_tree.delete(*self.mappings_tree.get_children())
            
            # Get mappings from backend
            mappings = self.backend.get_field_mappings()
            
            # Populate tree - mappings is a dict, not a list
            if isinstance(mappings, dict):
                for field_name, mapping in mappings.items():
                    if isinstance(mapping, dict):
                        ns_field = mapping.get('db1_field', mapping.get('netsuite_field', field_name))
                        sf_field = mapping.get('db2_field', mapping.get('shopify_field', ''))
                        description = mapping.get('description', '')
                    else:
                        # Handle legacy format where mapping might be a string
                        ns_field = field_name
                        sf_field = str(mapping)
                        description = f"Maps {field_name} to {mapping}"
                    
                    self.mappings_tree.insert('', 'end', values=(ns_field, sf_field, description))
            
            # Update status
            count = len(mappings) if mappings else 0
            self.status_var.set(f"Loaded {count} field mappings")
            
        except Exception as e:
            self.status_var.set("Error loading field mappings")
    
    def browse_file(self, system_type):
        """Browse for data file."""
        try:
            # Set up file dialog
            title = f"Select {system_type.title()} Data File"
            filetypes = [
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
            
            # Open file dialog
            filename = filedialog.askopenfilename(
                title=title,
                filetypes=filetypes,
                initialdir=os.getcwd()
            )
            
            if filename:
                # Update the appropriate variable
                if system_type == 'db1':
                    self.ns_file_var.set(filename)
                elif system_type == 'db2':
                    self.sf_file_var.set(filename)
                
                self.update_status(f"Selected {system_type.title()} file: {os.path.basename(filename)}")
                
        except Exception as e:
            messagebox.showerror("File Selection Error", f"Error selecting file: {e}")
    
    def save_data_sources(self):
        """Save the selected data source files."""
        try:
            db1_file = self.ns_file_var.get().strip()
            db2_file = self.sf_file_var.get().strip()
            
            # Validate that both files are selected
            if not db1_file or not db2_file:
                messagebox.showwarning("Missing Files", f"Please select both {self.db1_name} and {self.db2_name} data files.")
                return
            
            # Validate that files exist
            if not os.path.exists(db1_file):
                messagebox.showerror("File Not Found", f"{self.db1_name} file not found: {db1_file}")
                return
                
            if not os.path.exists(db2_file):
                messagebox.showerror("File Not Found", f"{self.db2_name} file not found: {db2_file}")
                return
            
            # Configure data sources in backend
            if hasattr(self.backend, 'configure_data_sources'):
                success, message = self.backend.configure_data_sources(db1_file, db2_file)
                
                if success:
                    messagebox.showinfo("Success", "Data source files configured successfully!")
                    self.update_status("Data source files configured - ready to configure field mappings")
                    
                    # Refresh the data to load fields from the new files
                    self.refresh_data()
                else:
                    messagebox.showerror("Configuration Error", f"Failed to configure data sources: {message}")
            else:
                messagebox.showerror("Backend Error", "Backend does not support data source configuration.")
                
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving data sources: {e}")
    
    def load_configured_data_sources(self):
        """Load the currently configured data source files."""
        try:
            if hasattr(self.backend, 'get_configured_data_sources'):
                db1_file, db2_file = self.backend.get_configured_data_sources()
                
                # Update the UI with configured files
                if db1_file:
                    self.ns_file_var.set(db1_file)
                if db2_file:
                    self.sf_file_var.set(db2_file)
                    
        except Exception as e:
            pass
    
    # End of FieldMappingsPage class - now simplified for non-technical users
