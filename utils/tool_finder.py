import os
import shutil
import sys
import subprocess


def find_aapt(app_dir=None):
    """
    Find aapt or aapt2 executable in bundled tools, system PATH, 
    or common Android SDK locations.
    """
    aapt_name = "aapt.exe" if os.name == "nt" else "aapt"
    aapt2_name = "aapt2.exe" if os.name == "nt" else "aapt2"

    # 1. Try bundled tools first
    bundled_dir = None
    if getattr(sys, 'frozen', False):
        bundled_dir = sys._MEIPASS
    elif app_dir:
        bundled_dir = app_dir
    
    if bundled_dir:
        build_tools_dir = os.path.join(bundled_dir, "build-tools")
        bundled_aapt = find_aapt_in_build_tools(build_tools_dir)
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
            found_aapt = find_aapt_in_build_tools(build_tools)
            if found_aapt:
                return found_aapt

    return ""


def find_aapt_in_build_tools(build_tools_dir):
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


def find_adb(app_dir=None):
    """
    Find adb executable in bundled tools, system PATH, 
    or common Android SDK locations.
    """
    adb_name = "adb.exe" if os.name == "nt" else "adb"

    # 1. Try bundled tools first
    bundled_dir = None
    if getattr(sys, 'frozen', False):
        bundled_dir = sys._MEIPASS
    elif app_dir:
        bundled_dir = app_dir
    
    if bundled_dir:
        platform_tools_dir = os.path.join(bundled_dir, "platform-tools")
        bundled_adb = os.path.join(platform_tools_dir, adb_name)
        if os.path.exists(bundled_adb):
            return bundled_adb

    # 2. Try system PATH
    adb_path = shutil.which("adb")
    if adb_path:
        return adb_path

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

    return "adb"  # Fallback to just "adb"
