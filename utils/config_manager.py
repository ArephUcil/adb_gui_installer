import json
import os
import shutil


class ConfigManager:
    """Manages application configuration persistence."""

    CONFIG_FILE = os.path.join("utils", "app_config.json")

    def __init__(self, app_dir):
        self.app_dir = app_dir
        self.config_path = os.path.join(app_dir, self.CONFIG_FILE)
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
            bundled_adb = os.path.join(self.app_dir, "platform-tools", "adb.exe")
            self._config["adb_path"] = bundled_adb if os.path.exists(bundled_adb) else ""
        
        if "aapt_path" not in self._config:
            # Try to find aapt in build-tools subdirectories
            build_tools_dir = os.path.join(self.app_dir, "build-tools")
            aapt_path = self._find_aapt_in_build_tools(build_tools_dir)
            self._config["aapt_path"] = aapt_path or ""
        
        self._save_config()

    def _find_aapt_in_build_tools(self, build_tools_dir):
        """Find aapt executable in build-tools directory."""
        if not os.path.exists(build_tools_dir):
            return None
        
        # Check root of build-tools first
        aapt_root = os.path.join(build_tools_dir, "aapt.exe")
        aapt2_root = os.path.join(build_tools_dir, "aapt2.exe")
        if os.path.exists(aapt_root):
            return aapt_root
        if os.path.exists(aapt2_root):
            return aapt2_root
        
        # Look for aapt or aapt2 in build-tools subdirectories
        if os.path.isdir(build_tools_dir):
            for item in os.listdir(build_tools_dir):
                item_path = os.path.join(build_tools_dir, item)
                if os.path.isdir(item_path):
                    aapt = os.path.join(item_path, "aapt.exe")
                    aapt2 = os.path.join(item_path, "aapt2.exe")
                    if os.path.exists(aapt):
                        return aapt
                    if os.path.exists(aapt2):
                        return aapt2
        
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
            bundled_adb = os.path.join(self.app_dir, "platform-tools", "adb.exe")
            if os.path.exists(bundled_adb):
                return bundled_adb
        # Fall back to configured path or system PATH
        return path or "adb"

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
            build_tools_dir = os.path.join(self.app_dir, "build-tools")
            bundled_aapt = self._find_aapt_in_build_tools(build_tools_dir)
            if bundled_aapt:
                return bundled_aapt
        # Fall back to configured path or system PATH
        if path:
            return path
        # Try to find in PATH
        return shutil.which("aapt") or shutil.which("aapt2") or ""

    @aapt_path.setter
    def aapt_path(self, value):
        """Set the AAPT executable path."""
        self.set("aapt_path", value)