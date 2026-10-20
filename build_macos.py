import os
import sys
import shutil
import subprocess
import platform
import urllib.request
import zipfile
import tarfile

def download_mac_ffmpeg(dest_dir="."):
    """Download static ffmpeg binary for macOS if not present."""
    ffmpeg_bin = os.path.join(dest_dir, "ffmpeg")
    if os.path.isfile(ffmpeg_bin) and os.access(ffmpeg_bin, os.X_OK):
        print(f"Local macOS FFmpeg already exists at: {ffmpeg_bin}")
        return ffmpeg_bin

    # Check system PATH / Homebrew first
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        print(f"Found system FFmpeg at: {system_ffmpeg}")
        return system_ffmpeg
    for p in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if os.path.isfile(p):
            print(f"Found Homebrew FFmpeg at: {p}")
            return p

    # Download prebuilt static ffmpeg binary
    arch = platform.machine().lower()
    print(f"Downloading static FFmpeg for macOS ({arch})...")
    # GitHub release static build for macOS (Universal / ARM64 / x86_64)
    # Using dependable eugenware or evermeet static build
    url = "https://evermeet.cx/ffmpeg/getrelease/zip"
    zip_path = os.path.join(dest_dir, "ffmpeg_mac.zip")
    try:
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        if os.path.isfile(ffmpeg_bin):
            os.chmod(ffmpeg_bin, 0o755)
            print(f"FFmpeg downloaded and unpacked to: {ffmpeg_bin}")
        if os.path.isfile(zip_path):
            os.remove(zip_path)
        return ffmpeg_bin
    except Exception as e:
        print(f"Automatic FFmpeg download notice: {e}")
        print("Please ensure 'brew install ffmpeg' or place 'ffmpeg' binary in current folder.")
        return None

def build():
    if sys.platform != "darwin":
        print("="*60)
        print("NOTICE: PyInstaller must be executed directly on macOS")
        print("to compile native Mach-O binaries (.app / .dmg).")
        print("You can run this script on any Mac, or use GitHub Actions!")
        print("="*60)

    print("=== [1/4] Generating App Icons (ICNS & PNG) ===")
    from create_icon import create_app_icon
    create_app_icon(".")

    print("=== [2/4] Locating macOS FFmpeg ===")
    from engine import find_ffmpeg_path
    ffmpeg_bin = find_ffmpeg_path()
    ffprobe_bin = None

    if not ffmpeg_bin and sys.platform == "darwin":
        ffmpeg_bin = download_mac_ffmpeg(".")

    if ffmpeg_bin:
        print(f"Using FFmpeg at: {ffmpeg_bin}")
        probe_candidate = os.path.join(os.path.dirname(ffmpeg_bin), "ffprobe")
        if os.path.isfile(probe_candidate):
            ffprobe_bin = probe_candidate
            print(f"Using FFprobe at: {ffprobe_bin}")
    else:
        print("Warning: FFmpeg not detected. Download will work with YouTube formats <= 720p.")

    print("=== [3/4] Running PyInstaller for macOS ===")
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",                 # macOS .app GUI mode
        "--name", "MediaGrabPro",
        "--icon", "app_icon.icns",
        "--collect-all", "customtkinter",
        "--collect-all", "yt_dlp",
        "--collect-all", "PIL",
        "--add-data", "app_icon.icns:.",
        "--add-data", "app_icon.png:.",
    ]

    # Add ffmpeg binary if present
    if ffmpeg_bin and os.path.isfile(ffmpeg_bin):
        pyinstaller_cmd.extend(["--add-binary", f"{ffmpeg_bin}:."])
    if ffprobe_bin and os.path.isfile(ffprobe_bin):
        pyinstaller_cmd.extend(["--add-binary", f"{ffprobe_bin}:."])

    pyinstaller_cmd.append("main.py")

    print("Executing command:", " ".join(pyinstaller_cmd))
    res = subprocess.run(pyinstaller_cmd)
    if res.returncode != 0:
        print("PyInstaller build failed!")
        sys.exit(res.returncode)

    app_path = os.path.abspath(os.path.join("dist", "MediaGrabPro.app"))

    # Remove macOS quarantine flags if running on Mac
    if sys.platform == "darwin" and os.path.isdir(app_path):
        print("=== [4/4] Removing Gatekeeper Quarantine & Creating DMG ===")
        subprocess.run(["xattr", "-cr", app_path])

        dmg_path = os.path.abspath(os.path.join("dist", "MediaGrabPro-macOS.dmg"))
        if os.path.isfile(dmg_path):
            os.remove(dmg_path)

        # Create single-file DMG disk image using hdiutil
        try:
            hdiutil_cmd = [
                "hdiutil", "create",
                "-volname", "MediaGrabPro",
                "-srcfolder", app_path,
                "-ov",
                "-format", "UDZO",
                dmg_path
            ]
            print("Creating DMG disk image:", " ".join(hdiutil_cmd))
            subprocess.run(hdiutil_cmd, check=True)
            print(f"\nCreated Single-file macOS DMG: {dmg_path}")
        except Exception as e:
            print(f"DMG creation note: {e}")

    print("\n" + "="*60)
    print(" BUILD SUCCESSFUL! ")
    print(f" macOS App Bundle: {app_path}")
    print("="*60)

if __name__ == "__main__":
    build()
