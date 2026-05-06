import os
import shutil
import subprocess
from utils.logger import logger


class AdbService:
    """Service for running ADB commands with configurable tool paths."""
    
    _adb_executable = None
    _recording_processes = {}  # Track recording processes by device serial

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

    @staticmethod
    def take_screenshot(device_serial, output_path):
        """
        Take a screenshot from a specific device and save to output_path.

        Returns:
            success (bool)
            message (str)
        """
        command = AdbService._build_device_command(device_serial, "exec-out", "screencap", "-p")
        
        logger.info(f"Taking screenshot from {device_serial} to {output_path}")
        try:
            # For binary output, we need to handle it differently
            adb_exe = AdbService.get_adb_executable()
            full_command = [adb_exe, "-s", device_serial, "exec-out", "screencap", "-p"]
            
            result = subprocess.run(
                full_command,
                capture_output=True,
                check=False,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                with open(output_path, 'wb') as f:
                    f.write(result.stdout)  # Write binary data directly
                logger.info(f"Screenshot saved to {output_path}")
                return True, f"Screenshot saved to {output_path}"
            else:
                error_msg = result.stderr.decode('utf-8', errors='replace').strip() or "Unknown error"
                logger.error(f"Screenshot failed: {error_msg}")
                return False, f"Failed to take screenshot: {error_msg}"
                
        except Exception as e:
            logger.error(f"Error taking screenshot from {device_serial}: {str(e)}")
            return False, f"Error taking screenshot: {str(e)}"

    @staticmethod
    def start_screen_recording(device_serial, remote_path="/sdcard/screen_record.mp4", duration=None, bit_rate="12000000"):
        """
        Start screen recording on a specific device.
        
        Args:
            device_serial: Device serial number
            remote_path: Path on device to save recording
            duration: Recording duration in seconds (None for indefinite)
            bit_rate: Bit rate for video compression (lower = smaller file)
            
        Returns:
            success (bool)
            message (str)
        """
        # For indefinite recording, start in background
        import subprocess
        
        adb_exe = AdbService.get_adb_executable()
        command = [adb_exe, "-s", device_serial, "shell", "screenrecord", 
                    "--bit-rate", bit_rate, remote_path]
        
        logger.info(f"Starting indefinite screen recording on {device_serial}")
        try:
            # Start the process in background
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Store the process for later stopping
            AdbService._recording_processes[device_serial] = process
            
            logger.info(f"Screen recording started on {device_serial}")
            return True, f"Recording started on device: {remote_path}"
            
        except Exception as e:
            logger.error(f"Error starting screen recording on {device_serial}: {str(e)}")
            return False, f"Error starting recording: {str(e)}"

    @staticmethod
    def stop_screen_recording(device_serial, remote_path="/sdcard/screen_record.mp4"):
        """
        Stop screen recording on a specific device.
        
        Returns:
            success (bool)
            message (str)
        """
        logger.info(f"Stopping screen recording on {device_serial}")
        try:
            adb_exe = AdbService.get_adb_executable()
            pid_command = [adb_exe, "-s", device_serial, "shell", "pidof", "screenrecord"]

            # First stop the remote screenrecord process so the MP4 can finalize
            pid_result = subprocess.run(
                pid_command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=False,
                timeout=10
            )

            remote_stopped = False
            if pid_result.returncode == 0 and pid_result.stdout.strip():
                for pid in pid_result.stdout.strip().split():
                    kill_command = [adb_exe, "-s", device_serial, "shell", "kill", "-2", pid]
                    subprocess.run(
                        kill_command,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        check=False,
                        timeout=10
                    )

                import time
                timeout = 5
                interval = 0.5
                elapsed = 0.0
                while elapsed < timeout:
                    check_result = subprocess.run(
                        pid_command,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        check=False,
                        timeout=10
                    )
                    if check_result.returncode != 0 or not check_result.stdout.strip():
                        remote_stopped = True
                        break
                    time.sleep(interval)
                    elapsed += interval

                if not remote_stopped:
                    logger.warning(f"Remote screenrecord process still running after SIGINT on {device_serial}")
            else:
                remote_stopped = True
                logger.info(f"No remote screenrecord process found on {device_serial}")

            # Then stop the local adb shell process cleanly
            if device_serial in AdbService._recording_processes:
                process = AdbService._recording_processes[device_serial]
                try:
                    process.terminate()
                    process.wait(timeout=10)
                except Exception:
                    process.kill()
                    process.wait(timeout=5)
                finally:
                    del AdbService._recording_processes[device_serial]

            # Give the device a moment to finalize the MP4 header if needed
            if remote_stopped:
                import time
                time.sleep(1)

            logger.info(f"Screen recording stopped on {device_serial}")
            return True, f"Recording stopped on device: {remote_path}"
        except Exception as e:
            logger.error(f"Error stopping screen recording on {device_serial}: {str(e)}")
            return False, f"Error stopping recording: {str(e)}"

    @staticmethod
    def pull_file(device_serial, remote_path, local_path):
        """
        Pull a file from device to local machine.
        
        Returns:
            success (bool)
            message (str)
        """
        command = AdbService._build_device_command(device_serial, "pull", remote_path, local_path)
        return AdbService._execute_adb_operation(
            command,
            ["100%", "1 file pulled"],
            f"Pulled {remote_path} to",
            local_path
        )