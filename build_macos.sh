#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "=========================================="
echo "  Building MediaGrab Pro for macOS (.dmg) "
echo "=========================================="

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Run the python build script
python3 build_macos.py

echo ""
echo "=========================================="
echo "  BUILD COMPLETE!"
echo "  Output file: dist/MediaGrabPro-macOS.dmg"
echo "  or dist/MediaGrabPro.app"
echo "=========================================="
