"""
Automated Verification Test Suite for Wireless File Transfer Server
Tests both FTP and Web endpoints to ensure complete functionality.
"""

import os
import sys
import io
import time
import ftplib
import urllib.request
import urllib.parse
import json
import threading

# Safe UTF-8 console output for Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from ftp_server import run_ftp_server
from web_server import app, TRANSFERS_DIR, get_local_ip


def run_tests():
    print("[TEST] Starting background test servers...")
    ftp_port = 2129
    web_port = 8089

    # Start FTP Server in thread
    ftp_thread = threading.Thread(
        target=run_ftp_server,
        kwargs={
            'host': '127.0.0.1',
            'port': ftp_port,
            'shared_dir': TRANSFERS_DIR,
            'username': 'anonymous',
            'password': ''
        },
        daemon=True
    )
    ftp_thread.start()

    # Start Web Server in thread
    web_thread = threading.Thread(
        target=lambda: app.run(host='127.0.0.1', port=web_port, debug=False, use_reloader=False),
        daemon=True
    )
    web_thread.start()

    time.sleep(2.0)
    print("[TEST] Servers started. Beginning tests...\n")

    # 1. Test FTP Server Login & Transfer
    print("--- 1. Testing FTP Server ---")
    try:
        ftp = ftplib.FTP()
        ftp.connect('127.0.0.1', ftp_port, timeout=10)
        welcome = ftp.login() # anonymous
        print(f"[OK] FTP Connect & Login: {welcome}")

        test_ftp_content = b"Hello from wireless phone FTP transfer test!"
        ftp.storbinary("STOR test_ftp_file.txt", io.BytesIO(test_ftp_content))
        print("[OK] FTP Upload: test_ftp_file.txt uploaded successfully")

        # List files
        lines = []
        ftp.dir(lines.append)
        print(f"[OK] FTP Directory listing: {len(lines)} files found")

        # Download back
        download_buf = io.BytesIO()
        ftp.retrbinary("RETR test_ftp_file.txt", download_buf.write)
        assert download_buf.getvalue() == test_ftp_content, "FTP download content mismatch"
        print("[OK] FTP Download & Integrity Check: PASSED")

        ftp.delete("test_ftp_file.txt")
        print("[OK] FTP Delete: PASSED")
        ftp.quit()
    except Exception as e:
        print(f"[FAIL] FTP Test Failed: {e}")
        return False

    # 2. Test Web API Endpoints
    print("\n--- 2. Testing Web Transfer Portal ---")
    try:
        base_url = f"http://127.0.0.1:{web_port}"

        # GET / (HTML Page)
        req = urllib.request.urlopen(f"{base_url}/")
        html = req.read().decode('utf-8')
        assert "Universal" in html, "Web page title missing"
        print("[OK] Web UI Render: PASSED")

        # POST /api/upload
        boundary = "---------------------------974767299852498929531610575"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="test_web_upload.txt"\r\n'
            f"Content-Type: text/plain\r\n\r\n"
            f"Hello from mobile web transfer!\r\n"
            f"--{boundary}--\r\n"
        ).encode('utf-8')

        upload_req = urllib.request.Request(
            f"{base_url}/api/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        with urllib.request.urlopen(upload_req) as resp:
            upload_res = json.loads(resp.read().decode('utf-8'))
            assert upload_res.get("success") is True
            print("[OK] Web File Upload (/api/upload): PASSED")

        # GET /api/files
        with urllib.request.urlopen(f"{base_url}/api/files") as resp:
            files = json.loads(resp.read().decode('utf-8'))
            file_names = [f["name"] for f in files]
            assert "test_web_upload.txt" in file_names
            print("[OK] Web File List (/api/files): PASSED")

        # POST & GET /api/clipboard
        clip_data = json.dumps({"text": "Shared link: https://example.com"}).encode('utf-8')
        clip_req = urllib.request.Request(
            f"{base_url}/api/clipboard",
            data=clip_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(clip_req) as resp:
            clip_res = json.loads(resp.read().decode('utf-8'))
            assert clip_res.get("success") is True

        with urllib.request.urlopen(f"{base_url}/api/clipboard") as resp:
            clip_fetch = json.loads(resp.read().decode('utf-8'))
            assert clip_fetch.get("text") == "Shared link: https://example.com"
            print("[OK] Web Clipboard Synchronization (/api/clipboard): PASSED")

        # Direct OS Clipboard Push Test
        os_push_data = json.dumps({"text": "Antigravity Direct OS Clipboard Test"}).encode('utf-8')
        os_push_req = urllib.request.Request(
            f"{base_url}/api/os-clipboard/push",
            data=os_push_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(os_push_req) as resp:
            os_push_res = json.loads(resp.read().decode('utf-8'))
            assert os_push_res.get("success") is True
            print("[OK] Direct Windows OS Clipboard Push (/api/os-clipboard/push): PASSED")

        # Direct OS Clipboard Pull Test
        with urllib.request.urlopen(f"{base_url}/api/os-clipboard/pull") as resp:
            os_pull_res = json.loads(resp.read().decode('utf-8'))
            assert os_pull_res.get("success") is True
            assert os_pull_res.get("text") == "Antigravity Direct OS Clipboard Test"
            print("[OK] Direct Windows OS Clipboard Pull (/api/os-clipboard/pull): PASSED")

        # GET /api/clipboard/history Test
        with urllib.request.urlopen(f"{base_url}/api/clipboard/history") as resp:
            history_res = json.loads(resp.read().decode('utf-8'))
            assert isinstance(history_res, list) and len(history_res) > 0
            print(f"[OK] Clipboard History Stream (/api/clipboard/history): PASSED ({len(history_res)} items)")

        # GET /api/download-all (ZIP batch download) Test
        with urllib.request.urlopen(f"{base_url}/api/download-all") as resp:
            zip_bytes = resp.read()
            assert len(zip_bytes) > 0
            assert resp.headers.get('Content-Type') == 'application/zip'
            print(f"[OK] Multi-PC Batch ZIP Download (/api/download-all): PASSED ({len(zip_bytes)} bytes)")

        # DELETE /api/delete/test_web_upload.txt
        del_req = urllib.request.Request(
            f"{base_url}/api/delete/test_web_upload.txt",
            method="DELETE"
        )
        with urllib.request.urlopen(del_req) as resp:
            del_res = json.loads(resp.read().decode('utf-8'))
            assert del_res.get("success") is True
            print("[OK] Web File Delete (/api/delete): PASSED")

    except Exception as e:
        print(f"[FAIL] Web Server Test Failed: {e}")
        return False

    print("\n" + "=" * 50)
    print(" ALL AUTOMATED TESTS PASSED SUCCESSFULLY! ")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
