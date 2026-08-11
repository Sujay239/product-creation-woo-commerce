"""
Universal Multi-PC Companion Client
Run this script on ANY other computer (Windows, Mac, Linux) on the same Wi-Fi network
for automatic 2-way OS-to-OS clipboard synchronization and instant CLI file transfers.
"""

import os
import sys
import time
import json
import socket
import argparse
import urllib.request
import urllib.parse
import threading

# Safe UTF-8 console output for Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False
    print("[WARNING] 'pyperclip' not installed on this PC. Install it with 'pip install pyperclip' for direct OS clipboard sync.")


def auto_discover_server(port=8080):
    """Attempts to find the wireless share host on the local subnet."""
    print("[DISCOVER] Searching for Universal Share Host on local network...")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'
    finally:
        s.close()

    subnet = ".".join(local_ip.split(".")[:3])
    # Fast check of common IPs or local IP
    candidates = [f"http://{local_ip}:{port}", f"http://127.0.0.1:{port}"]
    for url in candidates:
        try:
            req = urllib.request.Request(f"{url}/api/files", headers={"User-Agent": "UniversalClient/1.0"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return url
        except Exception:
            pass

    return f"http://{local_ip}:{port}"


def upload_file(server_url, filepath):
    """Sends a local file to the host PC."""
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return

    filename = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)
    print(f"[UPLOAD] Sending {filename} ({file_size / (1024*1024):.2f} MB) to {server_url}...")

    with open(filepath, 'rb') as f:
        file_bytes = f.read()

    boundary = "----UniversalClientBoundary" + str(int(time.time()))
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode('utf-8'))
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode('utf-8'))
    body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
    body.extend(file_bytes)
    body.extend(f"\r\n--{boundary}\r\n".encode('utf-8'))
    body.extend(f'Content-Disposition: form-data; name="device"\r\n\r\n'.encode('utf-8'))
    body.extend(socket.gethostname().encode('utf-8'))
    body.extend(f"\r\n--{boundary}--\r\n".encode('utf-8'))

    req = urllib.request.Request(
        f"{server_url}/api/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get("success"):
                print(f"[SUCCESS] File '{filename}' uploaded successfully!")
            else:
                print(f"[ERROR] Upload failed: {data}")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")


def list_files(server_url):
    """Lists files available in the network shared storage."""
    try:
        req = urllib.request.Request(f"{server_url}/api/files")
        with urllib.request.urlopen(req) as resp:
            files = json.loads(resp.read().decode('utf-8'))
            print("\n" + "=" * 60)
            print(f" SHARED NETWORK STORAGE ({len(files)} files)")
            print("=" * 60)
            for f in files:
                print(f" • {f['name']:<35} {f['size_formatted']:<10} ({f['modified']})")
            print("=" * 60 + "\n")
    except Exception as e:
        print(f"[ERROR] Could not fetch files: {e}")


def sync_clipboard_loop(server_url):
    """
    Continuously mirrors OS clipboards in both directions in real-time.
    Whenever this PC copies text -> sends to host PC & network.
    Whenever another PC copies text -> updates this PC's OS clipboard.
    """
    if not HAS_PYPERCLIP:
        print("[ERROR] 'pyperclip' is required for automatic background clipboard sync.")
        return

    hostname = socket.gethostname()
    print("=" * 65)
    print(" >> 2-WAY BACKGROUND OS CLIPBOARD SYNC ACTIVE")
    print("=" * 65)
    print(f" Host Server : {server_url}")
    print(f" Device Name : {hostname}")
    print(" • Anything you copy (Ctrl+C) on this PC will sync across the network.")
    print(" • Anything copied on other PCs will write to your OS clipboard.")
    print(" Press Ctrl+C to stop.\n")

    last_local_clip = pyperclip.paste()
    last_remote_id = 0

    while True:
        try:
            # 1. Check if local clipboard changed
            current_local = pyperclip.paste()
            if current_local and current_local != last_local_clip:
                last_local_clip = current_local
                payload = json.dumps({"text": current_local, "device": f"PC ({hostname})"}).encode('utf-8')
                req = urllib.request.Request(
                    f"{server_url}/api/os-clipboard/push",
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                try:
                    with urllib.request.urlopen(req, timeout=3) as resp:
                        res = json.loads(resp.read().decode('utf-8'))
                        print(f"[SYNC OUT] Broadcasted local clipboard to network ({len(current_local)} chars)")
                except Exception as e:
                    pass

            # 2. Check if remote network clipboard changed
            req_get = urllib.request.Request(f"{server_url}/api/clipboard")
            with urllib.request.urlopen(req_get, timeout=3) as resp:
                remote_data = json.loads(resp.read().decode('utf-8'))
                r_id = remote_data.get("id", 0)
                r_text = remote_data.get("text", "")
                r_device = remote_data.get("device_name", "Remote")

                if r_id and r_id != last_remote_id and r_text:
                    last_remote_id = r_id
                    if r_text != current_local:
                        pyperclip.copy(r_text)
                        last_local_clip = r_text
                        print(f"[SYNC IN] Received & wrote clipboard from {r_device} ({len(r_text)} chars) -> Ctrl+V ready!")

            time.sleep(1.0)
        except KeyboardInterrupt:
            print("\nStopped clipboard sync.")
            break
        except Exception as e:
            time.sleep(2.0)


def main():
    parser = argparse.ArgumentParser(description="Universal Multi-PC Companion Client")
    parser.add_argument("command", nargs="?", default="sync", choices=["sync", "send", "list"], help="Action: sync (clipboard), send (file), list (files)")
    parser.add_argument("file", nargs="?", default=None, help="File path to send (for 'send' command)")
    parser.add_argument("--server", type=str, default=None, help="Host server URL (e.g. http://192.168.1.5:8080)")
    args = parser.parse_args()

    server_url = args.server
    if not server_url:
        server_url = auto_discover_server()

    server_url = server_url.rstrip("/")

    if args.command == "send":
        if not args.file:
            print("[ERROR] Please specify a file to send: python client.py send <filepath>")
            return
        upload_file(server_url, args.file)
    elif args.command == "list":
        list_files(server_url)
    elif args.command == "sync":
        sync_clipboard_loop(server_url)


if __name__ == "__main__":
    main()
