"""
Error Page for DBSyncr

This page is displayed when critical configuration is missing.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging

class ErrorPage:
    """Error page to display when critical configuration is missing."""
    
    def __init__(self, parent, backend, error_type="primary_link_missing"):
        self.parent = parent
        self.backend = backend
        self.error_type = error_type
        self.logger = logging.getLogger('ErrorPage')
        
        # Create main frame
        self.main_frame = ttk.Frame(parent)
        
        # Setup interface
        self.setup_interface()
    
    def setup_interface(self):
        """Setup the error page interface."""
        # Title
        title_label = ttk.Label(
            self.main_frame,
            text="⚠️ Configuration Required",
            font=("Arial", 16, "bold"),
            foreground="red"
        )
        title_label.pack(pady=(20, 10))
        
        # Error message based on type
        if self.error_type == "primary_link_missing":
            self.setup_primary_link_error()
        else:
            self.setup_generic_error()
    
    def setup_primary_link_error(self):
        """Setup interface for primary link missing error."""
        # Main error message
        error_msg = ttk.Label(
            self.main_frame,
            text="Primary Link Field Not Configured",
            font=("Arial", 14, "bold")
        )
        error_msg.pack(pady=(0, 10))
        
        # Explanation
        explanation = ttk.Label(
            self.main_frame,
            text="The system needs a primary linking field to match records between\nthe two databases.",
            font=("Arial", 10),
            justify="center"
        )
        explanation.pack(pady=(0, 20))
        
        # Instructions
        instructions_frame = ttk.LabelFrame(self.main_frame, text="To Fix This Issue:", padding=20)
        instructions_frame.pack(pady=10, padx=20, fill="x")
        
        instructions = [
            "1. Go to the 'Field Mappings' tab",
            "2. Click 'Step 1: Configure Linking Field'",
            "3. Select matching fields between the databases",
            "4. Save your configuration",
            "5. Return to the Bulk Editor tab"
        ]
        
        for i, instruction in enumerate(instructions, 1):
            label = ttk.Label(
                instructions_frame,
                text=instruction,
                font=("Arial", 10)
            )
            label.pack(anchor="w", pady=2)
        
        # Button frame
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(pady=20)
        
        # Go to Field Mappings button
        goto_button = ttk.Button(
            button_frame,
            text="Go to Field Mappings",
            command=self.go_to_field_mappings,
            style="Accent.TButton"
        )
        goto_button.pack(side="left", padx=10)
        
        # Refresh button
        refresh_button = ttk.Button(
            button_frame,
            text="Check Again",
            command=self.check_configuration
        )
        refresh_button.pack(side="left", padx=10)
    
    def setup_generic_error(self):
        """Setup interface for generic errors."""
        error_msg = ttk.Label(
            self.main_frame,
            text="Configuration Error",
            font=("Arial", 14, "bold")
        )
        error_msg.pack(pady=(0, 10))
        
        explanation = ttk.Label(
            self.main_frame,
            text="There is a configuration issue that needs to be resolved.",
            font=("Arial", 10)
        )
        explanation.pack(pady=(0, 20))
    
    def go_to_field_mappings(self):
        """Navigate to the Field Mappings tab."""
        try:
            # Get the notebook from the parent
            notebook = self.parent.master
            if hasattr(notebook, 'select'):
                # Find the Field Mappings tab
                for i in range(notebook.index("end")):
                    tab_text = notebook.tab(i, "text")
                    if "Field Mappings" in tab_text:
                        notebook.select(i)
                        break
        except Exception as e:
            self.logger.error(f"Error navigating to Field Mappings: {e}")
            messagebox.showerror("Navigation Error", "Could not navigate to Field Mappings tab.")
    
    def check_configuration(self):
        """Check if configuration is now valid."""
        try:
            # Reload mappings from backend
            self.backend.load_mappings()
            
            # Check if primary link is now configured
            if self.backend.is_primary_link_configured():
                messagebox.showinfo("Success", "Primary link is now configured! You can return to the Bulk Editor.")
                # Trigger a refresh of the main application
                if hasattr(self.parent, 'master') and hasattr(self.parent.master, 'refresh_all_pages'):
                    self.parent.master.refresh_all_pages()
            else:
                messagebox.showwarning("Still Missing", "Primary link field is still not configured. Please set it up in Field Mappings.")
        except Exception as e:
            self.logger.error(f"Error checking configuration: {e}")
            messagebox.showerror("Error", "Could not check configuration status.")
    
    def pack(self, **kwargs):
        """Pack the main frame."""
        self.main_frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        """Grid the main frame."""
        self.main_frame.grid(**kwargs)
