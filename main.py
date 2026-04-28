import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.logger import logger


def main():
    """Main application entry point with error handling."""
    try:
        logger.info("Starting ADB GUI Installer application")
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        logger.info("Application window shown")
        sys.exit(app.exec_())
    except Exception as e:
        logger.error(f"Critical error in main application: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
