import os
import sys
import shutil
import subprocess

def build():
    print("=== [1/4] Generating App Icons ===")
    from create_icon import create_app_icon
    create_app_icon(".")

    print("=== [2/4] Locating Full FFmpeg & FFprobe Binaries ===")
    from engine import find_ffmpeg_path
    raw_ffmpeg = find_ffmpeg_path()
    ffmpeg_bin = None
    ffprobe_bin = None

    if raw_ffmpeg:
        ffmpeg_bin = os.path.realpath(raw_ffmpeg)
        print(f"Target FFmpeg binary: {ffmpeg_bin} (Size: {os.path.getsize(ffmpeg_bin):,} bytes)")

        probe_path = os.path.join(os.path.dirname(ffmpeg_bin), "ffprobe.exe")
        if os.path.isfile(probe_path):
            ffprobe_bin = os.path.realpath(probe_path)
            print(f"Target FFprobe binary: {ffprobe_bin} (Size: {os.path.getsize(ffprobe_bin):,} bytes)")
    else:
        print("Warning: FFmpeg not detected.")

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
    ]

    # Embed ffmpeg and ffprobe directly inside the single .exe
    if ffmpeg_bin and os.path.isfile(ffmpeg_bin):
        pyinstaller_cmd.extend(["--add-binary", f"{ffmpeg_bin};."])
    if ffprobe_bin and os.path.isfile(ffprobe_bin):
        pyinstaller_cmd.extend(["--add-binary", f"{ffprobe_bin};."])

    pyinstaller_cmd.append("main.py")

    print("Executing command:", " ".join(pyinstaller_cmd))
    result = subprocess.run(pyinstaller_cmd)
    if result.returncode != 0:
        print("PyInstaller build failed!")
        sys.exit(result.returncode)

    single_exe_path = os.path.abspath(os.path.join("dist", "MediaGrabPro.exe"))
    print("\n" + "="*60)
    print(" BUILD SUCCESSFUL! (FULLY SELF-CONTAINED STANDALONE EXE)")
    print(f" Standalone File: {single_exe_path}")
    if os.path.isfile(single_exe_path):
        size_mb = os.path.getsize(single_exe_path) / (1024 * 1024)
        print(f" File Size: {size_mb:.2f} MB")
    print("="*60)

if __name__ == "__main__":
    build()
