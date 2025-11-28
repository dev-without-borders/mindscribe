import sys
import subprocess
import importlib.metadata
import os
import shutil

# Name of requirements-file
REQ_FILE = "requirements.txt"
# Download-URL for FFmpeg (Windows Builds)
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

def get_installed_packages():
    """Returns a set of all installed package names (lowercase)."""
    try:
        return {dist.metadata['Name'].lower() for dist in importlib.metadata.distributions()}
    except Exception:
        return set()

def parse_requirements(filename):
    """Reads requirements.txt and extracts package names."""
    required = []
    if not os.path.exists(filename):
        print(f"ERROR: {filename} not found!")
        return []
    
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Extract package names (everything before ==, >=, etc.)
            pkg_name = line.split('=')[0].split('>')[0].split('<')[0].strip()
            required.append(pkg_name.lower())
    return required

def check_python_dependencies():
    print("--- 1. Checking Python Packages ---")
    installed_pkgs = get_installed_packages()
    required_pkgs = parse_requirements(REQ_FILE)
    
    if not required_pkgs:
        print("No packages found in requirements.txt.")
        return True

    missing = [pkg for pkg in required_pkgs if pkg not in installed_pkgs]

    if missing:
        print(f"WARNING: The following packages are missing:")
        for pkg in missing:
            print(f" - {pkg}")
        
        print("\nDo you want to install the missing packages now? (y/n)")
        choice = input("Choice: ").lower()
        
        if choice in ['j', 'y']:
            print("\nStarting installation via pip...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQ_FILE])
                print("\nInstallation complete.")
                return True
            except subprocess.CalledProcessError:
                print("\nERROR during installation.")
                return False
        else:
            return False
    else:
        print("All Python dependencies are installed.")
        return True

def check_ffmpeg():
    print("\n--- 2. Checking FFmpeg ---")
    
    # 1. Check: Is it in the system PATH?
    ffmpeg_path = shutil.which("ffmpeg")
    
    # 2. Check: Is it directly in the current folder? (If not in PATH)
    if not ffmpeg_path:
        local_exe = os.path.join(os.getcwd(), "ffmpeg.exe")
        if os.path.exists(local_exe):
            ffmpeg_path = local_exe

    if ffmpeg_path:
        print(f"[OK] FFmpeg gefunden: {ffmpeg_path}")
        try:
            # Briefly check version
            result = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True)
            version_line = result.stdout.split('\n')[0]
            print(f"     Version: {version_line}")
        except Exception as e:
            print(f"     Warning: Could not read version ({e})")
        return True
    else:
        print("[ERROR] FFmpeg was NOT found!")
        print("Whisper requires FFmpeg to process audio files.")
        print("-" * 50)
        print("SOLUTION:")
        print(f"1. Download it here: {FFMPEG_URL}")
        print("2. Unzip the downloaded file.")
        print("3. Look for 'ffmpeg.exe' in the 'bin' folder.")
        print("4. Copy 'ffmpeg.exe' directly into this project folder.")
        print("-" * 50)
        return False

def check_cuda():
    print("\n--- 3. Checking GPU / CUDA ---")
    try:
        import torch
        print(f"PyTorch Version: {torch.__version__}")
        
        if torch.cuda.is_available():
            print(f"[OK] CUDA available: Yes")
            print(f"     Device: {torch.cuda.get_device_name(0)}")
        else:
            print("[WARNING] CUDA available: No")
            print("     Script will run on CPU (slow).")
            print("     If you have an NVIDIA GPU, reinstall PyTorch with CUDA support.")
            
    except ImportError:
        print("[ERROR] Could not import 'torch'.")
    except Exception as e:
        print(f"[ERROR] Error during GPU check: {e}")

if __name__ == "__main__":
    deps_ok = check_python_dependencies()
    ffmpeg_ok = check_ffmpeg()
    
    if deps_ok:
        check_cuda()
    
    print("\nCheck finished.")
    if not ffmpeg_ok:
        print("ATTENTION: FFmpeg is still missing!")
        
    input("\nPress ENTER to close the window...")
