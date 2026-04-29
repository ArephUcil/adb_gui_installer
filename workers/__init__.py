from PyQt5.QtCore import QThread, pyqtSignal
from utils.logger import logger


class BaseWorker(QThread):
    """Base class for ADB operation workers."""

    finished = pyqtSignal(str, str)  # device, message
    log_signal = pyqtSignal(str)

    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device

    def log(self, message):
        """Emit a log signal."""
        self.log_signal.emit(message)


class DeviceRefreshWorker(QThread):
    finished = pyqtSignal(list)
    log_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        from services.adb_service import AdbService

        self.log_signal.emit("Refreshing connected device list...")
        devices = AdbService.get_connected_devices()
        self.finished.emit(devices)


class DeviceConnectWorker(QThread):
    finished = pyqtSignal(bool, str)
    log_signal = pyqtSignal(str)

    def __init__(self, address, parent=None):
        super().__init__(parent)
        self.address = address

    def run(self):
        from services.adb_service import AdbService

        self.log_signal.emit(f"Connecting to {self.address}...")
        success, message = AdbService.connect_device(self.address)
        self.finished.emit(success, message)


class DeviceDisconnectWorker(QThread):
    finished = pyqtSignal()
    log_signal = pyqtSignal(str)

    def __init__(self, device_serials, parent=None):
        super().__init__(parent)
        self.device_serials = device_serials

    def run(self):
        from services.adb_service import AdbService

        for serial in self.device_serials:
            self.log_signal.emit(f"Disconnecting {serial}...")
            _, message = AdbService.disconnect_device(serial)
            self.log_signal.emit(message)

        self.finished.emit()


class InstallWorker(BaseWorker):
    """Worker for APK installation operations."""

    downgrade_detected = pyqtSignal(str, str)  # device, package_name
    progress = pyqtSignal(str, int)  # device, percentage

    def __init__(self, device, apk_path, parent=None):
        super().__init__(device, parent)
        self.apk_path = apk_path
        self.parent = parent

    def run(self):
        from services.adb_service import AdbService

        self.log(f"Installing on {self.device}...")
        self.progress.emit(self.device, 10)  # Start at 10%
        
        try:
            self.progress.emit(self.device, 30)  # Preparing
            success, message = AdbService.install_apk(self.device, self.apk_path)
            self.progress.emit(self.device, 100)  # Complete

            if not success and "VERSION_DOWNGRADE" in message:
                # Handle downgrade by offering to uninstall first
                package_name = self.parent.get_package_name_from_apk(self.apk_path)
                if package_name:
                    self.downgrade_detected.emit(self.device, package_name)
                    return  # Wait for user response

            self.finished.emit(self.device, message)
        except Exception as e:
            self.progress.emit(self.device, 0)
            logger.error(f"Installation error on {self.device}: {str(e)}")
            self.finished.emit(self.device, f"Installation error on {self.device}: {str(e)}")


class UninstallWorker(BaseWorker):
    """Worker for app uninstallation operations."""

    progress = pyqtSignal(str, int)  # device, percentage

    def __init__(self, device, package_name, parent=None):
        super().__init__(device, parent)
        self.package_name = package_name

    def run(self):
        from services.adb_service import AdbService

        self.log(f"Uninstalling {self.package_name} from {self.device}...")
        self.progress.emit(self.device, 0)
        
        try:
            success, message = AdbService.uninstall_app(self.device, self.package_name)
            self.progress.emit(self.device, 100)
            self.finished.emit(self.device, message)
        except Exception as e:
            self.progress.emit(self.device, 0)
            logger.error(f"Uninstallation error on {self.device}: {str(e)}")
            self.finished.emit(self.device, f"Uninstallation error on {self.device}: {str(e)}")


class ClearDataWorker(BaseWorker):
    """Worker for clearing app data operations."""

    progress = pyqtSignal(str, int)  # device, percentage

    def __init__(self, device, package_name, parent=None):
        super().__init__(device, parent)
        self.package_name = package_name

    def run(self):
        from services.adb_service import AdbService

        self.log(f"Clearing data for {self.package_name} on {self.device}...")
        self.progress.emit(self.device, 0)
        
        try:
            success, message = AdbService.clear_app_data(self.device, self.package_name)
            self.progress.emit(self.device, 100)
            self.finished.emit(self.device, message)
        except Exception as e:
            self.progress.emit(self.device, 0)
            logger.error(f"Clear data error on {self.device}: {str(e)}")
            self.finished.emit(self.device, f"Clear data error on {self.device}: {str(e)}")


class RetryInstallWorker(BaseWorker):
    """Worker for retrying installation after uninstalling for downgrade."""

    progress = pyqtSignal(str, int)  # device, percentage

    def __init__(self, device, apk_path, package_name, parent=None):
        super().__init__(device, parent)
        self.apk_path = apk_path
        self.package_name = package_name

    def run(self):
        from services.adb_service import AdbService

        self.log(f"Uninstalling {self.package_name} from {self.device} for downgrade...")
        self.progress.emit(self.device, 0)
        uninstall_success, uninstall_message = AdbService.uninstall_app(self.device, self.package_name)
        self.log(uninstall_message)
        self.progress.emit(self.device, 50)

        if uninstall_success:
            self.log(f"Retrying install on {self.device}...")
            success, message = AdbService.install_apk(self.device, self.apk_path)
            self.progress.emit(self.device, 100)
            self.finished.emit(self.device, message)
        else:
            self.progress.emit(self.device, 0)
            self.finished.emit(self.device, f"Failed to uninstall {self.package_name} on {self.device}")


class ApkInfoWorker(QThread):
    """Worker for extracting APK information asynchronously."""

    finished = pyqtSignal(list)  # info_lines
    error = pyqtSignal(str)  # error_message

    def __init__(self, apk_path, aapt_path=None, parent=None):
        super().__init__(parent)
        self.apk_path = apk_path
        self.aapt_path = aapt_path

    def run(self):
        try:
            info_lines = [f"APK File: {self.apk_path}"]
            metadata = self.extract_apk_metadata(self.apk_path)

            if metadata:
                info_lines.extend(metadata)
            else:
                info_lines.append("Unable to extract detailed APK metadata.")
                info_lines.append("Install Android SDK Build-tools (aapt / aapt2) to display package, version, SDK and permission details.")

            self.finished.emit(info_lines)
        except Exception as e:
            self.error.emit(f"Error extracting APK info: {str(e)}")

    def extract_apk_metadata(self, apk_path):
        """Extract APK metadata using aapt."""
        import os
        import re
        import subprocess

        aapt = self.aapt_path
        if not aapt:
            # Try to find aapt in bundled tools
            aapt_paths = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build-tools", "aapt.exe"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build-tools", "aapt2.exe"),
                "aapt.exe",
                "aapt2.exe",
                "aapt",
                "aapt2"
            ]

            for path in aapt_paths:
                if os.path.exists(path) or self._is_command_available(path):
                    aapt = path
                    break

        if not aapt:
            return None

        try:
            # Setup to run subprocess silently (no console window)
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
                creationflags=creation_flags
            )

            if result.returncode != 0:
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

            return metadata
        except Exception as e:
            logger.error(f"Error extracting APK metadata: {str(e)}")
            return None

    def _is_command_available(self, cmd):
        """Check if a command is available in PATH."""
        import shutil
        return shutil.which(cmd) is not None


class PackageNameWorker(QThread):
    """Worker for extracting the package name asynchronously."""

    finished = pyqtSignal(str)  # package_name
    error = pyqtSignal(str)  # error_message

    def __init__(self, apk_path, aapt_path=None, parent=None):
        super().__init__(parent)
        self.apk_path = apk_path
        self.aapt_path = aapt_path

    def run(self):
        import os
        import re
        import subprocess
        import shutil

        aapt = self.aapt_path
        if not aapt:
            # Try to find aapt in bundled tools
            aapt_paths = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build-tools", "aapt.exe"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build-tools", "aapt2.exe"),
                "aapt.exe",
                "aapt2.exe",
                "aapt",
                "aapt2"
            ]

            for path in aapt_paths:
                if os.path.exists(path) or shutil.which(path):
                    aapt = path
                    break

        if not aapt:
            self.error.emit("aapt/aapt2 not found, cannot extract package name")
            return

        try:
            # Setup to run subprocess silently (no console window)
            startup_info = None
            creation_flags = 0
            if os.name == 'nt':  # Windows
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup_info.wShowWindow = subprocess.SW_HIDE
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            result = subprocess.run(
                [aapt, "dump", "badging", self.apk_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=False,
                startupinfo=startup_info,
                creationflags=creation_flags
            )

            if result.returncode != 0:
                self.error.emit(f"aapt command failed with return code {result.returncode}")
                return

            for line in result.stdout.splitlines():
                if line.startswith("package:"):
                    match = re.search(r"name='([^']+)'", line)
                    if match:
                        package_name = match.group(1)
                        self.finished.emit(package_name)
                        return
                        
            self.error.emit("Package name not found in aapt output")
        except Exception as e:
            logger.error(f"Error extracting package name: {str(e)}")
            self.error.emit(f"Error extracting package name: {str(e)}")


class SecondaryDisplayWorker(BaseWorker):
    """Worker for configuring secondary display overlay."""

    progress = pyqtSignal(str, int)  # device, percentage

    def __init__(self, device, resolution, dpi, enable=True, parent=None):
        super().__init__(device, parent)
        self.resolution = resolution
        self.dpi = dpi
        self.enable = enable

    def run(self):
        from services.adb_service import AdbService

        if self.enable:
            display_config = f"{self.resolution}/{self.dpi}"
            self.log(f"Enabling secondary display {display_config} on {self.device}...")
            command = ["shell", "settings", "put", "global", "overlay_display_devices", display_config]
        else:
            self.log(f"Disabling secondary display on {self.device}...")
            command = ["shell", "settings", "delete", "global", "overlay_display_devices"]

        try:
            self.progress.emit(self.device, 50)
            result = AdbService._run_adb_command(AdbService._build_device_command(self.device, *command))
            self.progress.emit(self.device, 100)
            
            if result.returncode == 0:
                status = "enabled" if self.enable else "disabled"
                message = f"SUCCESS: Secondary display {status} on {self.device}"
                self.log(message)
            else:
                message = f"FAILED: Secondary display operation failed on {self.device}\n{result.stderr or result.stdout}"
                self.log(message)
            
            self.finished.emit(self.device, message)
        except Exception as e:
            self.progress.emit(self.device, 0)
            error_msg = f"Error configuring secondary display on {self.device}: {str(e)}"
            logger.error(error_msg)
            self.log(error_msg)
            self.finished.emit(self.device, error_msg)