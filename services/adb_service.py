import os
import shutil
import subprocess
from utils.logger import logger


class AdbService:
    """Service for running ADB commands with configurable tool paths."""
    
    _adb_executable = None

    @staticmethod
    def set_adb_executable(adb_path):
        """Set the ADB executable path to use."""
        AdbService._adb_executable = adb_path
        logger.info(f"ADB executable set to: {adb_path}")

    @staticmethod
    def get_adb_executable():
        """Get the ADB executable path."""
        if AdbService._adb_executable:
            return AdbService._adb_executable
        return "adb"
    @staticmethod
    def _run_adb_command(command, timeout=30):
        """
        Helper method to run ADB commands with common parameters.
        """
        logger.debug(f"Running ADB command: {' '.join(command)}")
        try:
            kwargs = {
                "capture_output": True,
                "text": True,
                "encoding": 'utf-8',
                "errors": 'replace',
                "check": False,
                "timeout": timeout
            }
            
            # creationflags is Windows-only
            if os.name == 'nt':
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                
            result = subprocess.run(command, **kwargs)
            logger.debug(f"ADB command completed with return code: {result.returncode}")
            if result.stdout:
                logger.debug(f"ADB stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.debug(f"ADB stderr: {result.stderr.strip()}")
            return result
        except subprocess.TimeoutExpired as e:
            logger.error(f"ADB command timed out after {timeout}s: {' '.join(command)}")
            raise
        except Exception as e:
            logger.error(f"Error running ADB command {' '.join(command)}: {str(e)}")
            raise

    @staticmethod
    def _build_device_command(device_serial, *args):
        """
        Helper method to build ADB commands for a specific device.
        """
        adb_exe = AdbService.get_adb_executable()
        return [adb_exe, "-s", device_serial] + list(args)

    @staticmethod
    def _process_command_output(result, success_indicators, operation_name, target):
        """
        Helper method to process command output and determine success.
        
        Args:
            result: subprocess.CompletedProcess result
            success_indicators: list of strings that indicate success
            operation_name: name of the operation for error messages
            target: target of the operation for error messages
            
        Returns:
            tuple: (success: bool, message: str)
        """
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        logger.debug(f"Processing output for {operation_name} on {target}")
        logger.debug(f"Command output: {output.strip()}")
        
        for indicator in success_indicators:
            if indicator.lower() in output.lower():
                logger.info(f"{operation_name} succeeded for {target}")
                return True, f"SUCCESS: {operation_name} {target}"
        
        logger.warning(f"{operation_name} failed for {target}: {output.strip()}")
        return False, f"FAILED to {operation_name.lower()} {target}\n{output.strip()}"

    @staticmethod
    def _execute_adb_operation(command, success_indicators, operation_desc, target, timeout=30):
        """
        Generic method to execute ADB operations that return success/message tuples.
        
        Args:
            command: list of command arguments
            success_indicators: list of strings indicating success
            operation_desc: description of the operation for success messages
            target: target of the operation for messages
            timeout: command timeout in seconds
            
        Returns:
            tuple: (success: bool, message: str)
        """
        logger.info(f"Executing {operation_desc.lower()} on {target}")
        try:
            result = AdbService._run_adb_command(command, timeout=timeout)
            return AdbService._process_command_output(
                result, success_indicators, operation_desc, target
            )
        except subprocess.TimeoutExpired as e:
            logger.error(f"{operation_desc} timed out for {target}: {str(e)}")
            return False, f"ADB {operation_desc.lower().split()[0]} timed out for {target}: {str(e)}"
        except Exception as e:
            logger.error(f"Error during {operation_desc.lower()} on {target}: {str(e)}", exc_info=True)
            return False, f"Error {operation_desc.lower()} {target}: {str(e)}"

    @staticmethod
    def check_adb():
        """
        Check whether adb is available at configured path or in PATH.
        Returns adb path if found, otherwise None.
        """
        adb_exe = AdbService.get_adb_executable()
        if os.path.exists(adb_exe):
            return adb_exe
        return shutil.which(adb_exe) or shutil.which("adb")

    @staticmethod
    def get_connected_devices():
        """
        Returns a list of connected device serials.
        Example:
        ["emulator-5554", "R58N123456"]
        """
        logger.info("Getting connected devices")
        devices = []

        try:
            adb_exe = AdbService.get_adb_executable()
            result = AdbService._run_adb_command([adb_exe, "devices"])

            lines = result.stdout.strip().split("\n")
            logger.debug(f"ADB devices output: {len(lines)} lines")

            for line in lines[1:]:
                if "	device" in line:
                    serial = line.split("	")[0]
                    logger.info(f"Found device: {serial}")

                    model_command = AdbService._build_device_command(
                        serial, "shell", "getprop", "ro.product.model"
                    )
                    model_result = AdbService._run_adb_command(model_command)

                    version_command = AdbService._build_device_command(
                        serial, "shell", "getprop", "ro.build.version.release"
                    )
                    version_result = AdbService._run_adb_command(version_command)

                    device_info = {
                        "serial": serial,
                        "model": model_result.stdout.strip() or "Unknown Model",
                        "android_version": version_result.stdout.strip() or "Unknown Version"
                    }
                    devices.append(device_info)
                    logger.info(f"Device info collected: {device_info}")

        except subprocess.TimeoutExpired as e:
            logger.error(f"ADB devices command timed out: {str(e)}")
            print(f"ADB Timeout: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting connected devices: {str(e)}", exc_info=True)
            print(f"ADB Error: {str(e)}")

        logger.info(f"Found {len(devices)} connected devices")
        return devices

    @staticmethod
    def connect_device(address):
        """
        Connect to a device over TCP/IP via adb.
        Returns success and message.
        """
        adb_exe = AdbService.get_adb_executable()
        return AdbService._execute_adb_operation(
            [adb_exe, "connect", address],
            ["connected to", "already connected to"],
            "Connected to",
            address
        )

    @staticmethod
    def disconnect_device(address):
        """
        Disconnect a device over TCP/IP via adb.
        Returns success and message.
        """
        adb_exe = AdbService.get_adb_executable()
        return AdbService._execute_adb_operation(
            [adb_exe, "disconnect", address],
            ["disconnected", "not connected"],
            "Disconnected",
            address
        )

    @staticmethod
    def uninstall_app(device_serial, package_name):
        """
        Uninstall app from a specific device.

        Returns:
            success (bool)
            message (str)
        """
        command = AdbService._build_device_command(device_serial, "uninstall", package_name)
        return AdbService._execute_adb_operation(
            command,
            ["Success"],
            f"Uninstalled {package_name} from",
            device_serial
        )

    @staticmethod
    def install_apk(device_serial, apk_path):
        """
        Install APK on a specific device.

        Returns:
            success (bool)
            message (str)
        """
        command = AdbService._build_device_command(device_serial, "install", "-r", apk_path)
        return AdbService._execute_adb_operation(
            command,
            ["Success"],
            "Installed on",
            device_serial,
            timeout=60
        )

    @staticmethod
    def clear_app_data(device_serial, package_name):
        """
        Clear app data for a specific package on a device.

        Returns:
            success (bool)
            message (str)
        """
        command = AdbService._build_device_command(device_serial, "shell", "pm", "clear", package_name)
        return AdbService._execute_adb_operation(
            command,
            ["Success"],
            f"Cleared data for {package_name} on",
            device_serial
        )