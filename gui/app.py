"""
DBSyncr GUI Application
Main tkinter application class that manages the main loop and page navigation.
Thread-safe version with graceful shutdown support.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from backend_wrapper import DataBackend


class DBSyncrGUI:
    """Main GUI application class with threading support."""
    
    def __init__(self, backend=None, on_close_callback=None):
        self.root = tk.Tk()
        self.backend = backend if backend is not None else DataBackend()
        self.on_close_callback = on_close_callback
        
        # Threading attributes
        self.is_shutting_down = False
        self.shutdown_lock = threading.Lock()
        
        # Page containers
        self.pages = {}
        self.current_page = None
        
        self.setup_main_window()
        self.setup_menu()
        self.setup_main_interface()
        
        # Only initialize data if we created our own backend instance
        if backend is None:
            self.initialize_data()
        else:
            # Backend is already initialized, just load pages
            self.load_pages()
            self.update_status("Backend already initialized")
    
    def setup_main_window(self):
        """Configure the main window."""
        self.root.title("DBSyncr")
        self.root.geometry("1400x800")
        self.root.minsize(800, 600)
        
        # Center window on screen
        self.root.eval('tk::PlaceWindow . center')
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')  # Use a modern theme
        
        # Configure protocol for window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_menu(self):
        """Setup the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Reload Data", command=self.reload_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh Pages", command=self.refresh_pages)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def setup_main_interface(self):
        """Setup the main interface with tabs."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Starting application...")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief='sunken', anchor='w')
        status_bar.pack(fill='x', side='bottom', pady=(5, 0))
        
        # Create initial placeholder tabs
        self.create_placeholder_tabs()
    
    def create_placeholder_tabs(self):
        """Create placeholder tabs while loading."""
        # Bulk Editor tab
        bulk_frame = ttk.Frame(self.notebook)
        self.notebook.add(bulk_frame, text="Bulk Editor")
        ttk.Label(bulk_frame, text="Bulk Editor - Loading...", font=('Arial', 12)).pack(expand=True)
        
        # Field Mappings tab
        mappings_frame = ttk.Frame(self.notebook)
        self.notebook.add(mappings_frame, text="Field Mappings")
        ttk.Label(mappings_frame, text="Field Mappings - Loading...", font=('Arial', 12)).pack(expand=True)
    
    def load_pages(self):
        """Load and create page instances."""
        try:
            # Import page classes
            from gui.bulk_editor_page import BulkEditorPage
            from gui.field_mappings_page import FieldMappingsPage
            from gui.unmatched_items_page import UnmatchedItemsPage
            from gui.error_page import ErrorPage
            
            # Clear existing tabs
            for tab in self.notebook.tabs():
                self.notebook.forget(tab)
            
            # Check if primary link is configured
            if hasattr(self.backend, 'is_primary_link_configured') and not self.backend.is_primary_link_configured():
                # Create error page instead of bulk editor
                self.pages['error'] = ErrorPage(self.notebook, self.backend, "primary_link_missing")
                self.notebook.add(self.pages['error'].main_frame, text="⚠️ Configuration Required")
            else:
                self.pages['bulk_editor'] = BulkEditorPage(self.notebook, self.backend, self.update_status)
                self.notebook.add(self.pages['bulk_editor'].frame, text="Bulk Editor")
            
            self.pages['field_mappings'] = FieldMappingsPage(self.notebook, self.backend, self.update_status)
            self.pages['unmatched_items'] = UnmatchedItemsPage(self.notebook, self.backend, self.update_status)
            
            # Add remaining pages to notebook
            self.notebook.add(self.pages['field_mappings'].frame, text="Field Mappings")
            self.notebook.add(self.pages['unmatched_items'].frame, text="📊 Unmatched Items")
            
            self.update_status("Pages loaded successfully")
            
        except ImportError as e:
            self.update_status(f"Warning: Could not load page classes: {e}")
            messagebox.showwarning("Import Warning", 
                                   f"Some page classes could not be loaded: {e}\\n\\n"
                                   "The application will continue with basic functionality.")
        except Exception as e:
            import traceback
            traceback.print_exc()
    
    def initialize_data(self):
        """Initialize the backend data."""
        try:
            success, message = self.backend.load_data()
            
            # Always load pages regardless of data loading result
            self.load_pages()
            
            if success:
                self.update_status("Data loaded successfully")
            else:
                self.update_status(f"Data loading warning: {message}")
                
        except Exception as e:
            self.update_status(f"Error during initialization: {str(e)}")
            # Still try to load pages for basic functionality
            self.load_pages()
    
    def update_status(self, message):
        """Update the status bar with a message."""
        if hasattr(self, 'status_var'):
            self.status_var.set(str(message))
            self.root.update_idletasks()
    
    def reload_data(self):
        """Reload data from files."""
        try:
            self.update_status("Reloading data...")
            success, message = self.backend.load_data()
            
            # Refresh all pages
            self.refresh_pages()
            
            if success:
                self.update_status("Data reloaded successfully")
            else:
                self.update_status(f"Data reload warning: {message}")
                
        except Exception as e:
            self.update_status(f"Error reloading data: {str(e)}")
            messagebox.showerror("Error", f"Failed to reload data: {str(e)}")
    
    def refresh_pages(self):
        """Refresh all loaded pages."""
        try:
            for page_name, page in self.pages.items():
                if hasattr(page, 'refresh_data'):
                    page.refresh_data()
            self.update_status("Pages refreshed")
        except Exception as e:
            self.update_status(f"Error refreshing pages: {str(e)}")
    
    def show_about(self):
        """Show about dialog."""
        about_text = """DBSyncr - Professional Edition
        
A simplified data management application for handling
NetSuite and Shopify product data.

Features:
• Bulk data editing and management
• Individual item editing
• Field mapping configuration
• Data export and synchronization

Version: 2.0"""
        
        messagebox.showinfo("About DBSyncr", about_text)
    
    def on_closing(self):
        """Handle application closing with threading support."""
        try:
            with self.shutdown_lock:
                if self.is_shutting_down:
                    return
                self.is_shutting_down = True
            
            # Call callback if provided (for threaded environment)
            if self.on_close_callback:
                self.on_close_callback()
            else:
                # Standalone mode - just destroy the window
                self.root.destroy()
                
        except Exception as e:
            # Ensure we close even if there's an error
            try:
                self.root.destroy()
            except:
                pass
    
    def run(self):
        """Start the GUI main loop."""
        try:
            self.update_status("Application ready")
            self.root.mainloop()
        except Exception as e:
            messagebox.showerror("Fatal Error", f"Application crashed: {str(e)}")


def main():
    """Main entry point for standalone execution."""
    try:
        app = DBSyncrGUI()
        app.run()
    except Exception as e:
        messagebox.showerror("Startup Error", f"Failed to start application: {str(e)}")


if __name__ == "__main__":
    main()