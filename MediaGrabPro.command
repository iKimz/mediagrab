#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "Launching MediaGrab Pro..."
python3 -c "import customtkinter, yt_dlp, PIL, requests" 2>/dev/null || {
    echo "Installing required libraries (one-time setup)..."
    python3 -m pip install -r requirements.txt
}

python3 main.py
