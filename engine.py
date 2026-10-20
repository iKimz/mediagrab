import os
import sys
import shutil
import re
import threading
from typing import Dict, Any, List, Optional, Callable
import yt_dlp

def find_ffmpeg_path() -> Optional[str]:
    """Find ffmpeg binary either bundled, in app directory, or in system PATH / Homebrew."""
    binary_names = ['ffmpeg.exe', 'ffmpeg'] if sys.platform.startswith('win') else ['ffmpeg', 'ffmpeg.exe']

    # 1. PyInstaller bundled temp dir (_MEIPASS)
    if hasattr(sys, '_MEIPASS'):
        for name in binary_names:
            p = os.path.join(sys._MEIPASS, name)
            if os.path.isfile(p):
                return p
            p_bin = os.path.join(sys._MEIPASS, 'bin', name)
            if os.path.isfile(p_bin):
                return p_bin

    # 2. Alongside the executable (.exe / .app)
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        for name in binary_names:
            p = os.path.join(exe_dir, name)
            if os.path.isfile(p):
                return p
            p_bin = os.path.join(exe_dir, 'bin', name)
            if os.path.isfile(p_bin):
                return p_bin
        # Inside macOS .app bundle: Contents/MacOS or Contents/Resources
        if sys.platform == 'darwin':
            res_p = os.path.join(exe_dir, '..', 'Resources', 'ffmpeg')
            if os.path.isfile(res_p):
                return os.path.abspath(res_p)

    # 3. Alongside current script
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    for name in binary_names:
        p = os.path.join(base_dir, name)
        if os.path.isfile(p):
            return p
        p_bin = os.path.join(base_dir, 'bin', name)
        if os.path.isfile(p_bin):
            return p_bin

    # 4. System PATH
    system_ffmpeg = shutil.which('ffmpeg')
    if system_ffmpeg and os.path.isfile(system_ffmpeg):
        return system_ffmpeg

    # 5. macOS Homebrew standard paths
    if sys.platform == 'darwin':
        for mac_path in ['/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/opt/local/bin/ffmpeg']:
            if os.path.isfile(mac_path):
                return mac_path

    # 6. Windows WinGet default links
    if sys.platform.startswith('win'):
        winget_link = os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe')
        if os.path.isfile(winget_link):
            return winget_link

    return None

def format_bytes(num_bytes: Optional[float]) -> str:
    if num_bytes is None or num_bytes <= 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"

def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def detect_platform(url: str, extractor_key: str = "") -> str:
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower or "youtube" in extractor_key.lower():
        return "YouTube"
    elif "facebook.com" in url_lower or "fb.watch" in url_lower or "facebook" in extractor_key.lower():
        return "Facebook"
    elif "instagram.com" in url_lower or "instagram" in extractor_key.lower():
        return "Instagram"
    elif "tiktok.com" in url_lower or "tiktok" in extractor_key.lower():
        return "TikTok"
    elif "twitter.com" in url_lower or "x.com" in url_lower or "twitter" in extractor_key.lower():
        return "X (Twitter)"
    elif "threads.net" in url_lower:
        return "Threads"
    elif "bilibili.com" in url_lower:
        return "Bilibili"
    elif "vimeo.com" in url_lower:
        return "Vimeo"
    return extractor_key or "Web Video"

class DownloadEngine:
    def __init__(self):
        self.ffmpeg_path = find_ffmpeg_path()
        self.is_cancelled = False
        self._current_ydl: Optional[yt_dlp.YoutubeDL] = None
        self._thread: Optional[threading.Thread] = None

    def get_base_ydl_opts(self) -> Dict[str, Any]:
        opts: Dict[str, Any] = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'nocheckcertificate': True,
            'retries': 5,
            'fragment_retries': 5,
        }
        if self.ffmpeg_path:
            opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg_path)
        return opts

    def fetch_info(self, url: str) -> Dict[str, Any]:
        """Fetch video metadata and available resolutions synchronously."""
        url = url.strip()
        opts = self.get_base_ydl_opts()
        opts.update({
            'skip_download': True,
            'extract_flat': False,
        })

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise ValueError("Could not extract video information from the provided URL.")

            # Handle playlists: take first entry if playlist
            if 'entries' in info and info['entries']:
                info = info['entries'][0]

            title = info.get('title') or "Untitled Video"
            author = info.get('uploader') or info.get('channel') or info.get('creator') or "Unknown Creator"
            duration = info.get('duration')
            video_id = info.get('id') or ""
            thumbnail = info.get('thumbnail')
            if not thumbnail and info.get('thumbnails'):
                thumbs = [t for t in info['thumbnails'] if t.get('url')]
                if thumbs:
                    thumbnail = thumbs[-1]['url']
            webpage_url = info.get('webpage_url') or url
            extractor = info.get('extractor_key') or ""
            platform = detect_platform(url, extractor)

            formats = info.get('formats') or []
            res_dict = {}

            # Analyze available heights
            for f in formats:
                h = f.get('height')
                if not h or h <= 0:
                    continue
                vcodec = f.get('vcodec')
                if vcodec == 'none':
                    continue
                fps = f.get('fps')
                fps_str = f" {fps}fps" if fps and fps >= 50 else ""

                if h not in res_dict:
                    res_dict[h] = fps_str
                elif fps_str:
                    res_dict[h] = fps_str

            # Construct clean resolution list
            resolutions = [
                {"label": "⭐ Best Available Quality", "height": 99999}
            ]

            sorted_heights = sorted(res_dict.keys(), reverse=True)
            for h in sorted_heights:
                tag = f"{h}p"
                if h >= 2160:
                    tag += " (4K UHD)"
                elif h >= 1440:
                    tag += " (2K QHD)"
                elif h >= 1080:
                    tag += " (Full HD)"
                elif h >= 720:
                    tag += " (HD)"
                elif h >= 480:
                    tag += " (SD)"
                elif h <= 360:
                    tag += " (Data Saver)"
                tag += res_dict[h]

                resolutions.append({
                    "label": tag,
                    "height": h
                })

            return {
                "title": title,
                "author": author,
                "video_id": video_id,
                "duration_seconds": duration,
                "duration_str": format_duration(duration),
                "thumbnail_url": thumbnail,
                "platform": platform,
                "webpage_url": webpage_url,
                "resolutions": resolutions,
                "raw_info": info
            }

    def start_download(
        self,
        url: str,
        output_dir: str,
        mode: str = "video", # 'video' or 'audio'
        height: Optional[int] = None, # None or 99999 for best
        audio_codec: str = "mp3", # 'mp3' or 'm4a'
        audio_quality: str = "320", # '320', '256', '192', '128'
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        complete_callback: Optional[Callable[[str], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None
    ):
        """Starts download in a separate thread."""
        self.is_cancelled = False

        def run():
            try:
                os.makedirs(output_dir, exist_ok=True)
                downloaded_file = ""

                def hook(d):
                    nonlocal downloaded_file
                    if self.is_cancelled:
                        raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")

                    status = d.get('status')
                    if status == 'downloading':
                        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                        downloaded = d.get('downloaded_bytes') or 0
                        percent = 0.0
                        if total > 0:
                            percent = round((downloaded / total) * 100, 1)

                        speed = d.get('speed')
                        speed_str = f"{format_bytes(speed)}/s" if speed else "--"
                        eta = d.get('eta')
                        eta_str = f"{eta}s" if eta is not None else "--"
                        if eta and eta >= 60:
                            eta_str = format_duration(eta)

                        downloaded_file = d.get('filename') or downloaded_file

                        if progress_callback:
                            progress_callback({
                                "status": "downloading",
                                "percent": percent,
                                "downloaded_bytes": downloaded,
                                "total_bytes": total,
                                "downloaded_str": format_bytes(downloaded),
                                "total_str": format_bytes(total),
                                "speed_str": speed_str,
                                "eta_str": eta_str,
                                "message": f"Downloading... ({percent}%)"
                            })

                    elif status == 'finished':
                        downloaded_file = d.get('filename') or downloaded_file
                        if progress_callback:
                            progress_callback({
                                "status": "processing",
                                "percent": 100.0,
                                "speed_str": "",
                                "eta_str": "",
                                "message": "Processing / Merging with FFmpeg..."
                            })

                opts = self.get_base_ydl_opts()
                # Windows safe output template
                outtmpl = os.path.join(output_dir, "%(title).120s [%(id)s].%(ext)s")
                opts.update({
                    'outtmpl': outtmpl,
                    'progress_hooks': [hook],
                    'windowsfilenames': True if sys.platform.startswith('win') else False,
                    'restrictfilenames': False,
                })

                if mode == "video":
                    # MP4 Video format
                    if height is None or height >= 99990:
                        opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
                    else:
                        opts['format'] = (
                            f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                            f"bestvideo[height<={height}]+bestaudio/"
                            f"best[height<={height}]/best"
                        )
                    opts['merge_output_format'] = 'mp4'
                else:
                    # Audio format
                    opts['format'] = 'bestaudio/best'
                    opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': audio_codec,
                        'preferredquality': audio_quality,
                    }]

                with yt_dlp.YoutubeDL(opts) as ydl:
                    self._current_ydl = ydl
                    info = ydl.extract_info(url, download=True)
                    target_file = ydl.prepare_filename(info)

                    # Adjust extension if merged to mp4 or converted to audio
                    if mode == "video":
                        base, _ = os.path.splitext(target_file)
                        potential_mp4 = base + ".mp4"
                        if os.path.isfile(potential_mp4):
                            target_file = potential_mp4
                    elif mode == "audio":
                        base, _ = os.path.splitext(target_file)
                        potential_audio = f"{base}.{audio_codec}"
                        if os.path.isfile(potential_audio):
                            target_file = potential_audio

                if not self.is_cancelled:
                    if complete_callback:
                        complete_callback(target_file)

            except yt_dlp.utils.DownloadCancelled:
                if error_callback:
                    error_callback("Download was cancelled.")
            except Exception as e:
                err_msg = str(e)
                if "DownloadCancelled" in err_msg:
                    if error_callback:
                        error_callback("Download was cancelled.")
                else:
                    if error_callback:
                        error_callback(f"Download error: {err_msg}")
            finally:
                self._current_ydl = None

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def cancel(self):
        self.is_cancelled = True
