import os
import sys
import subprocess
import shutil
import platform

def clean_build():
    """Clean build and dist directories."""
    dirs_to_clean = ['build', 'dist']
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"Cleaning {d}...")
            shutil.rmtree(d)

def install_requirements():
    """Install required packages."""
    print("Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def build_windows():
    """Run PyInstaller for Windows."""
    print("Building for Windows...")
    subprocess.check_call(["pyinstaller", "--noconfirm", "build_windows.spec"])

def build_mac():
    """Run PyInstaller for macOS."""
    print("Building for macOS...")
    # Ensure we are on macOS
    if platform.system() != "Darwin":
        print("Error: Must be on macOS to build for macOS.")
        return
    
    # Check if we are on Apple Silicon
    is_arm64 = platform.machine() == "arm64"
    print(f"Detected architecture: {platform.machine()}")
    
    subprocess.check_call(["pyinstaller", "--noconfirm", "build_mac.spec"])

def main():
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
    else:
        command = "build"

    try:
        if command == "clean":
            clean_build()
        elif command == "install":
            install_requirements()
        elif command == "build":
            # Determine platform
            current_os = platform.system()
            if current_os == "Windows":
                build_windows()
            elif current_os == "Darwin":
                build_mac()
            else:
                print(f"Unsupported OS: {current_os}")
        else:
            print(f"Unknown command: {command}")
            print("Usage: python build_app.py [clean|install|build]")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
