#!/usr/bin/env python3
"""
DBSyncr Application
Simplified synchronous application controller.
"""

import sys
import os
import logging
from typing import Optional

# Add the src directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up to project root
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from services.data_service import DataService
from gui.app import DBSyncrGUI
from services.service_factory import ServiceFactory


class DBSyncr:
    """Simplified synchronous application controller."""

    def __init__(self):
        self.backend = None
        self.gui = None
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the application."""
        logger = logging.getLogger("DBSyncr")
        logger.setLevel(logging.INFO)

        # Create handler if it doesn't exist
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def initialize_backend(self):
        """Initialize the backend synchronously."""
        self.logger.info("Initializing backend...")

        try:
            self.backend = ServiceFactory.create_data_service()

            # Load configuration and data
            success, message = self.backend.load_data()
            if success:
                self.logger.info(f"Backend initialized successfully: {message}")
            else:
                self.logger.warning(f"Backend initialization warning: {message}")

        except Exception as e:
            self.logger.error(f"Failed to initialize backend: {e}")
            raise

    def start_gui(self):
        """Start the GUI synchronously."""
        self.logger.info("Starting GUI...")

        try:
            # Create the GUI
            self.gui = DBSyncrGUI(self.backend)

            # Start the GUI main loop (this blocks)
            self.gui.run()

        except Exception as e:
            self.logger.error(f"GUI error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def run(self):
        """Run the application synchronously."""
        self.logger.info("Starting DBSyncr...")

        try:
            # Initialize backend
            self.initialize_backend()

            # Start GUI (blocks until GUI closes)
            self.start_gui()

        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            raise
        finally:
            self.logger.info("DBSyncr shutting down...")