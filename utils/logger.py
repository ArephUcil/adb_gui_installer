import logging
import os
from datetime import datetime


class Logger:
    """Centralized logging system for the ADB GUI Installer."""

    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self):
        """Setup the logger with file and console handlers."""
        import sys
        
        # Determine log directory
        if getattr(sys, 'frozen', False):
            if sys.platform == "win32":
                base_data_dir = os.path.join(os.environ.get("APPDATA", ""), "ADB_GUI_Installer")
            elif sys.platform == "darwin":
                base_data_dir = os.path.expanduser("~/Library/Application Support/ADB_GUI_Installer")
            else:
                base_data_dir = os.path.expanduser("~/.adb_gui_installer")
            log_dir = os.path.join(base_data_dir, "logs")
        else:
            log_dir = os.path.join(os.getcwd(), "logs")
            
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError:
            # Fallback to current directory if data directory is not writable
            log_dir = os.path.join(os.getcwd(), "logs")
            os.makedirs(log_dir, exist_ok=True)

        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"adb_installer_{timestamp}.log")

        # Create logger
        self._logger = logging.getLogger("ADBInstaller")
        self._logger.setLevel(logging.DEBUG)

        # Remove any existing handlers
        self._logger.handlers.clear()

        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )

        # File handler (detailed logging)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)

        # Console handler (info and above only)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)

        # Add handlers to logger
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

        # Log the start of the application
        self._logger.info("ADB GUI Installer started")
        self._logger.info(f"Log file: {log_file}")

    @property
    def logger(self):
        """Get the logger instance."""
        return self._logger

    def get_log_file_path(self):
        """Get the current log file path."""
        if self._logger and self._logger.handlers:
            for handler in self._logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    return handler.baseFilename
        return None


# Global logger instance
logger = Logger().logger