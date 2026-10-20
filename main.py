import sys
import os

# Safeguard for Windows GUI when run without console (sys.stdout/stderr are None)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Ensure base directory is in sys.path
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def main():
    try:
        from ui import MediaDownloaderApp
        app = MediaDownloaderApp()
        app.mainloop()
    except Exception as e:
        import tkinter.messagebox as mb
        import traceback
        err = traceback.format_exc()
        try:
            mb.showerror("MediaGrab Pro Error", f"เกิดข้อผิดพลาดในการเริ่มโปรแกรม:\n{err}")
        except Exception:
            pass

if __name__ == "__main__":
    main()
