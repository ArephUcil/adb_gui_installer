import json
import os
import shutil
import sys


class ConfigManager:
    """Manages application configuration persistence."""

    CONFIG_FILE = "app_config.json"

    def __init__(self, app_dir, data_dir=None):
        self.app_dir = app_dir
        self.data_dir = data_dir or app_dir
        self.config_path = os.path.join(self.data_dir, self.CONFIG_FILE)
        
        # Ensure data directory exists
        if not os.path.exists(self.data_dir):
            try:
                os.makedirs(self.data_dir, exist_ok=True)
            except OSError:
                # Fallback to app_dir if data_dir is not writable
                self.data_dir = app_dir
                self.config_path = os.path.join(self.data_dir, self.CONFIG_FILE)
        
        # Determine bundled tools directory
        if getattr(sys, 'frozen', False):
            self.bundled_dir = sys._MEIPASS
        else:
            self.bundled_dir = app_dir
            
        self._config = self._load_config()
        self._setup_default_tools()

    def _load_config(self):
        """Load configuration from file."""
        if not os.path.exists(self.config_path):
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _setup_default_tools(self):
        """Setup default tool paths if not configured."""
        if "use_bundled_tools" not in self._config:
            self._config["use_bundled_tools"] = True
        
        if "adb_path" not in self._config:
            adb_name = "adb.exe" if os.name == "nt" else "adb"
            bundled_adb = os.path.join(self.bundled_dir, "platform-tools", adb_name)
            self._config["adb_path"] = bundled_adb if os.path.exists(bundled_adb) else ""
        
        if "aapt_path" not in self._config:
            # Try to find aapt in bundled tools or system
            self._config["aapt_path"] = self._find_aapt()
        
        self._save_config()

    def _find_aapt(self):
        """Find aapt or aapt2 executable in bundled tools or common system locations."""
        # 1. Try bundled tools first
        build_tools_dir = os.path.join(self.bundled_dir, "build-tools")
        bundled_aapt = self._find_aapt_in_build_tools(build_tools_dir)
        if bundled_aapt:
            return bundled_aapt

        # 2. Try system PATH
        aapt_path = shutil.which("aapt") or shutil.which("aapt2")
        if aapt_path:
            return aapt_path
            
        # 3. Try common Mac locations (Homebrew)
        if sys.platform == "darwin":
            for base in ["/opt/homebrew/bin", "/usr/local/bin"]:
                for name in ["aapt", "aapt2"]:
                    path = os.path.join(base, name)
                    if os.path.exists(path) and os.access(path, os.X_OK):
                        return path

        # 4. Try common Android SDK locations
        sdk_root = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        if not sdk_root:
            if os.name == "nt":
                local_app_data = os.environ.get("LOCALAPPDATA", "")
                if local_app_data:
                    sdk_root = os.path.join(local_app_data, "Android", "Sdk")
            elif sys.platform == "darwin":
                sdk_root = os.path.expanduser("~/Library/Android/sdk")
            else:
                sdk_root = os.path.expanduser("~/Android/Sdk")

        if sdk_root and os.path.exists(sdk_root):
            build_tools = os.path.join(sdk_root, "build-tools")
            if os.path.exists(build_tools):
                found_aapt = self._find_aapt_in_build_tools(build_tools)
                if found_aapt:
                    return found_aapt

        return ""

    def _find_aapt_in_build_tools(self, build_tools_dir):
        """Find aapt executable in build-tools directory or its subdirectories."""
        if not os.path.exists(build_tools_dir):
            return None
        
        aapt_name = "aapt.exe" if os.name == "nt" else "aapt"
        aapt2_name = "aapt2.exe" if os.name == "nt" else "aapt2"
        
        # Check root of build-tools first
        aapt_root = os.path.join(build_tools_dir, aapt_name)
        aapt2_root = os.path.join(build_tools_dir, aapt2_name)
        if os.path.exists(aapt_root):
            return aapt_root
        if os.path.exists(aapt2_root):
            return aapt2_root
        
        # Look for aapt or aapt2 in build-tools subdirectories (sorted by name descending to get latest version)
        if os.path.isdir(build_tools_dir):
            try:
                subdirs = sorted(os.listdir(build_tools_dir), reverse=True)
                for item in subdirs:
                    item_path = os.path.join(build_tools_dir, item)
                    if os.path.isdir(item_path):
                        aapt = os.path.join(item_path, aapt_name)
                        aapt2 = os.path.join(item_path, aapt2_name)
                        if os.path.exists(aapt):
                            return aapt
                        if os.path.exists(aapt2):
                            return aapt2
            except OSError:
                pass
        
        return None

    def _save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2)
        except OSError as e:
            from utils.logger import logger
            logger.warning(f"Failed to save config to {self.config_path}: {e}")

    def get(self, key, default=None):
        """Get a configuration value."""
        return self._config.get(key, default)

    def set(self, key, value):
        """Set a configuration value."""
        self._config[key] = value
        self._save_config()

    @property
    def theme(self):
        """Get the current theme (light or dark)."""
        return self.get("theme", "dark")

    @theme.setter
    def theme(self, value):
        """Set the current theme."""
        self.set("theme", value)

    @property
    def last_package_name(self):
        """Get the last used package name."""
        return self.get("last_package_name", "")

    @last_package_name.setter
    def last_package_name(self, value):
        """Set the last used package name."""
        self.set("last_package_name", value)

    @property
    def last_apk_path(self):
        """Get the last used APK path."""
        return self.get("last_apk_path", "")

    @last_apk_path.setter
    def last_apk_path(self, value):
        """Set the last used APK path."""
        self.set("last_apk_path", value)

    @property
    def use_bundled_tools(self):
        """Get whether to use bundled tools."""
        return self.get("use_bundled_tools", True)

    @use_bundled_tools.setter
    def use_bundled_tools(self, value):
        """Set whether to use bundled tools."""
        self.set("use_bundled_tools", value)

    @property
    def adb_path(self):
        """Get the ADB executable path."""
        path = self.get("adb_path", "")
        # If configured to use bundled tools, prefer bundled path if it exists
        if self.use_bundled_tools:
            adb_name = "adb.exe" if os.name == "nt" else "adb"
            bundled_adb = os.path.join(self.bundled_dir, "platform-tools", adb_name)
            if os.path.exists(bundled_adb):
                return bundled_adb
        
        # Fall back to configured path
        if path:
            return path
            
        # Try to find in system
        return self._find_adb()

    def _find_adb(self):
        """Find adb executable in system PATH or common locations."""
        adb_name = "adb.exe" if os.name == "nt" else "adb"
        
        # 1. Try system PATH
        adb_path = shutil.which("adb")
        if adb_path:
            return adb_path
            
        # 2. Try common Mac locations (Homebrew)
        if sys.platform == "darwin":
            for base in ["/opt/homebrew/bin", "/usr/local/bin"]:
                path = os.path.join(base, "adb")
                if os.path.exists(path) and os.access(path, os.X_OK):
                    return path
                    
        # 3. Try common Android SDK locations
        sdk_root = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        if not sdk_root:
            if os.name == "nt":
                local_app_data = os.environ.get("LOCALAPPDATA", "")
                if local_app_data:
                    sdk_root = os.path.join(local_app_data, "Android", "Sdk")
            elif sys.platform == "darwin":
                sdk_root = os.path.expanduser("~/Library/Android/sdk")
            else:
                sdk_root = os.path.expanduser("~/Android/Sdk")

        if sdk_root and os.path.exists(sdk_root):
            adb_sdk_path = os.path.join(sdk_root, "platform-tools", adb_name)
            if os.path.exists(adb_sdk_path):
                return adb_sdk_path

        return "adb"

    @adb_path.setter
    def adb_path(self, value):
        """Set the ADB executable path."""
        self.set("adb_path", value)

    @property
    def aapt_path(self):
        """Get the AAPT executable path."""
        path = self.get("aapt_path", "")
        # If configured to use bundled tools, prefer bundled path if it exists
        if self.use_bundled_tools:
            build_tools_dir = os.path.join(self.bundled_dir, "build-tools")
            bundled_aapt = self._find_aapt_in_build_tools(build_tools_dir)
            if bundled_aapt:
                return bundled_aapt
        
        # Fall back to configured path
        if path:
            return path
            
        # Try to find in system
        return self._find_aapt()

    @aapt_path.setter
    def aapt_path(self, value):
        """Set the AAPT executable path."""
        self.set("aapt_path", value)