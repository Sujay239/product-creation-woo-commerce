"""
Wireless FTP Server
Enables fast, wireless file upload and download between phone and laptop over local Wi-Fi.
Compatible with all mobile FTP clients (e.g., CX File Explorer, Solid Explorer, AndFTP, FileZilla, etc.)
"""

import os
import sys
import socket
from pathlib import Path

# Safe UTF-8 console output for Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


def get_local_ip():
    """Detects the active local Wi-Fi / LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


class CustomFTPHandler(FTPHandler):
    """Custom FTP handler to log transfer events cleanly."""
    def on_file_received(self, file):
        filename = os.path.basename(file)
        size_bytes = os.path.getsize(file) if os.path.exists(file) else 0
        print(f"\n[FTP] [OK] Received File: {filename} ({size_bytes / (1024*1024):.2f} MB)")

    def on_file_sent(self, file):
        filename = os.path.basename(file)
        print(f"\n[FTP] [SEND] Sent File: {filename}")

    def on_connect(self):
        print(f"[FTP] Client connected from {self.remote_ip}:{self.remote_port}")

    def on_disconnect(self):
        print(f"[FTP] Client disconnected ({self.remote_ip})")


def run_ftp_server(host='0.0.0.0', port=2121, shared_dir=None, username="anonymous", password=""):
    """Starts the FTP server."""
    if shared_dir is None:
        shared_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transfers")
    
    os.makedirs(shared_dir, exist_ok=True)
    shared_dir = os.path.abspath(shared_dir)

    authorizer = DummyAuthorizer()
    
    # Full read/write/modify permissions for seamless file exchange:
    perms = 'elradfmwMT'

    if username == "anonymous" or not username:
        authorizer.add_anonymous(shared_dir, perm=perms)
        auth_info = "Anonymous (No password needed)"
    else:
        authorizer.add_user(username, password, shared_dir, perm=perms)
        auth_info = f"Username: {username} | Password: {'*' * len(password)}"

    handler = CustomFTPHandler
    handler.authorizer = authorizer
    handler.banner = "Wireless FTP Server Ready."
    
    # Passive ports range (helps pass through local firewalls smoothly)
    handler.passive_ports = range(60000, 60050)

    local_ip = get_local_ip()
    handler.masquerade_address = local_ip

    address = (host, port)
    server = FTPServer(address, handler)
    server.max_cons = 256
    server.max_cons_per_ip = 20

    print("=" * 60)
    print(" >> WIRELESS FTP SERVER RUNNING")
    print("=" * 60)
    print(f" Local IP Address   : {local_ip}")
    print(f" Port               : {port}")
    print(f" FTP URL            : ftp://{local_ip}:{port}")
    print(f" Authentication     : {auth_info}")
    print(f" Shared Folder      : {shared_dir}")
    print("=" * 60)
    print(" Connect your phone to the same Wi-Fi and open your FTP App.")
    print(" Press Ctrl+C to stop the server.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[FTP] Stopping FTP server...")
    finally:
        server.close_all()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Start Wireless FTP Server")
    parser.add_argument("--port", type=int, default=2121, help="Port to bind FTP server (default: 2121)")
    parser.add_argument("--dir", type=str, default=None, help="Directory to share/store files")
    parser.add_argument("--user", type=str, default="anonymous", help="Username (default: anonymous)")
    parser.add_argument("--password", type=str, default="", help="Password (default: empty)")
    args = parser.parse_args()

    run_ftp_server(port=args.port, shared_dir=args.dir, username=args.user, password=args.password)
