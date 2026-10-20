import os
import sys
import shutil
import subprocess
import platform
import urllib.request
import gzip

def download_mac_binaries(dest_dir="."):
    """
    Downloads static standalone FFmpeg and FFprobe binaries for macOS
    and creates Universal 2 binaries (runs natively on Apple Silicon and Intel).
    """
    ffmpeg_final = os.path.join(dest_dir, "ffmpeg")
    ffprobe_final = os.path.join(dest_dir, "ffprobe")

    if os.path.isfile(ffmpeg_final) and os.access(ffmpeg_final, os.X_OK):
        print(f"macOS FFmpeg binary already present at: {ffmpeg_final}")
        return ffmpeg_final, ffprobe_final if os.path.isfile(ffprobe_final) else None

    tag = "b6.1.1"
    base_url = f"https://github.com/eugeneware/ffmpeg-static/releases/download/{tag}"

    print("Downloading standalone static FFmpeg & FFprobe for macOS (Universal 2)...")
    try:
        # Download arm64 and x64 builds
        for tool in ["ffmpeg", "ffprobe"]:
            arm64_file = os.path.join(dest_dir, f"{tool}-arm64")
            x64_file = os.path.join(dest_dir, f"{tool}-x64")
            out_file = os.path.join(dest_dir, tool)

            print(f"Fetching {tool} for Apple Silicon (arm64)...")
            urllib.request.urlretrieve(f"{base_url}/{tool}-darwin-arm64", arm64_file)
            os.chmod(arm64_file, 0o755)

            print(f"Fetching {tool} for Intel (x64)...")
            urllib.request.urlretrieve(f"{base_url}/{tool}-darwin-x64", x64_file)
            os.chmod(x64_file, 0o755)

            # Combine into Universal binary using lipo if running on macOS
            if shutil.which("lipo"):
                print(f"Combining {tool} into Universal 2 binary with lipo...")
                subprocess.run(["lipo", "-create", "-output", out_file, arm64_file, x64_file], check=True)
                os.chmod(out_file, 0o755)
                # Cleanup temp single-arch files
                if os.path.isfile(arm64_file): os.remove(arm64_file)
                if os.path.isfile(x64_file): os.remove(x64_file)
            else:
                # Fallback to local architecture
                arch = platform.machine().lower()
                chosen = arm64_file if "arm" in arch or "aarch" in arch else x64_file
                shutil.move(chosen, out_file)
                os.chmod(out_file, 0o755)

        return ffmpeg_final, ffprobe_final
    except Exception as e:
        print(f"Notice during static FFmpeg download: {e}")
        # Fallback to system / homebrew ffmpeg
        sys_ffmpeg = shutil.which("ffmpeg")
        return sys_ffmpeg, shutil.which("ffprobe")

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

    print("=== [2/4] Preparing Embedded macOS FFmpeg & FFprobe ===")
    ffmpeg_bin, ffprobe_bin = download_mac_binaries(".")

    if ffmpeg_bin and os.path.isfile(ffmpeg_bin):
        print(f"Embedded FFmpeg binary: {ffmpeg_bin} ({os.path.getsize(ffmpeg_bin):,} bytes)")
    if ffprobe_bin and os.path.isfile(ffprobe_bin):
        print(f"Embedded FFprobe binary: {ffprobe_bin} ({os.path.getsize(ffprobe_bin):,} bytes)")

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

    # Embed standalone static FFmpeg binaries directly inside the .app bundle
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

    # Remove macOS quarantine flags & package into single-file DMG
    if sys.platform == "darwin" and os.path.isdir(app_path):
        print("=== [4/4] Removing Gatekeeper Quarantine & Packaging into DMG ===")
        subprocess.run(["xattr", "-cr", app_path])

        # Also copy ffmpeg directly inside Contents/MacOS just in case
        macos_dir = os.path.join(app_path, "Contents", "MacOS")
        if os.path.isdir(macos_dir) and ffmpeg_bin and os.path.isfile(ffmpeg_bin):
            dest_ff = os.path.join(macos_dir, "ffmpeg")
            if not os.path.isfile(dest_ff):
                shutil.copy2(ffmpeg_bin, dest_ff)
                os.chmod(dest_ff, 0o755)

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
            print(f"\nCreated Single-file macOS DMG (with embedded FFmpeg): {dmg_path}")
            if os.path.isfile(dmg_path):
                print(f"DMG Size: {os.path.getsize(dmg_path) / (1024*1024):.2f} MB")
        except Exception as e:
            print(f"DMG creation note: {e}")

    print("\n" + "="*60)
    print(" BUILD SUCCESSFUL! ")
    print(f" macOS App Bundle: {app_path}")
    print("="*60)

if __name__ == "__main__":
    build()
