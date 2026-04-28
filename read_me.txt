# ADB Multi-Device Installer

A modern PyQt5-based GUI application for managing Android devices via ADB (Android Debug Bridge). This tool allows you to connect, disconnect, and manage multiple Android devices simultaneously, with support for APK installation and uninstallation.

## Features

- 🔌 **Device Management**: Connect/disconnect Android devices over WiFi
- 📱 **Multi-Device Support**: Handle multiple devices simultaneously
- 📦 **APK Operations**: Install and uninstall APK files on selected devices
- 🔄 **Real-time Updates**: Live device list refresh and status monitoring
- 💾 **Configuration Persistence**: Remembers last used APK paths and package names
- 🖥️ **Clean GUI**: Modern PyQt5 interface with intuitive controls
- ⚡ **Background Processing**: Non-blocking operations using worker threads

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10/11, macOS 10.14+, or Linux
- **Python**: Python 3.8 or higher
- **RAM**: 512 MB minimum
- **Storage**: 50 MB free space

### Android Development Requirements
- **ADB (Android Debug Bridge)**: Must be installed and available in PATH
- **Android Device**: Physical device or emulator with USB debugging enabled
- **USB Drivers**: For physical devices (usually included with Android SDK)

## Installation

### 1. Install Python Dependencies

```bash
pip install PyQt5
```

### 2. Install Android SDK Platform Tools

Download and install Android SDK Platform Tools from:
https://developer.android.com/studio/releases/platform-tools

**Windows Installation:**
1. Download `platform-tools-latest-windows.zip`
2. Extract to a folder (e.g., `C:\android-sdk\platform-tools`)
3. Add the folder to your system PATH

**macOS Installation:**
```bash
brew install android-platform-tools
```

**Linux Installation:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install android-tools-adb android-tools-fastboot

# Or download from Android website
```

### 3. Verify ADB Installation

Open a terminal/command prompt and run:
```bash
adb version
```

You should see output similar to:
```
Android Debug Bridge version 1.0.41
Version 34.0.4-10411341
Installed as /path/to/adb
```

## Usage

### Starting the Application

1. Navigate to the project directory
2. Run the main application:
   ```bash
   python main.py
   ```

### Connecting Devices

#### WiFi Connection (Recommended)
1. Connect your Android device via USB
2. Enable USB debugging in Developer Options
3. Run `adb tcpip 5555` in terminal, or use the app's connect feature
4. Disconnect USB cable
5. In the app, enter your device's IP address and click "Connect"

#### USB Connection
- Simply connect your device via USB with debugging enabled
- The app will automatically detect USB-connected devices

### APK Operations

#### Installing APK
1. Click "Browse APK" to select your APK file
2. Select target devices from the device list
3. Click "Install APK" to begin installation
4. Monitor progress in the log area

#### Uninstalling Apps
1. Enter the package name (e.g., `com.example.app`)
2. Select target devices
3. Click "Uninstall App" to remove the application

### Device Management

- **Refresh Devices**: Click "Refresh Devices" to update the device list
- **Connect Device**: Enter IP address and click "Connect"
- **Disconnect Device**: Select device and click "Disconnect"

## Configuration

The application stores configuration in `utils/app_config.json`:

```json
{
  "last_package_name": "com.example.app",
  "last_apk_path": "/path/to/last/apk/file.apk"
}
```

You can manually edit this file to change default values.

## Troubleshooting

### Common Issues

#### "ADB not found" Error
- Ensure ADB is installed and in your system PATH
- Restart the application after installing ADB
- Check ADB installation: `adb version`

#### Device Not Detected
- Enable USB debugging in Developer Options
- Try different USB ports/cables
- For WiFi: Ensure device and computer are on same network
- Restart ADB server: `adb kill-server && adb start-server`

#### Unicode/Encoding Errors
- **Error**: `UnicodeDecodeError: 'charmap' codec can't decode byte...`
- **Cause**: Windows default encoding can't handle non-ASCII characters in ADB output
- **Solution**: The application handles this automatically with UTF-8 encoding
- **Manual Fix**: If issues persist, ensure your system locale supports UTF-8

#### APK Analysis Issues
- **Error**: Package name extraction fails
- **Cause**: Missing Android build tools (aapt/aapt2)
- **Solution**: Install Android SDK build-tools or use manual package name entry

#### Connection Issues
- Firewall/antivirus might block ADB
- Try different USB ports or cables
- For WiFi: Check IP address and network connectivity

### Debug Mode

Enable verbose logging by modifying the ADB commands in `services/adb_service.py` if needed.

### Reset Application

To reset configuration:
1. Delete `utils/app_config.json`
2. Restart the application

## Project Structure

```
adb_gui_installer/
├── main.py                 # Application entry point
├── services/
│   └── adb_service.py      # ADB command wrapper
├── ui/
│   └── main_window.py      # Main GUI window
├── utils/
│   ├── config_manager.py   # Configuration management
│   └── app_config.json     # Application settings
├── workers/
│   └── __init__.py         # Worker thread classes
└── read_me.txt            # This file
```

## Development

### Adding New Features

1. **ADB Operations**: Add methods to `AdbService` class
2. **UI Elements**: Modify `MainWindow` class in `ui/main_window.py`
3. **Workers**: Create new worker classes in `workers/__init__.py`

### Code Style

- Follow PEP 8 Python style guidelines
- Use type hints where possible
- Keep methods focused and single-purpose
- Handle exceptions appropriately

## License

This project is provided as-is for educational and development purposes.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Verify ADB installation and device setup
3. Ensure all Python dependencies are installed
4. Check application logs for error details

## Logging and Debugging

The application includes comprehensive logging to help troubleshoot issues. All operations are logged to both console and file.

### Log Files Location

- **Directory**: `logs/` (created automatically in the application folder)
- **Filename Format**: `adb_installer_YYYYMMDD_HHMMSS.log`
- **Example**: `adb_installer_20260422_143052.log`

### Log Levels

- **DEBUG**: Detailed technical information (ADB commands, outputs, etc.)
- **INFO**: General application flow and successful operations
- **WARNING**: Non-critical issues that don't prevent operation
- **ERROR**: Errors that may affect functionality

### Accessing Logs

1. **In Application**: The log file location is displayed in the application log area when it starts
2. **Automatic**: Logs are created automatically when the application starts
3. **Location**: Check the console output for the log file path
4. **Manual**: Navigate to the `logs/` folder in the application directory

### When to Provide Logs

When reporting issues, please include:
1. The relevant log file(s)
2. Description of what you were doing when the error occurred
3. Your system information (Windows version, Python version)
4. ADB version (`adb version` command output)

### Log File Example

```
2026-04-22 14:30:52 - ADBInstaller - INFO - ADB GUI Installer started
2026-04-22 14:30:52 - ADBInstaller - INFO - Log file: C:\path\to\app\logs\adb_installer_20260422_143052.log
2026-04-22 14:30:55 - ADBInstaller - INFO - Getting connected devices
2026-04-22 14:30:55 - ADBInstaller - DEBUG - Running ADB command: adb devices
2026-04-22 14:30:56 - ADBInstaller - INFO - Found device: emulator-5554
```

### Clearing Logs

To clear old log files:
1. Navigate to the `logs/` folder
2. Delete old `.log` files manually
3. The application will create new logs on next run

---

**Note**: This application requires Android devices with Developer Options enabled and USB debugging activated for full functionality.