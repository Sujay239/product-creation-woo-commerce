"""
Master Universal Wireless File & Clipboard Transfer Server
Launches both the FTP Server (port 2121) and the Universal Web Sync Portal (port 8080).
Connects ANY device (PC <-> PC, PC <-> Mac, PC <-> Linux, PC <-> Phone/Tablet) over Wi-Fi.
"""

import os
import sys
import time
import socket
import threading
import subprocess
from pathlib import Path

# Safe UTF-8 console output for Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Ensure required libraries
try:
    import qrcode
    from pyftpdlib.authorizers import DummyAuthorizer
    from pyftpdlib.handlers import FTPHandler
    from pyftpdlib.servers import FTPServer
    from flask import Flask
except ImportError as e:
    print(f"Missing dependency: {e}. Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

from ftp_server import run_ftp_server
from web_server import app, TRANSFERS_DIR, get_local_ip


def print_ascii_qr(url):
    """Generates and prints a clean ASCII QR Code in terminal."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        print("\n" + "-" * 45)
        print("  [>] SCAN WITH PHONE OR OPEN ON OTHER COMPUTERS:")
        print("-" * 45)
        qr.print_ascii(invert=True)
        print("-" * 45 + "\n")
    except Exception as e:
        print(f"Could not render ASCII QR code: {e}")


def main():
    local_ip = get_local_ip()
    ftp_port = 2121
    web_port = 8080
    web_url = f"http://{local_ip}:{web_port}"
    ftp_url = f"ftp://{local_ip}:{ftp_port}"

    os.makedirs(TRANSFERS_DIR, exist_ok=True)

    print("\n" + "=" * 68)
    print(" 🚀 UNIVERSAL LOCAL NETWORK SHARE & SYNC HUB")
    print(" (PC <-> PC | PC <-> Mac | PC <-> Linux | PC <-> Phone / Tablet)")
    print("=" * 68)
    print(f" • Host Local IP    : {local_ip}")
    print(f" • Web Portal URL   : {web_url}  (Any Browser / Computer)")
    print(f" • FTP Server URL   : {ftp_url}  (File Explorers & FTP Apps)")
    print(f" • Storage Folder   : {TRANSFERS_DIR}")
    print("=" * 68)

    # Print instant scan QR code
    print_ascii_qr(web_url)

    print(" 💻 HOW TO CONNECT OTHER COMPUTERS & LAPTOPS:")
    print(f" 1. On Computer B (Windows/Mac/Linux on same Wi-Fi):")
    print(f"    • Open Chrome/Edge/Safari and navigate to: {web_url}")
    print(f"    • Drag & drop files directly onto the browser window!")
    print(f"    • Real-time OS clipboard syncing works across all connected machines.")
    print("\n 2. (Optional) Background OS-to-OS Sync Client:")
    print(f"    • Run: python client.py --server {web_url}")
    print("\n 3. MOBILE USAGE (Android / iOS):")
    print(f"    • Scan the QR code with phone camera to open {web_url}")
    print("=" * 68)
    print(" [Logs] Real-time network transfers and clipboard sync ready.\n")

    # Start FTP Server in background daemon thread
    ftp_thread = threading.Thread(
        target=run_ftp_server,
        kwargs={
            'host': '0.0.0.0',
            'port': ftp_port,
            'shared_dir': TRANSFERS_DIR,
            'username': 'anonymous',
            'password': ''
        },
        daemon=True
    )
    ftp_thread.start()

    # Start Web Server in main thread
    try:
        app.run(host='0.0.0.0', port=web_port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\nShutting down Universal Server... Goodbye!")


if __name__ == "__main__":
    main()
