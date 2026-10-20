import os
import sys
import shutil
import subprocess
import urllib.request
import zipfile

def ensure_windows_ffmpeg(dest_dir="."):
    """Finds existing FFmpeg/FFprobe or downloads official static Windows build."""
    from engine import find_ffmpeg_path
    raw_ffmpeg = find_ffmpeg_path()
    ffmpeg_bin = None
    ffprobe_bin = None

    if raw_ffmpeg:
        real_ff = os.path.realpath(raw_ffmpeg)
        if os.path.isfile(real_ff):
            ffmpeg_bin = real_ff
            probe_candidate = os.path.join(os.path.dirname(real_ff), "ffprobe.exe")
            if os.path.isfile(probe_candidate):
                ffprobe_bin = os.path.realpath(probe_candidate)

    # Check local destination folder
    local_ff = os.path.abspath(os.path.join(dest_dir, "ffmpeg.exe"))
    local_probe = os.path.abspath(os.path.join(dest_dir, "ffprobe.exe"))
    if os.path.isfile(local_ff) and os.path.isfile(local_probe):
        return local_ff, local_probe

    if ffmpeg_bin and ffprobe_bin:
        return ffmpeg_bin, ffprobe_bin

    # If missing, download official standalone static build
    print("FFmpeg/FFprobe not fully detected. Downloading official static build for Windows...")
    zip_url = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    temp_zip = os.path.join(dest_dir, "ffmpeg_download.zip")

    try:
        print(f"Downloading from {zip_url} ...")
        urllib.request.urlretrieve(zip_url, temp_zip)
        print("Extracting FFmpeg binaries...")
        with zipfile.ZipFile(temp_zip, 'r') as z:
            for member in z.namelist():
                if member.endswith("ffmpeg.exe"):
                    with z.open(member) as source, open(local_ff, "wb") as target:
                        shutil.copyfileobj(source, target)
                elif member.endswith("ffprobe.exe"):
                    with z.open(member) as source, open(local_probe, "wb") as target:
                        shutil.copyfileobj(source, target)

        if os.path.isfile(temp_zip):
            os.remove(temp_zip)

        if os.path.isfile(local_ff) and os.path.isfile(local_probe):
            print(f"Extracted FFmpeg: {local_ff} ({os.path.getsize(local_ff):,} bytes)")
            print(f"Extracted FFprobe: {local_probe} ({os.path.getsize(local_probe):,} bytes)")
            return local_ff, local_probe
    except Exception as e:
        print(f"Failed to auto-download Windows FFmpeg: {e}")

    return ffmpeg_bin, ffprobe_bin

def build():
    print("=== [1/4] Generating App Icons ===")
    from create_icon import create_app_icon
    create_app_icon(".")

    print("=== [2/4] Locating Full FFmpeg & FFprobe Binaries ===")
    ffmpeg_bin, ffprobe_bin = ensure_windows_ffmpeg(".")

    if not ffmpeg_bin or not os.path.isfile(ffmpeg_bin):
        raise RuntimeError("CRITICAL ERROR: ffmpeg.exe is missing! Cannot proceed without FFmpeg.")
    if not ffprobe_bin or not os.path.isfile(ffprobe_bin):
        raise RuntimeError("CRITICAL ERROR: ffprobe.exe is missing! Cannot proceed without FFprobe.")

    print(f"Target FFmpeg binary: {ffmpeg_bin} (Size: {os.path.getsize(ffmpeg_bin):,} bytes)")
    print(f"Target FFprobe binary: {ffprobe_bin} (Size: {os.path.getsize(ffprobe_bin):,} bytes)")

    print("=== [3/4] Running PyInstaller (--onefile mode with Embedded FFmpeg) ===")
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",         # Single standalone executable
        "--windowed",        # No black console window
        "--name", "MediaGrabPro",
        "--icon", "app_icon.ico",
        "--collect-all", "customtkinter",
        "--collect-all", "yt_dlp",
        "--collect-all", "PIL",
        "--add-data", "app_icon.ico;.",
        "--add-data", "app_icon.png;.",
        "--add-binary", f"{ffmpeg_bin};.",
        "--add-binary", f"{ffprobe_bin};.",
        "main.py"
    ]

    print("Executing command:", " ".join(pyinstaller_cmd))
    result = subprocess.run(pyinstaller_cmd)
    if result.returncode != 0:
        print("PyInstaller build failed!")
        sys.exit(result.returncode)

    single_exe_path = os.path.abspath(os.path.join("dist", "MediaGrabPro.exe"))
    if not os.path.isfile(single_exe_path):
        raise RuntimeError(f"CRITICAL ERROR: Output file {single_exe_path} was not created!")

    size_mb = os.path.getsize(single_exe_path) / (1024 * 1024)
    print("\n" + "="*60)
    print(" BUILD SUCCESSFUL! (FULLY SELF-CONTAINED STANDALONE EXE)")
    print(f" Standalone File: {single_exe_path}")
    print(f" File Size: {size_mb:.2f} MB")
    print("="*60)

    # Verification: Must be > 100 MB because FFmpeg + FFprobe are embedded
    if size_mb < 80.0:
        raise RuntimeError(f"VALIDATION FAILED: Executable size is only {size_mb:.2f} MB! FFmpeg binaries were not properly embedded!")

if __name__ == "__main__":
    build()
