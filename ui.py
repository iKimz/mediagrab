import os
import sys
import io
import subprocess
import threading
import requests
import urllib3
from PIL import Image
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox

from engine import DownloadEngine, find_ffmpeg_path

# Suppress insecure SSL request warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

PLATFORM_COLORS = {
    "YouTube": ("#ef4444", "🔴"),
    "Facebook": ("#1877f2", "🔵"),
    "Instagram": ("#d946ef", "🟣"),
    "TikTok": ("#06b6d4", "🎵"),
    "X (Twitter)": ("#71717a", "✖️"),
    "Threads": ("#a855f7", "🧵"),
    "Web Video": ("#6366f1", "🌐"),
}

def open_file_crossplatform(filepath):
    """Open a media file using default system player on Windows, macOS, or Linux."""
    if not filepath or not os.path.exists(filepath):
        return
    if sys.platform.startswith('win'):
        os.startfile(filepath)
    elif sys.platform == 'darwin':
        subprocess.run(['open', filepath])
    else:
        subprocess.run(['xdg-open', filepath])

def reveal_in_folder_crossplatform(filepath):
    """Reveal a file or folder in Finder / Explorer / File Manager."""
    if not filepath:
        return
    if sys.platform.startswith('win'):
        if os.path.isfile(filepath):
            subprocess.run(f'explorer /select,"{os.path.abspath(filepath)}"', shell=True)
        else:
            os.startfile(filepath)
    elif sys.platform == 'darwin':
        if os.path.isfile(filepath):
            subprocess.run(['open', '-R', filepath])
        else:
            subprocess.run(['open', filepath])
    else:
        target = os.path.dirname(filepath) if os.path.isfile(filepath) else filepath
        subprocess.run(['xdg-open', target])

def setup_universal_shortcuts(widget):
    """
    Enables Ctrl+V, Ctrl+C, Ctrl+A, Ctrl+X (and Cmd on macOS)
    even when Thai or non-English keyboard layout is active, plus Right-Click Context Menu.
    """
    target = getattr(widget, "_entry", widget)

    def on_key(event):
        # Control (0x0004) or Command on Mac (0x0008)
        modifier_pressed = bool(event.state & 0x0004) or bool(event.state & 0x0008) or (event.state & 4 != 0)
        if not modifier_pressed:
            return

        # Keycode 86 = V (Paste)
        if event.keycode == 86 or event.char == '\x16':
            try:
                text = target.clipboard_get()
                try:
                    target.delete("sel.first", "sel.last")
                except Exception:
                    pass
                target.insert("insert", text)
                return "break"
            except Exception:
                pass
        # Keycode 65 = A (Select All)
        elif event.keycode == 65 or event.char == '\x01':
            target.select_range(0, "end")
            target.icursor("end")
            return "break"
        # Keycode 67 = C (Copy)
        elif event.keycode == 67 or event.char == '\x03':
            try:
                sel = target.selection_get()
                target.clipboard_clear()
                target.clipboard_append(sel)
                return "break"
            except Exception:
                pass
        # Keycode 88 = X (Cut)
        elif event.keycode == 88 or event.char == '\x18':
            try:
                sel = target.selection_get()
                target.clipboard_clear()
                target.clipboard_append(sel)
                target.delete("sel.first", "sel.last")
                return "break"
            except Exception:
                pass

    target.bind("<Key>", on_key, add="+")
    target.bind("<Control-v>", lambda e: on_key(e), add="+")
    target.bind("<Control-V>", lambda e: on_key(e), add="+")
    target.bind("<Control-a>", lambda e: on_key(e), add="+")
    target.bind("<Control-A>", lambda e: on_key(e), add="+")
    target.bind("<Control-c>", lambda e: on_key(e), add="+")
    target.bind("<Control-C>", lambda e: on_key(e), add="+")
    target.bind("<Control-x>", lambda e: on_key(e), add="+")
    target.bind("<Control-X>", lambda e: on_key(e), add="+")

    # macOS Command bindings
    target.bind("<Command-v>", lambda e: on_key(e), add="+")
    target.bind("<Command-V>", lambda e: on_key(e), add="+")
    target.bind("<Command-a>", lambda e: on_key(e), add="+")
    target.bind("<Command-A>", lambda e: on_key(e), add="+")
    target.bind("<Command-c>", lambda e: on_key(e), add="+")
    target.bind("<Command-C>", lambda e: on_key(e), add="+")
    target.bind("<Command-x>", lambda e: on_key(e), add="+")
    target.bind("<Command-X>", lambda e: on_key(e), add="+")

    # Right-click context menu
    menu = tk.Menu(target, tearoff=0, bg="#1e2538", fg="#f8fafc", activebackground="#6366f1", activeforeground="#ffffff")

    def do_paste():
        try:
            text = target.clipboard_get()
            try:
                target.delete("sel.first", "sel.last")
            except Exception:
                pass
            target.insert("insert", text)
        except Exception:
            pass

    def do_copy():
        try:
            sel = target.selection_get()
            target.clipboard_clear()
            target.clipboard_append(sel)
        except Exception:
            pass

    def do_cut():
        try:
            sel = target.selection_get()
            target.clipboard_clear()
            target.clipboard_append(sel)
            target.delete("sel.first", "sel.last")
        except Exception:
            pass

    def do_select_all():
        target.select_range(0, "end")
        target.icursor("end")

    def do_clear():
        target.delete(0, "end")

    menu.add_command(label="📋 Paste", command=do_paste)
    menu.add_command(label="📑 Copy", command=do_copy)
    menu.add_command(label="✂️ Cut", command=do_cut)
    menu.add_separator()
    menu.add_command(label="Select All", command=do_select_all)
    menu.add_command(label="Clear", command=do_clear)

    def show_context_menu(event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    target.bind("<Button-3>", show_context_menu)
    target.bind("<Button-2>", show_context_menu)
    target.bind("<Control-Button-1>", show_context_menu)


class MediaDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MediaGrab Pro - Universal Video & Audio Downloader")
        self.geometry("920x860")
        self.minsize(820, 750)

        # Apply icon if exists (cross-platform)
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "app_icon.ico")
        png_icon = os.path.join(base_dir, "app_icon.png")
        if sys.platform.startswith('win') and os.path.isfile(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        elif os.path.isfile(png_icon):
            try:
                icon_img = tk.PhotoImage(file=png_icon)
                self.iconphoto(True, icon_img)
            except Exception:
                pass

        self.engine = DownloadEngine()
        self.current_video_info = None
        self.download_history = []
        self.is_downloading = False
        self.last_downloaded_file = None
        self._current_thumb_image = None

        # Default save path
        user_download = os.path.join(os.path.expanduser("~"), "Downloads")
        self.save_dir = os.path.join(user_download, "MediaDownloads")
        os.makedirs(self.save_dir, exist_ok=True)

        self._build_ui()
        self._check_ffmpeg_status()

    def _build_ui(self):
        # Main scrollable canvas container
        self.main_container = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=15)

        # 1. Header Card
        self._build_header()

        # 2. URL Input Card (Clean: Only Entry + Fetch Video button)
        self._build_url_section()

        # 3. Video Metadata & Settings Card
        self._build_preview_settings_section()

        # 4. Save Directory Card
        self._build_save_directory_section()

        # 5. Download Progress & Control Card
        self._build_progress_section()

        # 6. Recent Downloads / History Card
        self._build_history_section()

    def _build_header(self):
        header_frame = ctk.CTkFrame(self.main_container, fg_color="#181c27", corner_radius=14, border_width=1, border_color="#2c3447")
        header_frame.pack(fill="x", pady=(0, 15), ipady=8, padx=5)

        top_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=6)

        # App title & subtitle
        title_box = ctk.CTkFrame(top_row, fg_color="transparent")
        title_box.pack(side="left")

        title_label = ctk.CTkLabel(
            title_box,
            text="⚡ MediaGrab Pro",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#f8fafc"
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            title_box,
            text="Download videos & audio from YouTube (4K/1080p), Facebook, Reels, TikTok, Instagram & X",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        subtitle_label.pack(anchor="w")

        # Right badges
        badge_box = ctk.CTkFrame(top_row, fg_color="transparent")
        badge_box.pack(side="right", padx=5)

        self.ffmpeg_badge = ctk.CTkLabel(
            badge_box,
            text="Checking FFmpeg...",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#334155",
            corner_radius=8,
            padx=10,
            pady=4,
            text_color="#f1f5f9"
        )
        self.ffmpeg_badge.pack(side="right")

    def _build_url_section(self):
        url_frame = ctk.CTkFrame(self.main_container, fg_color="#181c27", corner_radius=14, border_width=1, border_color="#2c3447")
        url_frame.pack(fill="x", pady=(0, 15), padx=5, ipady=8)

        lbl = ctk.CTkLabel(
            url_frame,
            text="🔗 Video URL:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f8fafc"
        )
        lbl.pack(anchor="w", padx=18, pady=(10, 6))

        input_row = ctk.CTkFrame(url_frame, fg_color="transparent")
        input_row.pack(fill="x", padx=16, pady=(0, 10))

        # Full-width Entry (Paste and Clear buttons removed per user request)
        self.url_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Paste video link here (YouTube, Facebook Reels, TikTok, Instagram, X...)",
            height=46,
            font=ctk.CTkFont(size=13),
            corner_radius=10,
            fg_color="#0f141f",
            border_color="#3b4661"
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self.on_fetch_clicked())

        # Enable Ctrl+V in Thai keyboard layout + Right-Click Context Menu
        setup_universal_shortcuts(self.url_entry)

        # Prominent Fetch Video button
        self.fetch_btn = ctk.CTkButton(
            input_row,
            text="🔍 Fetch Video",
            width=145,
            height=46,
            corner_radius=10,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.on_fetch_clicked
        )
        self.fetch_btn.pack(side="left")

        # Supported platforms tags
        tags_row = ctk.CTkFrame(url_frame, fg_color="transparent")
        tags_row.pack(fill="x", padx=18, pady=(0, 6))

        for name, (color, icon) in PLATFORM_COLORS.items():
            tag = ctk.CTkLabel(
                tags_row,
                text=f"{icon} {name}",
                font=ctk.CTkFont(size=11),
                fg_color="#1e2538",
                text_color="#cbd5e1",
                corner_radius=6,
                padx=8,
                pady=2
            )
            tag.pack(side="left", padx=(0, 6))

    def _build_preview_settings_section(self):
        self.preview_card = ctk.CTkFrame(self.main_container, fg_color="#181c27", corner_radius=14, border_width=1, border_color="#2c3447")
        self.preview_card.pack(fill="x", pady=(0, 15), padx=5, ipady=12)

        # Internal grid layout: Left for Thumbnail, Right for Info & Settings
        self.preview_grid = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.preview_grid.pack(fill="x", padx=16, pady=8)

        # Left Thumbnail Area
        self.thumb_container = ctk.CTkFrame(self.preview_grid, width=280, height=170, fg_color="#0e131d", corner_radius=12)
        self.thumb_container.pack(side="left", padx=(0, 18), fill="none")
        self.thumb_container.pack_propagate(False)

        self.thumb_label = ctk.CTkLabel(
            self.thumb_container,
            text="📷 Video thumbnail preview\n(Paste link & click Fetch Video)",
            font=ctk.CTkFont(size=12),
            text_color="#64748b"
        )
        self.thumb_label.pack(expand=True)

        # Right Info & Options Area
        self.info_container = ctk.CTkFrame(self.preview_grid, fg_color="transparent")
        self.info_container.pack(side="left", fill="both", expand=True)

        # Video Title
        self.video_title_label = ctk.CTkLabel(
            self.info_container,
            text="No video loaded yet",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#f8fafc",
            anchor="w",
            justify="left",
            wraplength=480
        )
        self.video_title_label.pack(anchor="w", pady=(0, 4))

        # Metadata Row (Platform badge, Author, Duration)
        self.meta_row = ctk.CTkFrame(self.info_container, fg_color="transparent")
        self.meta_row.pack(anchor="w", pady=(0, 12))

        self.platform_badge = ctk.CTkLabel(
            self.meta_row,
            text="--",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#334155",
            corner_radius=6,
            padx=8,
            pady=2,
            text_color="#e2e8f0"
        )
        self.platform_badge.pack(side="left", padx=(0, 8))

        self.author_label = ctk.CTkLabel(
            self.meta_row,
            text="Creator: --",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        self.author_label.pack(side="left", padx=(0, 12))

        self.duration_label = ctk.CTkLabel(
            self.meta_row,
            text="Duration: --:--",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        self.duration_label.pack(side="left")

        # Divider
        sep = ctk.CTkFrame(self.info_container, height=1, fg_color="#2c3447")
        sep.pack(fill="x", pady=(0, 12))

        # Download Mode Selector (Video MP4 vs Audio Only)
        mode_row = ctk.CTkFrame(self.info_container, fg_color="transparent")
        mode_row.pack(fill="x", pady=(0, 10))

        mode_lbl = ctk.CTkLabel(
            mode_row,
            text="Download Type:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#cbd5e1"
        )
        mode_lbl.pack(side="left", padx=(0, 12))

        self.mode_var = ctk.StringVar(value="video")
        self.mode_segmented = ctk.CTkSegmentedButton(
            mode_row,
            values=["🎬 Video (MP4)", "🎵 Audio Only"],
            command=self.on_mode_changed,
            font=ctk.CTkFont(size=12, weight="bold"),
            selected_color="#6366f1",
            selected_hover_color="#4f46e5",
            height=32
        )
        self.mode_segmented.set("🎬 Video (MP4)")
        self.mode_segmented.pack(side="left")

        # Video Quality Settings Frame
        self.video_settings_frame = ctk.CTkFrame(self.info_container, fg_color="transparent")
        self.video_settings_frame.pack(fill="x", pady=(0, 5))

        res_lbl = ctk.CTkLabel(
            self.video_settings_frame,
            text="Resolution:",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        res_lbl.pack(side="left", padx=(0, 10))

        self.resolution_combo = ctk.CTkComboBox(
            self.video_settings_frame,
            values=["⭐ Best Available Quality"],
            width=260,
            height=32,
            font=ctk.CTkFont(size=12),
            state="readonly"
        )
        self.resolution_combo.set("⭐ Best Available Quality")
        self.resolution_combo.pack(side="left")

        # Audio Settings Frame (Hidden by default)
        self.audio_settings_frame = ctk.CTkFrame(self.info_container, fg_color="transparent")

        audio_format_lbl = ctk.CTkLabel(
            self.audio_settings_frame,
            text="Audio Format:",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        audio_format_lbl.pack(side="left", padx=(0, 8))

        self.audio_format_combo = ctk.CTkComboBox(
            self.audio_settings_frame,
            values=["MP3", "M4A (AAC)"],
            width=110,
            height=32,
            font=ctk.CTkFont(size=12),
            state="readonly"
        )
        self.audio_format_combo.set("MP3")
        self.audio_format_combo.pack(side="left", padx=(0, 16))

        audio_bitrate_lbl = ctk.CTkLabel(
            self.audio_settings_frame,
            text="Audio Quality:",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        audio_bitrate_lbl.pack(side="left", padx=(0, 8))

        self.audio_bitrate_combo = ctk.CTkComboBox(
            self.audio_settings_frame,
            values=["320 kbps (High Quality)", "256 kbps", "192 kbps (Standard)", "128 kbps"],
            width=175,
            height=32,
            font=ctk.CTkFont(size=12),
            state="readonly"
        )
        self.audio_bitrate_combo.set("320 kbps (High Quality)")
        self.audio_bitrate_combo.pack(side="left")

    def _build_save_directory_section(self):
        dir_frame = ctk.CTkFrame(self.main_container, fg_color="#181c27", corner_radius=14, border_width=1, border_color="#2c3447")
        dir_frame.pack(fill="x", pady=(0, 15), padx=5, ipady=6)

        lbl = ctk.CTkLabel(
            dir_frame,
            text="📁 Save Location:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f8fafc"
        )
        lbl.pack(anchor="w", padx=18, pady=(8, 4))

        row = ctk.CTkFrame(dir_frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 8))

        self.dir_entry = ctk.CTkEntry(
            row,
            height=36,
            font=ctk.CTkFont(size=12),
            fg_color="#0f141f",
            border_color="#3b4661"
        )
        self.dir_entry.insert(0, self.save_dir)
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        setup_universal_shortcuts(self.dir_entry)

        browse_btn = ctk.CTkButton(
            row,
            text="📂 Browse",
            width=110,
            height=36,
            corner_radius=8,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.on_browse_directory
        )
        browse_btn.pack(side="left")

    def _build_progress_section(self):
        self.action_card = ctk.CTkFrame(self.main_container, fg_color="#181c27", corner_radius=14, border_width=1, border_color="#2c3447")
        self.action_card.pack(fill="x", pady=(0, 15), padx=5, ipady=12)

        # Buttons row
        btn_row = ctk.CTkFrame(self.action_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(4, 10))

        self.download_btn = ctk.CTkButton(
            btn_row,
            text="🚀 Download MP4 Video",
            height=46,
            corner_radius=10,
            fg_color="#ef4444",
            hover_color="#dc2626",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.on_download_clicked
        )
        self.download_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.cancel_btn = ctk.CTkButton(
            btn_row,
            text="⛔ Cancel",
            width=100,
            height=46,
            corner_radius=10,
            fg_color="#475569",
            hover_color="#64748b",
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled",
            command=self.on_cancel_clicked
        )
        self.cancel_btn.pack(side="left")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self.action_card,
            height=14,
            corner_radius=7,
            progress_color="#6366f1",
            fg_color="#0f141f"
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=18, pady=(4, 8))

        # Status & Stats Grid
        self.stats_row = ctk.CTkFrame(self.action_card, fg_color="transparent")
        self.stats_row.pack(fill="x", padx=18, pady=(0, 6))

        self.status_label = ctk.CTkLabel(
            self.stats_row,
            text="Ready to download",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.status_label.pack(side="left")

        self.stats_label = ctk.CTkLabel(
            self.stats_row,
            text="0% • -- MB/s • ETA: --",
            font=ctk.CTkFont(size=12),
            text_color="#cbd5e1"
        )
        self.stats_label.pack(side="right")

        # Post-download quick action buttons (Hidden until download finishes)
        self.post_download_row = ctk.CTkFrame(self.action_card, fg_color="transparent")
        
        self.open_file_btn = ctk.CTkButton(
            self.post_download_row,
            text="▶️ Play File",
            height=34,
            corner_radius=8,
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.on_open_downloaded_file
        )
        self.open_file_btn.pack(side="left", padx=(0, 8))

        self.open_folder_btn = ctk.CTkButton(
            self.post_download_row,
            text="📂 Open Folder",
            height=34,
            corner_radius=8,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.on_open_folder
        )
        self.open_folder_btn.pack(side="left")

    def _build_history_section(self):
        hist_card = ctk.CTkFrame(self.main_container, fg_color="#181c27", corner_radius=14, border_width=1, border_color="#2c3447")
        hist_card.pack(fill="x", pady=(0, 10), padx=5, ipady=8)

        head_row = ctk.CTkFrame(hist_card, fg_color="transparent")
        head_row.pack(fill="x", padx=18, pady=(8, 6))

        hist_title = ctk.CTkLabel(
            head_row,
            text="📋 Download History:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f8fafc"
        )
        hist_title.pack(side="left")

        self.history_count_lbl = ctk.CTkLabel(
            head_row,
            text="0 items",
            font=ctk.CTkFont(size=11),
            text_color="#64748b"
        )
        self.history_count_lbl.pack(side="right")

        self.history_container = ctk.CTkFrame(hist_card, fg_color="transparent")
        self.history_container.pack(fill="x", padx=18, pady=(0, 6))

        self.no_history_label = ctk.CTkLabel(
            self.history_container,
            text="No downloads in this session yet",
            font=ctk.CTkFont(size=12),
            text_color="#64748b"
        )
        self.no_history_label.pack(pady=8)

    def _check_ffmpeg_status(self):
        ffmpeg_bin = find_ffmpeg_path()
        if ffmpeg_bin:
            self.ffmpeg_badge.configure(
                text="🟢 FFmpeg: Ready",
                fg_color="#064e3b",
                text_color="#34d399"
            )
        else:
            self.ffmpeg_badge.configure(
                text="⚠️ FFmpeg: Not Found",
                fg_color="#7f1d1d",
                text_color="#f87171"
            )

    def reset_preview(self):
        self.current_video_info = None
        self._current_thumb_image = None
        self.video_title_label.configure(text="No video loaded yet")
        self.platform_badge.configure(text="--", fg_color="#334155")
        self.author_label.configure(text="Creator: --")
        self.duration_label.configure(text="Duration: --:--")
        self.thumb_label.configure(image=None, text="📷 Video thumbnail preview\n(Paste link & click Fetch Video)")
        self.thumb_label.image = None
        self.resolution_combo.configure(values=["⭐ Best Available Quality"])
        self.resolution_combo.set("⭐ Best Available Quality")
        self.progress_bar.set(0)
        self.status_label.configure(text="Ready to download", text_color="#94a3b8")
        self.stats_label.configure(text="0% • -- MB/s • ETA: --")
        self.post_download_row.pack_forget()

    def on_mode_changed(self, value):
        if "Video" in value:
            self.mode_var.set("video")
            self.audio_settings_frame.pack_forget()
            self.video_settings_frame.pack(fill="x", pady=(0, 5))
            self.download_btn.configure(text="🚀 Download MP4 Video", fg_color="#ef4444", hover_color="#dc2626")
        else:
            self.mode_var.set("audio")
            self.video_settings_frame.pack_forget()
            self.audio_settings_frame.pack(fill="x", pady=(0, 5))
            self.download_btn.configure(text="🎵 Download Audio", fg_color="#8b5cf6", hover_color="#7c3aed")

    def on_browse_directory(self):
        selected = filedialog.askdirectory(initialdir=self.save_dir)
        if selected:
            self.save_dir = selected
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, self.save_dir)

    def on_fetch_clicked(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please paste or enter a video link first.")
            return

        self.fetch_btn.configure(state="disabled", text="⏳ Fetching...")
        self.status_label.configure(text="Analyzing video link & available qualities...", text_color="#60a5fa")

        def run_fetch():
            try:
                info = self.engine.fetch_info(url)
                self.after(0, lambda: self._apply_fetched_info(info))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._handle_fetch_error(err_msg))

        threading.Thread(target=run_fetch, daemon=True).start()

    def _apply_fetched_info(self, info):
        self.fetch_btn.configure(state="normal", text="🔍 Fetch Video")
        self.status_label.configure(text="Video analyzed successfully! Ready to download.", text_color="#34d399")
        self.current_video_info = info

        # Title
        title = info.get("title") or "Unknown Video"
        self.video_title_label.configure(text=title)

        # Platform badge
        platform = info.get("platform", "Web Video")
        color, icon = PLATFORM_COLORS.get(platform, ("#6366f1", "🌐"))
        self.platform_badge.configure(text=f"{icon} {platform}", fg_color=color)

        # Author and duration
        author = info.get("author") or "Unknown"
        self.author_label.configure(text=f"Creator: {author[:25]}")
        self.duration_label.configure(text=f"Duration: {info.get('duration_str', '--:--')}")

        # Resolutions dropdown
        resolutions = info.get("resolutions", [])
        if resolutions:
            labels = [r["label"] for r in resolutions]
            self.resolution_combo.configure(values=labels)
            self.resolution_combo.set(labels[0])
        else:
            self.resolution_combo.configure(values=["⭐ Best Available Quality"])
            self.resolution_combo.set("⭐ Best Available Quality")

        # Load thumbnail asynchronously with fallbacks
        thumb_url = info.get("thumbnail_url")
        video_id = info.get("video_id")
        self._load_thumbnail_async(thumb_url, video_id)

    def _handle_fetch_error(self, err_msg):
        self.fetch_btn.configure(state="normal", text="🔍 Fetch Video")
        self.status_label.configure(text="Failed to fetch video. Please check URL.", text_color="#f87171")
        messagebox.showerror("Error", f"Failed to retrieve video details:\n{err_msg}")

    def _load_thumbnail_async(self, thumb_url, video_id=None):
        def load():
            # Build prioritized list of thumbnail URLs to try
            urls_to_try = []
            if thumb_url:
                urls_to_try.append(thumb_url)
            if video_id:
                urls_to_try.append(f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg")
                urls_to_try.append(f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg")
                urls_to_try.append(f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
            }

            for u in urls_to_try:
                if not u:
                    continue
                try:
                    resp = requests.get(u, headers=headers, timeout=8, verify=False)
                    if resp.status_code == 200 and len(resp.content) > 500:
                        pil_img = Image.open(io.BytesIO(resp.content))
                        pil_img = pil_img.convert("RGBA")
                        # Preserve aspect ratio to fit inside 280x160
                        pil_img.thumbnail((280, 160), Image.Resampling.LANCZOS)
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                        self.after(0, lambda img=ctk_img: self._set_thumbnail(img))
                        return
                except Exception:
                    continue

        threading.Thread(target=load, daemon=True).start()

    def _set_thumbnail(self, ctk_img):
        # Keep persistent reference to prevent Garbage Collector cleanup
        self._current_thumb_image = ctk_img
        self.thumb_label.configure(image=ctk_img, text="")
        self.thumb_label.image = ctk_img

    def on_download_clicked(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a valid video link.")
            return

        if self.is_downloading:
            return

        save_dir = self.dir_entry.get().strip()
        if not save_dir:
            save_dir = self.save_dir
        os.makedirs(save_dir, exist_ok=True)

        mode = self.mode_var.get()
        selected_height = None

        if mode == "video":
            selected_res_label = self.resolution_combo.get()
            if self.current_video_info and "resolutions" in self.current_video_info:
                for r in self.current_video_info["resolutions"]:
                    if r["label"] == selected_res_label:
                        selected_height = r["height"]
                        break

        # Audio settings
        audio_fmt = "mp3" if "MP3" in self.audio_format_combo.get() else "m4a"
        bitrate_raw = self.audio_bitrate_combo.get()
        bitrate = "320"
        if "256" in bitrate_raw: bitrate = "256"
        elif "192" in bitrate_raw: bitrate = "192"
        elif "128" in bitrate_raw: bitrate = "128"

        # UI state during download
        self.is_downloading = True
        self.download_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.fetch_btn.configure(state="disabled")
        self.post_download_row.pack_forget()
        self.progress_bar.set(0)
        self.status_label.configure(text="Starting download...", text_color="#60a5fa")
        self.stats_label.configure(text="0% • Connecting...")

        def on_progress(data):
            self.after(0, lambda: self._update_progress_ui(data))

        def on_complete(filepath):
            self.after(0, lambda: self._handle_download_complete(filepath))

        def on_error(err):
            self.after(0, lambda: self._handle_download_error(err))

        self.engine.start_download(
            url=url,
            output_dir=save_dir,
            mode=mode,
            height=selected_height,
            audio_codec=audio_fmt,
            audio_quality=bitrate,
            progress_callback=on_progress,
            complete_callback=on_complete,
            error_callback=on_error
        )

    def _update_progress_ui(self, data):
        percent = data.get("percent", 0.0)
        self.progress_bar.set(percent / 100.0)
        status_msg = data.get("message", "")
        self.status_label.configure(text=status_msg, text_color="#38bdf8")

        speed = data.get("speed_str", "--")
        eta = data.get("eta_str", "--")
        d_str = data.get("downloaded_str", "")
        t_str = data.get("total_str", "")

        stat_text = f"{percent:.1f}%"
        if d_str and t_str:
            stat_text += f" ({d_str} / {t_str})"
        if speed:
            stat_text += f" • {speed}"
        if eta:
            stat_text += f" • ETA: {eta}"

        self.stats_label.configure(text=stat_text)

    def _handle_download_complete(self, filepath):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.fetch_btn.configure(state="normal")
        self.progress_bar.set(1.0)

        filename = os.path.basename(filepath)
        self.last_downloaded_file = filepath

        self.status_label.configure(
            text="🎉 Download completed successfully!",
            text_color="#34d399"
        )
        self.stats_label.configure(text="100% Completed")

        # Show post-download action buttons
        self.post_download_row.pack(fill="x", padx=18, pady=(10, 4))

        # Add to history
        self._add_to_history(filename, filepath)

    def _handle_download_error(self, err_msg):
        self.is_downloading = False
        self.download_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        self.fetch_btn.configure(state="normal")

        if "cancelled" in err_msg.lower():
            self.status_label.configure(text="Download was cancelled.", text_color="#fbbf24")
            self.stats_label.configure(text="Cancelled by user")
        else:
            self.status_label.configure(text="Download failed.", text_color="#f87171")
            self.stats_label.configure(text="Error occurred")
            messagebox.showerror("Download Error", err_msg)

    def on_cancel_clicked(self):
        if self.is_downloading:
            self.engine.cancel()
            self.cancel_btn.configure(state="disabled")
            self.status_label.configure(text="Cancelling download...", text_color="#fbbf24")

    def on_open_downloaded_file(self):
        if self.last_downloaded_file and os.path.isfile(self.last_downloaded_file):
            try:
                open_file_crossplatform(self.last_downloaded_file)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")
        else:
            messagebox.showinfo("Notice", "File not found or was moved.")

    def on_open_folder(self):
        save_dir = self.dir_entry.get().strip() or self.save_dir
        if os.path.isdir(save_dir):
            try:
                if self.last_downloaded_file and os.path.isfile(self.last_downloaded_file):
                    reveal_in_folder_crossplatform(self.last_downloaded_file)
                else:
                    reveal_in_folder_crossplatform(save_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder: {e}")

    def _add_to_history(self, filename, filepath):
        self.no_history_label.pack_forget()
        self.download_history.append((filename, filepath))
        self.history_count_lbl.configure(text=f"{len(self.download_history)} items")

        item_row = ctk.CTkFrame(self.history_container, fg_color="#111622", corner_radius=8)
        item_row.pack(fill="x", pady=3, padx=2)

        icon_char = "🎬" if filename.lower().endswith(".mp4") else "🎵"
        name_lbl = ctk.CTkLabel(
            item_row,
            text=f"{icon_char}  {filename}",
            font=ctk.CTkFont(size=12),
            text_color="#e2e8f0",
            anchor="w"
        )
        name_lbl.pack(side="left", padx=10, pady=6, fill="x", expand=True)

        play_btn = ctk.CTkButton(
            item_row,
            text="▶️ Play",
            width=65,
            height=28,
            corner_radius=6,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=11),
            command=lambda fp=filepath: open_file_crossplatform(fp)
        )
        play_btn.pack(side="right", padx=(0, 8), pady=4)

        folder_btn = ctk.CTkButton(
            item_row,
            text="📂 Folder",
            width=75,
            height=28,
            corner_radius=6,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=11),
            command=lambda fp=filepath: reveal_in_folder_crossplatform(fp)
        )
        folder_btn.pack(side="right", padx=(0, 6), pady=4)

if __name__ == "__main__":
    app = MediaDownloaderApp()
    app.mainloop()
