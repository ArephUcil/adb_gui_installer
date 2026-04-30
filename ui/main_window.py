import json
import os
import re
import shutil
import subprocess
import zipfile
import sys

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QCheckBox,
    QGroupBox,
)

from services.adb_service import AdbService
from utils.config_manager import ConfigManager
from utils.logger import logger
from workers import (
    DeviceRefreshWorker,
    DeviceConnectWorker,
    DeviceDisconnectWorker,
    InstallWorker,
    UninstallWorker,
    ClearDataWorker,
    RetryInstallWorker,
    ApkInfoWorker,
    PackageNameWorker,
    SecondaryDisplayWorker,
)


# Constants
DEFAULT_PORT = "5555"
WINDOW_TITLE = "ADB Multi-Device Installer"
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        logger.info("Initializing MainWindow")
        self.apk_path = ""
        self.install_workers = []  # Track active install workers
        self.uninstall_workers = []  # Track active uninstall workers
        self.clear_data_workers = []  # Track active clear data workers
        self.secondary_display_workers = []  # Track active secondary display workers
        self.device_refresh_worker = None
        self.device_connect_worker = None
        self.device_disconnect_worker = None
        self.apk_info_worker = None
        self.package_name_worker = None

        # Progress tracking
        self.progress_bars = {}  # {device_serial: QProgressBar}
        self.progress_labels = {}  # {device_serial: QLabel}

        # Initialize config manager
        if getattr(sys, 'frozen', False):
            # If running as a compiled executable, use the folder containing the executable as app_dir
            app_dir = os.path.dirname(sys.executable)
            # Use standard app data directory for config/logs when frozen
            if sys.platform == "win32":
                data_dir = os.path.join(os.environ.get("APPDATA", app_dir), "ADB_GUI_Installer")
            elif sys.platform == "darwin":
                data_dir = os.path.expanduser("~/Library/Application Support/ADB_GUI_Installer")
            else:
                data_dir = os.path.expanduser("~/.adb_gui_installer")
        else:
            # If running as a Python script, use the project root
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = app_dir
            
        self.config = ConfigManager(app_dir, data_dir)
        
        # Initialize AdbService with configured path
        AdbService.set_adb_executable(self.config.adb_path)

        self.init_ui()
        self.apply_styles()

        # Log application start and show log location
        from utils.logger import Logger
        log_file = Logger().get_log_file_path()
        if log_file:
            logger.info(f"Log file location: {log_file}")
            self.log(f"Logs saved to: {os.path.basename(log_file)}")

    def apply_styles(self):
        theme = self.config.theme
        if theme == "light":
            bg_color = "#F5F5F5"
            card_bg = "#FFFFFF"
            text_color = "#333333"
            border_color = "#DDDDDD"
            input_bg = "#FFFFFF"
            item_selected = "#E1F5FE"
            secondary_text = "#666666"
        else:
            bg_color = "#252526"
            card_bg = "#2D2D30"
            text_color = "#CCCCCC"
            border_color = "#3E3E42"
            input_bg = "#333333"
            item_selected = "#37373D"
            secondary_text = "#999999"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }}
            
            QGroupBox {{
                background-color: {card_bg};
                border: 2px solid {border_color};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                font-weight: bold;
                color: #0078D4;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            
            QPushButton {{
                background-color: {border_color};
                color: {text_color};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
                font-weight: 500;
            }}
            
            QPushButton:hover {{
                background-color: {"#EEEEEE" if theme == "light" else "#444444"};
            }}
            
            QPushButton:pressed {{
                background-color: {"#CCCCCC" if theme == "light" else "#222222"};
            }}
            
            QPushButton#primary_button {{
                background-color: #0078D4;
                color: white;
            }}
            
            QPushButton#primary_button:hover {{
                background-color: #0086F0;
            }}
            
            QPushButton#danger_button {{
                background-color: #C42B1C;
                color: white;
            }}
            
            QPushButton#danger_button:hover {{
                background-color: #D83B2C;
            }}
            
            QPushButton#theme_toggle {{
                background-color: transparent;
                min-width: 40px;
                font-size: 16px;
            }}
            
            QLineEdit {{
                background-color: {input_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 6px;
                selection-background-color: #0078D4;
            }}
            
            QLineEdit:focus {{
                border: 1px solid #0078D4;
            }}
            
            QTextEdit {{
                background-color: {input_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 5px;
            }}
            
            QListWidget {{
                background-color: {input_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
                outline: none;
            }}
            
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {border_color};
            }}
            
            QListWidget::item:selected {{
                background-color: {item_selected};
                color: #0078D4;
                border-left: 3px solid #0078D4;
            }}
            
            QProgressBar {{
                border: 1px solid {border_color};
                border-radius: 4px;
                text-align: center;
                background-color: {input_bg};
            }}
            
            QProgressBar::chunk {{
                background-color: #0078D4;
                border-radius: 3px;
            }}
            
            QScrollBar:vertical {{
                border: none;
                background: {bg_color};
                width: 10px;
                margin: 0px;
            }}
            
            QScrollBar::handle:vertical {{
                background: {border_color};
                min-height: 20px;
                border-radius: 5px;
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
            
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
        """)
        
        # Update specific labels that might have hardcoded styles
        if hasattr(self, 'apk_label'):
            self.apk_label.setStyleSheet(f"color: {secondary_text}; font-style: italic; background-color: transparent;")
        if hasattr(self, 'progress_scroll'):
            self.progress_scroll.setStyleSheet("background-color: transparent; border: none;")
        if hasattr(self, 'log_output'):
            self.log_output.setStyleSheet(f"font-family: 'Consolas', 'Monaco', monospace; font-size: 11px; background-color: {input_bg}; border: 1px solid {border_color};")

    def toggle_theme(self):
        current_theme = self.config.theme
        new_theme = "light" if current_theme == "dark" else "dark"
        self.config.theme = new_theme
        self.apply_styles()
        self.theme_button.setText("☀️" if new_theme == "light" else "🌙")
        self.log(f"Theme switched to {new_theme} mode")

    def init_ui(self):
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # =============================
        # Header Section
        # =============================
        header_layout = QHBoxLayout()
        title_label = QLabel("ADB Multi-Device Installer")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078D4; background-color: transparent;")
        
        self.theme_button = QPushButton("☀️" if self.config.theme == "light" else "🌙")
        self.theme_button.setObjectName("theme_toggle")
        self.theme_button.setFixedWidth(40)
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setToolTip("Toggle Light/Dark Mode")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.theme_button)
        main_layout.addLayout(header_layout)

        # =============================
        # Tools Settings & WiFi Connection Section
        # =============================
        tools_conn_layout = QHBoxLayout()
        
        # Tools Settings
        tools_settings_group = QGroupBox("🛠️ Tool Settings")
        tools_layout = QVBoxLayout()

        self.use_bundled_tools_checkbox = QCheckBox("Use Bundled Tools (Automatic Path Resolution)")
        self.use_bundled_tools_checkbox.setChecked(self.config.use_bundled_tools)
        self.use_bundled_tools_checkbox.stateChanged.connect(self.on_bundled_tools_changed)
        tools_layout.addWidget(self.use_bundled_tools_checkbox)

        adb_path_layout = QHBoxLayout()
        adb_path_layout.addWidget(QLabel("ADB:"))
        self.adb_path_input = QLineEdit()
        self.adb_path_input.setText(self.config.adb_path)
        self.adb_path_input.setReadOnly(self.config.use_bundled_tools)
        self.adb_path_input.setEnabled(not self.config.use_bundled_tools)
        adb_path_layout.addWidget(self.adb_path_input)
        self.adb_browse_button = QPushButton("...")
        self.adb_browse_button.setFixedWidth(40)
        self.adb_browse_button.clicked.connect(self.browse_adb)
        self.adb_browse_button.setEnabled(not self.config.use_bundled_tools)
        adb_path_layout.addWidget(self.adb_browse_button)
        tools_layout.addLayout(adb_path_layout)

        # AAPT path
        aapt_path_layout = QHBoxLayout()
        aapt_path_layout.addWidget(QLabel("AAPT:"))
        self.aapt_path_input = QLineEdit()
        self.aapt_path_input.setText(self.config.aapt_path)
        self.aapt_path_input.setReadOnly(self.config.use_bundled_tools)
        self.aapt_path_input.setEnabled(not self.config.use_bundled_tools)
        aapt_path_layout.addWidget(self.aapt_path_input)
        self.aapt_browse_button = QPushButton("...")
        self.aapt_browse_button.setFixedWidth(40)
        self.aapt_browse_button.clicked.connect(self.browse_aapt)
        self.aapt_browse_button.setEnabled(not self.config.use_bundled_tools)
        aapt_path_layout.addWidget(self.aapt_browse_button)
        tools_layout.addLayout(aapt_path_layout)

        tools_settings_group.setLayout(tools_layout)
        
        # WiFi Connection Card
        conn_group = QGroupBox("🔌 WiFi Connection")
        conn_vbox = QVBoxLayout()
        ip_hbox = QHBoxLayout()
        self.connect_ip_input = QLineEdit()
        self.connect_ip_input.setPlaceholderText("IP Address (e.g. 192.168.1.5)")
        self.connect_port_input = QLineEdit()
        self.connect_port_input.setPlaceholderText("Port")
        self.connect_port_input.setFixedWidth(60)
        self.connect_port_input.setText(DEFAULT_PORT)
        ip_hbox.addWidget(self.connect_ip_input)
        ip_hbox.addWidget(self.connect_port_input)
        
        self.connect_button = QPushButton("Connect Device")
        self.connect_button.clicked.connect(self.connect_device)
        conn_vbox.addLayout(ip_hbox)
        conn_vbox.addWidget(self.connect_button)
        conn_group.setLayout(conn_vbox)
        
        tools_conn_layout.addWidget(tools_settings_group, 2)
        tools_conn_layout.addWidget(conn_group, 1)
        main_layout.addLayout(tools_conn_layout)

        # =============================
        # Connected Devices & APK Details Section
        # =============================
        devices_details_layout = QHBoxLayout()
        
        # Device Panel
        device_group = QGroupBox("📱 Connected Devices")
        device_vbox = QVBoxLayout()
        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QListWidget.MultiSelection)
        
        device_btns = QHBoxLayout()
        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.clicked.connect(self.load_devices)
        self.disconnect_button = QPushButton("🔌 Disconnect")
        self.disconnect_button.setObjectName("danger_button")
        self.disconnect_button.clicked.connect(self.disconnect_device)
        device_btns.addWidget(self.refresh_button)
        device_btns.addWidget(self.disconnect_button)
        
        device_vbox.addWidget(self.device_list)
        device_vbox.addLayout(device_btns)
        device_group.setLayout(device_vbox)
        
        # APK Details Card
        info_group = QGroupBox("ℹ️ APK Details")
        info_vbox = QVBoxLayout()
        self.apk_info_output = QTextEdit()
        self.apk_info_output.setReadOnly(True)
        self.apk_info_output.setPlaceholderText("APK metadata will appear here...")
        
        self.get_apk_info_button = QPushButton("Analyze APK")
        self.get_apk_info_button.clicked.connect(self.get_apk_info)
        self.get_apk_info_button.setEnabled(False)
        
        info_vbox.addWidget(self.apk_info_output)
        info_vbox.addWidget(self.get_apk_info_button)
        info_group.setLayout(info_vbox)
        
        devices_details_layout.addWidget(device_group, 1)
        devices_details_layout.addWidget(info_group, 2)
        main_layout.addLayout(devices_details_layout)

        # =============================
        # APK Management Section
        # =============================
        apk_group = QGroupBox("📦 APK Management")
        apk_hbox = QHBoxLayout()
        
        # Left side: APK info and label
        apk_left_vbox = QVBoxLayout()
        self.apk_label = QLabel("Not selected")
        self.apk_label.setWordWrap(True)
        self.apk_label.setStyleSheet("color: #AAAAAA; font-style: italic;")
        apk_left_vbox.addWidget(self.apk_label)
        apk_left_vbox.addStretch()
        
        # Right side: buttons vertically
        apk_btns_vbox = QVBoxLayout()
        self.browse_button = QPushButton("Browse APK")
        self.browse_button.setObjectName("primary_button")
        self.browse_button.clicked.connect(self.select_apk)
        self.install_button = QPushButton("📥 Install APK")
        self.install_button.setObjectName("primary_button")
        self.install_button.setEnabled(False)
        self.install_button.clicked.connect(self.install_apk)
        
        apk_btns_vbox.addWidget(self.browse_button)
        apk_btns_vbox.addWidget(self.install_button)
        
        apk_hbox.addLayout(apk_left_vbox, 2)
        apk_hbox.addLayout(apk_btns_vbox, 1)
        apk_group.setLayout(apk_hbox)
        main_layout.addWidget(apk_group)

        # =============================
        # Execution & Secondary Display Section
        # =============================
        exec_secondary_layout = QHBoxLayout()
        
        # Action Section
        action_group = QGroupBox("⚡ Execution")
        action_vbox = QVBoxLayout()
        
        pkg_hbox = QHBoxLayout()
        self.package_input = QLineEdit()
        self.package_input.setPlaceholderText("Target Package Name (e.g. com.example.app)")
        self.get_package_button = QPushButton("Auto-detect")
        self.get_package_button.clicked.connect(self.get_package_name)
        self.get_package_button.setEnabled(False)
        pkg_hbox.addWidget(self.package_input)
        pkg_hbox.addWidget(self.get_package_button)
        
        btns_hbox = QHBoxLayout()
        self.uninstall_button = QPushButton("🗑️ Uninstall")
        self.uninstall_button.setObjectName("danger_button")
        self.clear_data_button = QPushButton("🧹 Clear Data")
        
        self.uninstall_button.clicked.connect(self.uninstall_app)
        self.clear_data_button.clicked.connect(self.clear_app_data)
        
        btns_hbox.addWidget(self.uninstall_button)
        btns_hbox.addWidget(self.clear_data_button)
        
        action_vbox.addLayout(pkg_hbox)
        action_vbox.addLayout(btns_hbox)
        action_group.setLayout(action_vbox)
        
        # Secondary Display Section
        secondary_group = QGroupBox("🖥️ Secondary Display Settings")
        secondary_vbox = QVBoxLayout()
        
        # Resolution and DPI settings
        res_dpi_hbox = QHBoxLayout()
        
        res_label = QLabel("Resolution:")
        self.resolution_input = QLineEdit()
        self.resolution_input.setText("1280x800")
        self.resolution_input.setPlaceholderText("e.g. 1280x800")
        res_dpi_hbox.addWidget(res_label)
        res_dpi_hbox.addWidget(self.resolution_input)
        
        dpi_label = QLabel("DPI:")
        self.dpi_input = QLineEdit()
        self.dpi_input.setText("213")
        self.dpi_input.setPlaceholderText("e.g. 213")
        self.dpi_input.setFixedWidth(60)
        res_dpi_hbox.addWidget(dpi_label)
        res_dpi_hbox.addWidget(self.dpi_input)
        res_dpi_hbox.addStretch()
        
        # Secondary display buttons
        secondary_btns_hbox = QHBoxLayout()
        self.secondary_on_button = QPushButton("✓ Secondary ON")
        self.secondary_on_button.setObjectName("primary_button")
        self.secondary_on_button.clicked.connect(self.enable_secondary_display)
        self.secondary_off_button = QPushButton("✗ Secondary OFF")
        self.secondary_off_button.setObjectName("danger_button")
        self.secondary_off_button.clicked.connect(self.disable_secondary_display)
        
        secondary_btns_hbox.addWidget(self.secondary_on_button)
        secondary_btns_hbox.addWidget(self.secondary_off_button)
        
        secondary_vbox.addLayout(res_dpi_hbox)
        secondary_vbox.addLayout(secondary_btns_hbox)
        secondary_group.setLayout(secondary_vbox)
        
        exec_secondary_layout.addWidget(action_group, 1)
        exec_secondary_layout.addWidget(secondary_group, 1)
        main_layout.addLayout(exec_secondary_layout)

        # =============================
        # Status Section
        # =============================
        status_group = QGroupBox("📈 Progress & Logs")
        status_vbox = QVBoxLayout()
        
        self.progress_scroll = QScrollArea()
        self.progress_scroll.setWidgetResizable(True)
        self.progress_scroll.setMaximumHeight(100)
        self.progress_scroll.setStyleSheet("background-color: transparent; border: none;")
        self.progress_container = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_container)
        self.progress_layout.setContentsMargins(0, 0, 5, 0)
        self.progress_scroll.setWidget(self.progress_container)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(100)
        self.log_output.setStyleSheet("font-family: 'Consolas', 'Monaco', monospace; font-size: 11px;")
        
        status_vbox.addWidget(self.progress_scroll)
        status_vbox.addWidget(self.log_output)
        status_group.setLayout(status_vbox)
        main_layout.addWidget(status_group)

        self.setLayout(main_layout)

        # Initial checks
        self.initialize_app()

    def initialize_app(self):
        self.check_adb()
        self.load_devices()
        self.package_input.setText(self.config.last_package_name)

        saved_apk = self.config.last_apk_path
        if saved_apk:
            # Normalize path to handle forward slashes on Windows
            normalized_apk = os.path.normpath(saved_apk)
            self.apk_path = normalized_apk
            self.apk_label.setText(f"APK File: {normalized_apk}")
            self.install_button.setEnabled(True)
            self.get_apk_info_button.setEnabled(True)
            self.get_package_button.setEnabled(True)
            self.apk_info_output.setPlainText("Click 'Get APK Info' to view APK details and manifest information.")
            
            # Warn if file doesn't exist, but still display it
            if not os.path.exists(normalized_apk):
                self.log(f"Warning: Saved APK not currently accessible: {normalized_apk}")

    def save_package_name(self, package_name):
        config = self.load_config()
        config["last_package_name"] = package_name
        self.save_config(config)

    def save_apk_path(self, apk_path):
        config = self.load_config()
        config["last_apk_path"] = apk_path
        self.save_config(config)

    def log(self, message):
        self.log_output.append(message)

    def on_bundled_tools_changed(self):
        """Handle bundled tools checkbox change."""
        use_bundled = self.use_bundled_tools_checkbox.isChecked()
        self.config.use_bundled_tools = use_bundled
        self.adb_path_input.setEnabled(not use_bundled)
        self.adb_browse_button.setEnabled(not use_bundled)
        self.aapt_path_input.setEnabled(not use_bundled)
        self.aapt_browse_button.setEnabled(not use_bundled)
        
        # Refresh inputs to show active paths
        self.adb_path_input.setText(self.config.adb_path)
        self.aapt_path_input.setText(self.config.aapt_path)
        
        # Update services with new paths
        AdbService.set_adb_executable(self.config.adb_path)
        logger.info(f"Tool setting changed: use_bundled_tools={use_bundled}")
        self.log(f"Tool settings: Using {'Bundled' if use_bundled else 'Custom'} Tools")

    def browse_adb(self):
        """Browse for ADB executable."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ADB Executable",
            "",
            "ADB Executable (adb.exe);;All Files (*)"
        )
        if file_path:
            self.adb_path_input.setText(file_path)
            self.config.adb_path = file_path
            AdbService.set_adb_executable(file_path)
            self.log(f"ADB path set to: {file_path}")
            logger.info(f"ADB path updated to: {file_path}")

    def browse_aapt(self):
        """Browse for AAPT executable."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select AAPT Executable",
            "",
            "AAPT Executable (aapt.exe;aapt2.exe);;All Files (*)"
        )
        if file_path:
            self.aapt_path_input.setText(file_path)
            self.config.aapt_path = file_path
            self.log(f"AAPT path set to: {file_path}")
            logger.info(f"AAPT path updated to: {file_path}")

    def update_apk_info_panel(self, apk_path):
        info_lines = [f"APK File: {apk_path}"]
        metadata = self.extract_apk_metadata(apk_path)

        if metadata:
            info_lines.extend(metadata)
        else:
            info_lines.append("Unable to extract detailed APK metadata.")
            info_lines.append("Install Android SDK Build-tools (aapt / aapt2) to display package, version, SDK and permission details.")

        self.apk_info_output.setPlainText("\n".join(info_lines))

    def get_apk_info(self):
        if self.apk_path:
            if self.apk_info_worker and self.apk_info_worker.isRunning():
                return  # Already running

            self.apk_info_output.setPlainText("Extracting APK information...")
            self.get_apk_info_button.setEnabled(False)

            self.apk_info_worker = ApkInfoWorker(self.apk_path, self.config.aapt_path)
            self.apk_info_worker.finished.connect(self.on_apk_info_finished)
            self.apk_info_worker.error.connect(self.on_apk_info_error)
            self.apk_info_worker.start()
        else:
            QMessageBox.warning(self, "No APK Selected", "Please select an APK file first.")

    def on_apk_info_finished(self, info_lines):
        """Handle APK info extraction completion."""
        self.apk_info_output.setPlainText("\n".join(info_lines))
        self.get_apk_info_button.setEnabled(True)
        self.apk_info_worker = None

    def on_apk_info_error(self, error_message):
        """Handle APK info extraction error."""
        self.apk_info_output.setPlainText(f"Error: {error_message}")
        self.get_apk_info_button.setEnabled(True)
        self.apk_info_worker = None

    def get_package_name(self):
        if self.apk_path:
            if self.package_name_worker and self.package_name_worker.isRunning():
                return  # Prevent multiple clicks

            self.get_package_button.setEnabled(False)
            self.log("Extracting package name...")

            self.package_name_worker = PackageNameWorker(self.apk_path, self.config.aapt_path)
            self.package_name_worker.finished.connect(self.on_package_name_finished)
            self.package_name_worker.error.connect(self.on_package_name_error)
            self.package_name_worker.start()
        else:
            QMessageBox.warning(self, "No APK Selected", "Please select an APK file first.")

    def on_package_name_finished(self, package_name):
        """Handle package name extraction completion."""
        self.package_input.setText(package_name)
        self.log(f"Package name extracted: {package_name}")
        self.get_package_button.setEnabled(True)
        self.package_name_worker = None

    def on_package_name_error(self, error_message):
        """Handle package name extraction error."""
        QMessageBox.warning(self, "Package Name Extraction Failed", error_message)
        self.log(f"Package name extraction error: {error_message}")
        self.get_package_button.setEnabled(True)
        self.package_name_worker = None

    def _run_aapt_command(self, apk_path):
        """Helper method to run aapt command with silent window."""
        aapt = self.config.aapt_path
        if not aapt:
            return None
        
        try:
            # Setup silent window execution
            startup_info = None
            creation_flags = 0
            if os.name == 'nt':  # Windows
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup_info.wShowWindow = subprocess.SW_HIDE
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run(
                [aapt, "dump", "badging", apk_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=False,
                startupinfo=startup_info,
                creationflags=creation_flags,
                timeout=30
            )
            return result
        except Exception as e:
            logger.error(f"Error running aapt command: {str(e)}", exc_info=True)
            return None

    def get_package_name_from_apk(self, apk_path):
        logger.debug(f"Extracting package name from APK: {apk_path}")
        if not self.config.aapt_path:
            logger.warning("aapt/aapt2 not found, cannot extract package name")
            return None

        try:
            result = self._run_aapt_command(apk_path)
            if not result:
                return None
            
            if result.returncode != 0:
                logger.error(f"aapt command failed with return code {result.returncode}")
                return None

            for line in result.stdout.splitlines():
                if line.startswith("package:"):
                    match = re.search(r"name='([^']+)'", line)
                    if match:
                        package_name = match.group(1)
                        logger.debug(f"Extracted package name: {package_name}")
                        return package_name
            logger.warning("Package name not found in aapt output")
        except Exception as e:
            logger.error(f"Error extracting package name from APK: {str(e)}", exc_info=True)

        return None

    def extract_apk_metadata(self, apk_path):
        if not self.config.aapt_path:
            return None

        try:
            result = self._run_aapt_command(apk_path)
            if not result or result.returncode != 0:
                return None

            package_name = None
            version_name = None
            version_code = None
            app_label = None
            sdk_version = None
            target_sdk = None
            permissions = []

            for line in result.stdout.splitlines():
                if line.startswith("package:"):
                    match = re.search(r"name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", line)
                    if match:
                        package_name = match.group(1)
                        version_code = match.group(2)
                        version_name = match.group(3)
                elif line.startswith("application-label:"):
                    app_label = line.split(":", 1)[1].strip().strip("'")
                elif line.startswith("sdkVersion:"):
                    sdk_version = line.split(":", 1)[1].strip().strip("'")
                elif line.startswith("targetSdkVersion:"):
                    target_sdk = line.split(":", 1)[1].strip().strip("'")
                elif line.startswith("uses-permission:"):
                    permission = line.split(":", 1)[1].strip().strip("'")
                    permissions.append(permission)

            metadata = []
            if package_name:
                metadata.append(f"Package: {package_name}")
            if app_label:
                metadata.append(f"App Label: {app_label}")
            if version_name or version_code:
                if version_name:
                    metadata.append(f"Version Name: {version_name}")
                if version_code:
                    metadata.append(f"Version Code: {version_code}")
            if sdk_version:
                metadata.append(f"Min SDK: {sdk_version}")
            if target_sdk:
                metadata.append(f"Target SDK: {target_sdk}")
            if permissions:
                metadata.append(f"Declared Permissions ({len(permissions)}):")
                metadata.extend([f"  - {perm}" for perm in permissions[:20]])
                if len(permissions) > 20:
                    metadata.append(f"  ...and {len(permissions) - 20} more permissions")

            return metadata if metadata else None
        except Exception:
            return None

    def check_adb(self):
        adb_path = AdbService.check_adb()

        if not adb_path:
            QMessageBox.critical(
                self,
                "ADB Not Found",
                "adb is not available in PATH. Please install Android platform-tools."
            )
            return

        self.log(f"ADB found: {adb_path}")

    def select_apk(self):
        logger.info("Opening APK file selection dialog")
        last_apk_path = self.config.last_apk_path
        start_dir = ""
        if last_apk_path:
            # Normalize path to handle forward slashes on Windows
            normalized_last = os.path.normpath(last_apk_path)
            if os.path.isdir(normalized_last):
                start_dir = normalized_last
            else:
                start_dir = os.path.dirname(normalized_last)

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select APK File",
            start_dir,
            "APK Files (*.apk)"
        )

        if file_path:
            logger.info(f"APK selected: {file_path}")
            self.apk_path = file_path
            self.apk_label.setText(f"APK File: {file_path}")
            self.install_button.setEnabled(True)
            self.get_apk_info_button.setEnabled(True)
            self.get_package_button.setEnabled(True)
            # Normalize path before saving
            self.config.last_apk_path = os.path.normpath(file_path)
            self.apk_info_output.setPlainText("Click 'Get APK Info' to view APK details and manifest information.")
            self.log(f"Selected APK: {file_path}")
        else:
            logger.debug("APK selection cancelled")

    def connect_device(self):
        ip = self.connect_ip_input.text().strip()
        port = self.connect_port_input.text().strip() or DEFAULT_PORT

        if not ip:
            logger.warning("Connect device attempted without IP address")
            QMessageBox.warning(
                self,
                "No IP Address",
                "Please enter the device IP address before connecting."
            )
            return

        address = f"{ip}:{port}"
        logger.info(f"Starting device connection to {address}")
        self.log(f"Connecting to {address}...")
        self.connect_button.setEnabled(False)

        self.device_connect_worker = DeviceConnectWorker(address, self)
        self.device_connect_worker.log_signal.connect(self.log)
        self.device_connect_worker.finished.connect(self.on_device_connected)
        self.device_connect_worker.start()

    def disconnect_device(self):
        selected_serials = []
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.checkState() == 2:
                device_text = item.text()
                selected_serials.append(device_text.split(" | ")[-1])

        if not selected_serials:
            QMessageBox.warning(
                self,
                "No Device Selected",
                "Please select at least one device to disconnect."
            )
            return

        self.disconnect_button.setEnabled(False)
        self.device_disconnect_worker = DeviceDisconnectWorker(selected_serials, self)
        self.device_disconnect_worker.log_signal.connect(self.log)
        self.device_disconnect_worker.finished.connect(self.on_device_disconnected)
        self.device_disconnect_worker.start()

    def load_devices(self):
        self.start_refresh_devices()

    def start_refresh_devices(self):
        self.refresh_button.setEnabled(False)
        self.device_list.clear()

        self.device_refresh_worker = DeviceRefreshWorker(self)
        self.device_refresh_worker.log_signal.connect(self.log)
        self.device_refresh_worker.finished.connect(self.on_devices_loaded)
        self.device_refresh_worker.start()

    def on_devices_loaded(self, devices):
        self.refresh_button.setEnabled(True)

        if not devices:
            self.log("No connected devices found.")
            return

        for device in devices:
            display_text = (
                f"{device['model']} | Android {device['android_version']} | {device['serial']}"
            )
            item = QListWidgetItem(display_text)
            item.setCheckState(2)
            self.device_list.addItem(item)

        self.log("Device list refreshed.")

    def on_device_connected(self, success, message):
        self.log(message)
        self.connect_button.setEnabled(True)

        if success:
            self.load_devices()
        else:
            QMessageBox.warning(
                self,
                "ADB Connect Failed",
                message
            )

    def on_device_disconnected(self):
        self.disconnect_button.setEnabled(True)
        self.load_devices()

    def uninstall_app(self):
        package_name = self.package_input.text().strip()

        if not package_name:
            QMessageBox.warning(
                self,
                "No Package Name",
                "Please enter a valid package name before uninstalling."
            )
            return

        self.config.last_package_name = package_name

        selected_devices = []

        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.checkState() == 2:
                device_text = item.text()
                device = device_text.split(" | ")[-1]
                selected_devices.append(device)

        if not selected_devices:
            QMessageBox.warning(
                self,
                "No Device Selected",
                "Please select at least one device."
            )
            return

        # Start uninstallation workers for each device
        for device in selected_devices:
            worker = UninstallWorker(device, package_name, self)
            worker.log_signal.connect(self.log)
            worker.progress.connect(self.on_uninstall_progress)
            worker.finished.connect(self.on_uninstall_finished)
            self.uninstall_workers.append(worker)
            self.create_progress_bar(device)
            worker.start()

        # Disable uninstall button while uninstallations are in progress
        if self.uninstall_workers:
            self.uninstall_button.setEnabled(False)

    def install_apk(self):
        if not self.apk_path:
            QMessageBox.warning(
                self,
                "No APK Selected",
                "Please select an APK file first."
            )
            return

        if self.device_list.count() == 0:
            QMessageBox.warning(
                self,
                "No Devices Found",
                "No connected devices found."
            )
            return

        selected_devices = []

        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.checkState() == 2:
                device_text = item.text()
                device = device_text.split(" | ")[-1]
                selected_devices.append(device)

        if not selected_devices:
            QMessageBox.warning(
                self,
                "No Device Selected",
                "Please select at least one device."
            )
            return

        # Start installation workers for each device
        for device in selected_devices:
            worker = InstallWorker(device, self.apk_path, self)
            worker.log_signal.connect(self.log)
            worker.progress.connect(self.on_install_progress)
            worker.finished.connect(self.on_install_finished)
            worker.downgrade_detected.connect(self.on_downgrade_detected)
            self.install_workers.append(worker)
            self.create_progress_bar(device)
            worker.start()

        # Disable install button while installations are in progress
        if self.install_workers:
            self.install_button.setEnabled(False)

    def on_install_finished(self, device, message):
        self.log(message)
        # Remove progress bar
        self.remove_progress_bar(device)
        # Clean up finished workers
        self.install_workers = [w for w in self.install_workers if w.device != device]

        # Re-enable install button if no more workers are running
        if not self.install_workers:
            self.install_button.setEnabled(True)

    def on_uninstall_finished(self, device, message):
        self.log(message)
        # Remove progress bar
        self.remove_progress_bar(device)
        # Clean up finished workers
        self.uninstall_workers = [w for w in self.uninstall_workers if w.device != device]

        # Re-enable uninstall button if no more workers are running
        if not self.uninstall_workers:
            self.uninstall_button.setEnabled(True)

    def on_downgrade_detected(self, device, package_name):
        reply = QMessageBox.question(
            self,
            "Version Downgrade Detected",
            f"The APK version is lower than the installed version on {device}.\n\n"
            f"Package: {package_name}\n\n"
            f"Do you want to uninstall the current version first and then install the new one?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Create a new worker to handle the uninstall and retry
            retry_worker = RetryInstallWorker(device, self.apk_path, package_name, self)
            retry_worker.log_signal.connect(self.log)
            retry_worker.progress.connect(self.on_retry_install_progress)
            retry_worker.finished.connect(self.on_install_finished)
            self.install_workers.append(retry_worker)
            retry_worker.start()
        else:
            # User declined, just log the failure and clean up
            self.log(f"Installation cancelled for {device} due to version downgrade.")
            # Clean up the original worker
            self.install_workers = [w for w in self.install_workers if w.device != device]
            # Remove progress bar
            self.remove_progress_bar(device)
            # Re-enable install button if no more workers are running
            if not self.install_workers:
                self.install_button.setEnabled(True)

    def create_progress_bar(self, device):
        """Create a progress bar for a device operation."""
        if device in self.progress_bars:
            return  # Already exists
        
        # Create a horizontal layout for device label, progress bar, and percentage
        device_layout = QHBoxLayout()
        device_layout.setContentsMargins(0, 5, 0, 5)
        
        # Device label
        device_label = QLabel(device[:20] + "..." if len(device) > 20 else device)
        device_label.setFixedWidth(100)
        
        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        
        # Percentage label
        percentage_label = QLabel("0%")
        percentage_label.setFixedWidth(40)
        
        # Add to layout
        device_layout.addWidget(device_label)
        device_layout.addWidget(progress_bar)
        device_layout.addWidget(percentage_label)
        
        # Store references
        self.progress_bars[device] = progress_bar
        self.progress_labels[device] = percentage_label
        
        # Add to progress container
        self.progress_layout.addLayout(device_layout)

    def remove_progress_bar(self, device):
        """Remove the progress bar for a device."""
        if device in self.progress_bars:
            progress_bar = self.progress_bars.pop(device)
            percentage_label = self.progress_labels.pop(device)
            
            # Remove from layout
            layout = progress_bar.parent().layout() if progress_bar.parent() else None
            if layout:
                # Find and remove the layout containing this progress bar
                for i in range(self.progress_layout.count()):
                    item = self.progress_layout.itemAt(i)
                    if item.layout():
                        # Check if this layout contains our progress bar
                        for j in range(item.layout().count()):
                            if item.layout().itemAt(j).widget() == progress_bar:
                                # Remove the entire layout
                                layout_to_remove = self.progress_layout.takeAt(i)
                                if layout_to_remove:
                                    self.clear_layout(layout_to_remove.layout())
                                return

    def clear_layout(self, layout):
        """Clear all widgets from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def on_install_progress(self, device, percentage):
        """Update install progress bar."""
        if device in self.progress_bars:
            self.progress_bars[device].setValue(percentage)
            self.progress_labels[device].setText(f"{percentage}%")

    def on_uninstall_progress(self, device, percentage):
        """Update uninstall progress bar."""
        if device in self.progress_bars:
            self.progress_bars[device].setValue(percentage)
            self.progress_labels[device].setText(f"{percentage}%")

    def on_retry_install_progress(self, device, percentage):
        """Update retry install progress bar."""
        if device in self.progress_bars:
            self.progress_bars[device].setValue(percentage)
            self.progress_labels[device].setText(f"{percentage}%")

    def clear_app_data(self):
        package_name = self.package_input.text().strip()

        if not package_name:
            QMessageBox.warning(
                self,
                "No Package Name",
                "Please enter a valid package name before clearing data."
            )
            return

        selected_devices = []

        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.checkState() == 2:
                device_text = item.text()
                device = device_text.split(" | ")[-1]
                selected_devices.append(device)

        if not selected_devices:
            QMessageBox.warning(
                self,
                "No Device Selected",
                "Please select at least one device."
            )
            return

        # Start clear data workers for each device
        for device in selected_devices:
            worker = ClearDataWorker(device, package_name, self)
            worker.log_signal.connect(self.log)
            worker.progress.connect(self.on_clear_data_progress)
            worker.finished.connect(self.on_clear_data_finished)
            self.clear_data_workers.append(worker)
            self.create_progress_bar(device)
            worker.start()

        # Disable clear data button while operations are in progress
        if self.clear_data_workers:
            self.clear_data_button.setEnabled(False)

    def on_clear_data_finished(self, device, message):
        self.log(message)
        # Remove progress bar
        self.remove_progress_bar(device)
        # Clean up finished workers
        self.clear_data_workers = [w for w in self.clear_data_workers if w.device != device]

        # Re-enable button if no more workers are running
        if not self.clear_data_workers:
            self.clear_data_button.setEnabled(True)

    def on_clear_data_progress(self, device, percentage):
        """Update clear data progress bar."""
        if device in self.progress_bars:
            self.progress_bars[device].setValue(percentage)
            self.progress_labels[device].setText(f"{percentage}%")

    def enable_secondary_display(self):
        """Enable secondary display on selected devices."""
        resolution = self.resolution_input.text().strip()
        dpi = self.dpi_input.text().strip()

        if not resolution or not dpi:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter both resolution and DPI values."
            )
            return

        selected_devices = []
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.checkState() == 2:
                device_text = item.text()
                device = device_text.split(" | ")[-1]
                selected_devices.append(device)

        if not selected_devices:
            QMessageBox.warning(
                self,
                "No Device Selected",
                "Please select at least one device."
            )
            return

        # Start secondary display workers for each device
        for device in selected_devices:
            worker = SecondaryDisplayWorker(device, resolution, dpi, enable=True, parent=self)
            worker.log_signal.connect(self.log)
            worker.progress.connect(self.on_secondary_display_progress)
            worker.finished.connect(self.on_secondary_display_finished)
            self.secondary_display_workers.append(worker)
            self.create_progress_bar(device)
            worker.start()

        # Disable buttons while operations are in progress
        if self.secondary_display_workers:
            self.secondary_on_button.setEnabled(False)
            self.secondary_off_button.setEnabled(False)

    def disable_secondary_display(self):
        """Disable secondary display on selected devices."""
        selected_devices = []
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.checkState() == 2:
                device_text = item.text()
                device = device_text.split(" | ")[-1]
                selected_devices.append(device)

        if not selected_devices:
            QMessageBox.warning(
                self,
                "No Device Selected",
                "Please select at least one device."
            )
            return

        # Start secondary display workers for each device
        for device in selected_devices:
            worker = SecondaryDisplayWorker(device, "", "", enable=False, parent=self)
            worker.log_signal.connect(self.log)
            worker.progress.connect(self.on_secondary_display_progress)
            worker.finished.connect(self.on_secondary_display_finished)
            self.secondary_display_workers.append(worker)
            self.create_progress_bar(device)
            worker.start()

        # Disable buttons while operations are in progress
        if self.secondary_display_workers:
            self.secondary_on_button.setEnabled(False)
            self.secondary_off_button.setEnabled(False)

    def on_secondary_display_progress(self, device, percentage):
        """Update secondary display progress bar."""
        if device in self.progress_bars:
            self.progress_bars[device].setValue(percentage)
            self.progress_labels[device].setText(f"{percentage}%")

    def on_secondary_display_finished(self, device, message):
        """Handle secondary display operation completion."""
        self.log(message)
        # Remove progress bar
        self.remove_progress_bar(device)
        # Clean up finished workers
        self.secondary_display_workers = [w for w in self.secondary_display_workers if w.device != device]

        # Re-enable buttons if no more workers are running
        if not self.secondary_display_workers:
            self.secondary_on_button.setEnabled(True)
            self.secondary_off_button.setEnabled(True)