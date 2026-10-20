# MediaGrab Pro ⚡

<p align="center">
  <img src="app_icon.png" width="128" height="128" alt="MediaGrab Pro Logo" />
</p>

<p align="center">
  <strong>Universal Video & Audio Downloader for YouTube, Facebook, Reels, TikTok, Instagram, and X (Twitter)</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-blue?style=flat-square" alt="Platform" />
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-green?style=flat-square" alt="Python" />
  <img src="https://img.shields.io/badge/FFmpeg-Embedded-red?style=flat-square" alt="FFmpeg" />
  <img src="https://img.shields.io/badge/License-MIT-purple?style=flat-square" alt="License" />
</p>

---

## ✨ Features

- **🎬 Dynamic Video Quality Selection**: Inspects and extracts the actual available resolutions from the source video (up to 4K UHD, 2K QHD, 1080p 60fps, 720p HD, 480p, and 360p).
- **🎵 High-Quality Audio Extraction**: Download audio-only tracks as **MP3** (320 kbps, 256 kbps, 192 kbps, 128 kbps) or original **M4A (AAC)**.
- **🌐 Wide Platform Support**:
  - 🔴 **YouTube**: Videos, Shorts, and Live replays.
  - 🔵 **Facebook**: Standard Videos, Facebook Watch, and Reels.
  - 🟣 **Instagram**: Reels, Video posts, and Stories.
  - 🎵 **TikTok**: HD videos without watermark.
  - ✖️ **X (Twitter)** & **Threads**.
- **🎨 Modern Dark UI / UX**:
  - Built with CustomTkinter for a sleek dark aesthetic.
  - Live video metadata preview (High-res thumbnail, title, uploader, duration).
  - Real-time download progress bar with speed (`MB/s`), downloaded/total size, and ETA.
  - Download history with 1-click play and folder reveal.
- **⌨️ Universal Clipboard Support**: Seamless `Ctrl+V` (Windows) and `Cmd+V` (macOS) even when typing in non-English keyboard layouts (such as Thai).
- **📦 100% Standalone & Portable**: Includes embedded FFmpeg. No extra installations or dependencies required on the target machine!

---

## 📥 Download Prebuilt Binaries

Go to the [Releases](https://github.com/iKimz/mediagrab/releases) page to download the latest version:

| Platform | Download File | Notes |
|---|---|---|
| **Windows** | `MediaGrabPro-windows-x64.exe` | Single standalone `.exe` (Self-contained, includes FFmpeg) |
| **macOS** | `MediaGrabPro-macOS.dmg` | Single-file DMG disk image for Apple Silicon & Intel |

---

## 🚀 Running from Source

### Prerequisites
- Python 3.10 or higher
- FFmpeg installed in system PATH (or placed next to the project)

### Setup & Launch
```bash
# Clone the repository
git clone https://github.com/iKimz/mediagrab.git
cd mediagrab

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

---

## 🛠️ Building Standalone Binaries

### Building on Windows (.exe)
```bash
python build.py
```
Output executable: `dist/MediaGrabPro.exe`

### Building on macOS (.app & .dmg)
```bash
bash build_macos.sh
# or
python3 build_macos.py
```
Output disk image: `dist/MediaGrabPro-macOS.dmg`

> **Note for macOS Gatekeeper**:  
> If macOS displays *"App is damaged or can't be opened"*, run this command in Terminal to clear the quarantine flag:  
> ```bash
> xattr -cr /Applications/MediaGrabPro.app
> ```

---

## 📁 Project Structure

```
├── main.py                  # Application entry point
├── ui.py                    # Modern CustomTkinter GUI layout & event handlers
├── engine.py                # yt-dlp wrapper with multi-platform FFmpeg detection
├── create_icon.py           # Generates .ico, .icns, and .png application icons
├── build.py                 # PyInstaller packaging script for Windows (Embedded FFmpeg)
├── build_macos.py           # PyInstaller packaging script for macOS (.app & .dmg)
├── build_macos.sh           # 1-click shell build script for macOS
├── MediaGrabPro.command     # Double-clickable macOS launcher script
├── requirements.txt         # Python project dependencies
├── .github/workflows/
│   └── release.yml          # Automated CI/CD for Windows & macOS GitHub Releases
└── README.md                # Project documentation
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
