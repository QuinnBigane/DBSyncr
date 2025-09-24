#!/usr/bin/env python3
"""
DBSyncr Application
Runs the GUI and backend in separate threads with graceful shutdown.
"""

import threading
import time
import signal
import sys
import os
import logging
from typing import Optional
import tkinter as tk

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend_wrapper import DataBackend
from gui.app import DBSyncrGUI


class DBSyncr:
    """Main application controller that manages GUI and backend threads."""
    
    def __init__(self):
        self.backend = None
        self.gui = None
        self.backend_thread = None
        self.gui_thread = None
        self.shutdown_event = threading.Event()
        self.logger = self._setup_logging()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the threaded application."""
        logger = logging.getLogger('ThreadedDBSyncr')
        logger.setLevel(logging.INFO)
        
        # Create handler if it doesn't exist
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown()
    
    def start_backend_thread(self):
        """Start the backend in a separate thread."""
        def backend_worker():
            try:
                self.logger.info("Starting backend thread...")
                self.backend = DataBackend()
                
                # Load configuration and data
                success, message = self.backend.load_data()
                if success:
                    self.logger.info(f"Backend initialized successfully: {message}")
                else:
                    self.logger.warning(f"Backend initialization warning: {message}")
                
                # Keep backend alive and responsive
                while not self.shutdown_event.is_set():
                    time.sleep(0.1)  # Small delay to prevent high CPU usage
                    
                self.logger.info("Backend thread shutting down...")
                
            except Exception as e:
                self.logger.error(f"Backend thread error: {e}")
                import traceback
                traceback.print_exc()
                self.shutdown()
        
        self.backend_thread = threading.Thread(target=backend_worker, name="BackendThread")
        self.backend_thread.daemon = True
        self.backend_thread.start()
    
    def start_gui_thread(self):
        """Start the GUI in a separate thread."""
        def gui_worker():
            try:
                self.logger.info("Starting GUI thread...")
                
                # Wait for backend to be fully initialized and data loaded
                max_wait_time = 30  # Maximum wait time in seconds
                wait_interval = 0.5  # Check every 0.5 seconds
                waited_time = 0
                
                while waited_time < max_wait_time:
                    if (self.backend is not None and 
                        hasattr(self.backend, 'get_combined_data') and 
                        self.backend.get_combined_data() is not None):
                        self.logger.info("Backend data is ready, creating GUI...")
                        break
                    time.sleep(wait_interval)
                    waited_time += wait_interval
                else:
                    self.logger.warning("Backend data not ready after waiting, proceeding with GUI creation...")
                
                # Create the GUI
                self.gui = DBSyncrGUI(self.backend, on_close_callback=self.shutdown)
                
                # Start the GUI main loop
                self.gui.run()
                
                self.logger.info("GUI thread shutting down...")
                
            except Exception as e:
                self.logger.error(f"GUI thread error: {e}")
                import traceback
                traceback.print_exc()
                self.shutdown()
        
        self.gui_thread = threading.Thread(target=gui_worker, name="GUIThread")
        self.gui_thread.daemon = True
        self.gui_thread.start()
    
    def start(self):
        """Start both backend and GUI threads."""
        self.logger.info("Starting Threaded DBSyncr...")
        
        try:
            # Start backend first
            self.start_backend_thread()
            
            # Start GUI
            self.start_gui_thread()
            
            # Wait for threads to be ready
            time.sleep(1)
            
            self.logger.info("Both threads started successfully!")
            
            # Main thread keeps the application alive
            self.wait_for_shutdown()
            
        except Exception as e:
            self.logger.error(f"Failed to start application: {e}")
            self.shutdown()
    
    def wait_for_shutdown(self):
        """Wait for shutdown signal or thread completion."""
        try:
            while not self.shutdown_event.is_set():
                # Check if threads are still alive
                if self.gui_thread and not self.gui_thread.is_alive():
                    self.logger.info("GUI thread has ended, shutting down...")
                    break
                
                if self.backend_thread and not self.backend_thread.is_alive():
                    self.logger.info("Backend thread has ended, shutting down...")
                    break
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received, shutting down...")
        
        self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown all threads and resources."""
        if self.shutdown_event.is_set():
            return  # Already shutting down
            
        self.logger.info("Initiating graceful shutdown...")
        self.shutdown_event.set()
        
        # Close GUI first
        if self.gui:
            try:
                # Schedule GUI close on the GUI thread
                if hasattr(self.gui, 'root') and self.gui.root:
                    self.gui.root.after(0, self._close_gui_safely)
            except Exception as e:
                self.logger.warning(f"Error closing GUI: {e}")
        
        # Wait for threads to finish
        if self.gui_thread and self.gui_thread.is_alive():
            self.logger.info("Waiting for GUI thread to finish...")
            self.gui_thread.join(timeout=5)
            
        if self.backend_thread and self.backend_thread.is_alive():
            self.logger.info("Waiting for backend thread to finish...")
            self.backend_thread.join(timeout=5)
        
        # Cleanup backend
        if self.backend:
            try:
                # Any backend cleanup if needed
                pass
            except Exception as e:
                self.logger.warning(f"Error cleaning up backend: {e}")
        
        self.logger.info("Graceful shutdown completed!")
    
    def _close_gui_safely(self):
        """Safely close the GUI on the GUI thread."""
        try:
            if self.gui and hasattr(self.gui, 'root') and self.gui.root:
                self.gui.root.quit()
                self.gui.root.destroy()
        except Exception as e:
            self.logger.warning(f"Error in GUI cleanup: {e}")


def main():
    """Main entry point for the application."""
    print("🚀 Starting DBSyncr...")
    
    try:
        app = DBSyncr()
        app.start()
        
    except KeyboardInterrupt:
        print("\n⚠️  Keyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"❌ Application error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("✨ Application shutdown complete!")


if __name__ == "__main__":
    main()