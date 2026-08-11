"""
Universal Wireless File Transfer & Multi-Device Sync Portal
Enables high-speed file sharing and real-time clipboard synchronization
across ANY device on the local network (PC <-> PC, PC <-> Mac, PC <-> Linux, PC <-> Phone).
"""

import os
import sys
import io
import time
import json
import queue
import socket
import zipfile
import datetime
import threading
from pathlib import Path

# Safe UTF-8 console output for Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Direct OS Clipboard integration
try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

from flask import Flask, request, jsonify, send_from_directory, send_file, render_template_string, Response

# Determine shared transfers directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSFERS_DIR = os.path.join(BASE_DIR, "transfers")
os.makedirs(TRANSFERS_DIR, exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024 * 1024  # 20 GB max upload limit

# Clipboard state & history
clipboard_history = []  # List of {id, text, timestamp, source_ip, device_name}
MAX_CLIPBOARD_HISTORY = 30
current_clipboard = {
    "id": 0,
    "text": "",
    "timestamp": None,
    "source_ip": "Host",
    "device_name": "Host PC"
}

# Real-time event subscribers (Server-Sent Events)
event_listeners = []
event_lock = threading.Lock()


def get_local_ip():
    """Detects active local Wi-Fi / LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def format_size(bytes_size):
    """Formats bytes into human readable KB, MB, GB, TB."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


def notify_clients(event_type, payload):
    """Broadcasts SSE message to all connected browsers and PCs."""
    message = f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
    with event_lock:
        stale = []
        for q in event_listeners:
            try:
                q.put_nowait(message)
            except Exception:
                stale.append(q)
        for q in stale:
            if q in event_listeners:
                event_listeners.remove(q)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Universal Local Network Share & Sync</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0a0e17;
            --bg-card: rgba(18, 24, 38, 0.85);
            --bg-card-hover: rgba(26, 35, 56, 0.95);
            --border-color: rgba(255, 255, 255, 0.08);
            --accent-primary: #6366f1;
            --accent-primary-hover: #4f46e5;
            --accent-secondary: #06b6d4;
            --accent-gradient: linear-gradient(135deg, #6366f1 0%, #06b6d4 100%);
            --accent-os: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
            --accent-success: #10b981;
            --accent-warning: #f59e0b;
            --accent-danger: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            background-color: var(--bg-base);
            background-image: 
                radial-gradient(circle at 10% 10%, rgba(99, 102, 241, 0.14) 0%, transparent 45%),
                radial-gradient(circle at 90% 90%, rgba(6, 182, 212, 0.12) 0%, transparent 45%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            padding: 20px 24px 60px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Header */
        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
            flex-wrap: wrap;
            gap: 12px;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .brand-icon {
            width: 46px;
            height: 46px;
            border-radius: 12px;
            background: var(--accent-gradient);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: 0 8px 20px rgba(99, 102, 241, 0.35);
        }

        .brand-text h1 {
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .brand-text p {
            font-size: 13px;
            color: var(--text-muted);
        }

        .header-badges {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 20px;
            font-size: 12px;
            color: var(--accent-success);
            font-weight: 600;
        }

        .device-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.25);
            border-radius: 20px;
            font-size: 12px;
            color: #a5b4fc;
            font-weight: 600;
        }

        .status-pulse {
            width: 8px;
            height: 8px;
            background-color: var(--accent-success);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--accent-success);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); opacity: 0.8; }
            50% { transform: scale(1.2); opacity: 1; }
            100% { transform: scale(0.95); opacity: 0.8; }
        }

        /* Layout Grid for Desktop PC <-> PC */
        .workspace-grid {
            display: grid;
            grid-template-columns: 1.15fr 0.85fr;
            gap: 24px;
        }

        @media (max-width: 900px) {
            .workspace-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Cards */
        .card {
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 22px;
            margin-bottom: 20px;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.3);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .card-title {
            font-size: 16px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Drop Zone */
        .dropzone {
            border: 2px dashed rgba(99, 102, 241, 0.4);
            background: rgba(99, 102, 241, 0.04);
            border-radius: 14px;
            padding: 36px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.25s ease;
            position: relative;
        }

        .dropzone:hover, .dropzone.dragover {
            border-color: var(--accent-secondary);
            background: rgba(6, 182, 212, 0.08);
            transform: translateY(-2px);
        }

        .dropzone-icon {
            font-size: 42px;
            margin-bottom: 12px;
            display: inline-block;
            filter: drop-shadow(0 4px 10px rgba(99, 102, 241, 0.4));
        }

        .dropzone-text {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 6px;
            color: var(--text-main);
        }

        .dropzone-sub {
            font-size: 12px;
            color: var(--text-muted);
        }

        .file-input {
            display: none;
        }

        .action-buttons {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 14px;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 12px 18px;
            border-radius: 10px;
            border: none;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
        }

        .btn-primary {
            background: var(--accent-gradient);
            color: #ffffff;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.35);
        }

        .btn-primary:hover {
            opacity: 0.92;
            transform: translateY(-1px);
        }

        .btn-os {
            background: var(--accent-os);
            color: #0b0f19;
            font-weight: 700;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.35);
        }

        .btn-os:hover {
            opacity: 0.92;
            transform: translateY(-1px);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-main);
            border: 1px solid var(--border-color);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.14);
        }

        .btn-sm {
            padding: 6px 12px;
            font-size: 12px;
            border-radius: 8px;
        }

        /* Progress List */
        .progress-list {
            margin-top: 16px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-height: 250px;
            overflow-y: auto;
        }

        .progress-item {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px;
        }

        .progress-info {
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            margin-bottom: 6px;
        }

        .progress-filename {
            font-weight: 600;
            max-width: 70%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .progress-bar-bg {
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-bar-fill {
            height: 100%;
            background: var(--accent-gradient);
            width: 0%;
            transition: width 0.15s ease;
        }

        /* File List */
        .file-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 480px;
            overflow-y: auto;
            padding-right: 4px;
        }

        .file-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 14px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            transition: all 0.2s ease;
        }

        .file-card:hover {
            background: var(--bg-card-hover);
            border-color: rgba(99, 102, 241, 0.3);
        }

        .file-left {
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 0;
        }

        .file-icon {
            font-size: 24px;
            flex-shrink: 0;
        }

        .file-details {
            min-width: 0;
        }

        .file-name {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-main);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .file-meta {
            font-size: 11px;
            color: var(--text-dim);
            margin-top: 2px;
        }

        .file-actions {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-shrink: 0;
        }

        .btn-icon {
            width: 34px;
            height: 34px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s ease;
        }

        .btn-icon:hover {
            background: var(--accent-primary);
            border-color: var(--accent-primary);
        }

        .btn-icon.delete:hover {
            background: var(--accent-danger);
            border-color: var(--accent-danger);
        }

        /* Clipboard Component */
        .clipboard-box {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .clipboard-header-info {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            background: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: 8px;
            font-size: 12px;
            color: #34d399;
        }

        .clipboard-textarea {
            width: 100%;
            height: 120px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px;
            color: var(--text-main);
            font-size: 13px;
            font-family: 'JetBrains Mono', monospace;
            resize: vertical;
            outline: none;
        }

        .clipboard-textarea:focus {
            border-color: var(--accent-primary);
        }

        .clipboard-btn-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        .clipboard-btn-full {
            grid-column: span 2;
        }

        /* Clipboard History List */
        .history-section {
            margin-top: 18px;
            border-top: 1px solid var(--border-color);
            padding-top: 14px;
        }

        .history-title {
            font-size: 13px;
            font-weight: 700;
            color: var(--text-muted);
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .history-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 280px;
            overflow-y: auto;
        }

        .history-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 10px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            transition: all 0.2s ease;
        }

        .history-card:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(99, 102, 241, 0.3);
        }

        .history-text {
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: var(--text-main);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 80%;
        }

        .history-meta {
            font-size: 10px;
            color: var(--text-dim);
            margin-top: 2px;
        }

        .empty-state {
            text-align: center;
            padding: 30px 10px;
            color: var(--text-dim);
            font-size: 13px;
        }

        /* Full page Drag-and-Drop overlay */
        #dragOverlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(11, 15, 25, 0.92);
            backdrop-filter: blur(12px);
            z-index: 9999;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            border: 3px dashed var(--accent-secondary);
        }

        #dragOverlay.active {
            display: flex;
        }

        /* Toast */
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: #1e293b;
            color: #ffffff;
            padding: 12px 24px;
            border-radius: 30px;
            font-size: 13px;
            font-weight: 600;
            border: 1px solid var(--border-color);
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 10000;
            text-align: center;
            max-width: 90%;
        }

        .toast.show {
            transform: translateX(-50%) translateY(0);
        }

        @media (max-width: 600px) {
            body { padding: 14px 12px 50px; }
            .action-buttons, .clipboard-btn-grid { grid-template-columns: 1fr; }
            .clipboard-btn-full { grid-column: span 1; }
        }
    </style>
</head>
<body>
    <!-- Drag Overlay -->
    <div id="dragOverlay">
        <div style="font-size: 60px; margin-bottom: 16px;">📥</div>
        <h2 style="font-size: 24px; font-weight: 700;">Drop Files Anywhere to Share</h2>
        <p style="color: var(--text-muted); margin-top: 8px;">Upload instantly to connected PCs & devices</p>
    </div>

    <div class="container">
        <!-- Header -->
        <header>
            <div class="brand">
                <div class="brand-icon">⚡</div>
                <div class="brand-text">
                    <h1>Universal Network Share & Sync</h1>
                    <p>High-Speed Local Wi-Fi Sharing across all Computers & Devices</p>
                </div>
            </div>
            <div class="header-badges">
                <div class="device-badge" id="myDeviceBadge">💻 Connected Device</div>
                <div class="status-badge">
                    <div class="status-pulse"></div>
                    <span id="sseStatus">Live Synced</span>
                </div>
            </div>
        </header>

        <!-- Widescreen Dual-Pane Grid (Perfect for PC <-> PC and Mobile) -->
        <div class="workspace-grid">
            
            <!-- LEFT PANE: Files & Uploads -->
            <div class="pane-left">
                <!-- Upload Card -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">📤 Upload & Send Files</div>
                    </div>

                    <div class="dropzone" id="dropzone" onclick="document.getElementById('fileInput').click()">
                        <div class="dropzone-icon">📥</div>
                        <div class="dropzone-text">Click or Drag Files / Folders Here</div>
                        <div class="dropzone-sub">Share 4K Videos, Large ZIPs, Documents across any Computer or Phone</div>
                        <input type="file" id="fileInput" class="file-input" multiple onchange="handleFileSelect(event)">
                    </div>

                    <div class="action-buttons">
                        <button class="btn btn-primary" onclick="document.getElementById('fileInput').click()">
                            📁 Select Files from Device
                        </button>
                        <button class="btn btn-secondary" onclick="document.getElementById('cameraInput').click()">
                            📷 Camera / Photo Picker
                        </button>
                        <input type="file" id="cameraInput" class="file-input" capture="environment" accept="image/*,video/*" onchange="handleFileSelect(event)">
                    </div>

                    <!-- Progress Section -->
                    <div class="progress-list" id="progressList"></div>
                </div>

                <!-- Shared Files List -->
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">💻 Shared Storage on Network</div>
                        <div style="display: flex; gap: 8px;">
                            <a href="/api/download-all" class="btn btn-secondary btn-sm" title="Download all files as a single ZIP">
                                📦 Download All (.ZIP)
                            </a>
                            <button class="btn-icon" onclick="fetchFiles()" title="Refresh files list">🔄</button>
                        </div>
                    </div>
                    <div class="file-list" id="fileList">
                        <div class="empty-state">Loading shared files...</div>
                    </div>
                </div>
            </div>

            <!-- RIGHT PANE: Universal Live Clipboard & History -->
            <div class="pane-right">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">📋 Universal OS Clipboard Hub</div>
                        <button class="btn-icon" onclick="pullFromOSClipboard()" title="Pull from Host PC OS Clipboard">📥</button>
                    </div>

                    <div class="clipboard-box">
                        <div class="clipboard-header-info">
                            <span>⚡ Live OS Sync: Instant Ctrl+V on Host PC & connected devices</span>
                        </div>

                        <textarea id="clipboardText" class="clipboard-textarea" placeholder="Paste code snippets, URLs, passwords, or text to broadcast across all connected computers & phones..."></textarea>

                        <div class="clipboard-btn-grid">
                            <button class="btn btn-os clipboard-btn-full" onclick="pushToOSClipboard()">
                                ⚡ Write Directly to Host PC OS Clipboard (Ctrl+V Ready)
                            </button>
                            <button class="btn btn-primary" onclick="pullFromOSClipboard()">
                                📥 Pull from Host PC Clipboard
                            </button>
                            <button class="btn btn-secondary" onclick="copyThisDevice()">
                                📋 Copy to This Device
                            </button>
                        </div>

                        <!-- Clipboard History -->
                        <div class="history-section">
                            <div class="history-title">
                                <span>Recent Network Clipboard Stream</span>
                                <button class="btn-icon" style="width:26px; height:26px; font-size:11px;" onclick="fetchHistory()" title="Refresh history">🔄</button>
                            </div>
                            <div class="history-list" id="historyList">
                                <div class="empty-state">No clipboard history yet.</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <!-- Toast Notification -->
    <div id="toast" class="toast">Notification</div>

    <script>
        // Identify local device
        const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
        const deviceName = isMobile ? (navigator.userAgent.includes('iPhone') ? '📱 iPhone' : '📱 Android Phone') : '💻 Computer / Laptop';
        document.getElementById('myDeviceBadge').innerText = deviceName;

        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }

        // Window-wide drag and drop for desktop computers
        let dragCounter = 0;
        const dragOverlay = document.getElementById('dragOverlay');

        window.addEventListener('dragenter', (e) => {
            e.preventDefault();
            dragCounter++;
            dragOverlay.classList.add('active');
        });

        window.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dragCounter--;
            if (dragCounter <= 0) {
                dragOverlay.classList.remove('active');
                dragCounter = 0;
            }
        });

        window.addEventListener('dragover', (e) => e.preventDefault());

        window.addEventListener('drop', (e) => {
            e.preventDefault();
            dragCounter = 0;
            dragOverlay.classList.remove('active');
            if (e.dataTransfer && e.dataTransfer.files.length > 0) {
                uploadFiles(e.dataTransfer.files);
            }
        });

        function handleFileSelect(e) {
            if (e.target.files.length > 0) {
                uploadFiles(e.target.files);
            }
        }

        function uploadFiles(files) {
            const progressList = document.getElementById('progressList');
            
            Array.from(files).forEach((file, idx) => {
                const itemId = 'prog_' + Date.now() + '_' + idx;
                const item = document.createElement('div');
                item.className = 'progress-item';
                item.id = itemId;
                item.innerHTML = `
                    <div class="progress-info">
                        <span class="progress-filename">${file.name}</span>
                        <span class="progress-percent" id="${itemId}_pct">0%</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" id="${itemId}_bar"></div>
                    </div>
                `;
                progressList.prepend(item);

                const formData = new FormData();
                formData.append('file', file);
                formData.append('device', deviceName);

                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/api/upload', true);

                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) {
                        const pct = Math.round((e.loaded / e.total) * 100);
                        document.getElementById(`${itemId}_pct`).innerText = pct + '%';
                        document.getElementById(`${itemId}_bar`).style.width = pct + '%';
                    }
                };

                xhr.onload = () => {
                    if (xhr.status === 200) {
                        document.getElementById(`${itemId}_pct`).innerText = '✔ Done';
                        document.getElementById(`${itemId}_bar`).style.background = 'var(--accent-success)';
                        showToast(`Uploaded ${file.name}`);
                        fetchFiles();
                    } else {
                        document.getElementById(`${itemId}_pct`).innerText = '❌ Failed';
                    }
                };

                xhr.onerror = () => {
                    document.getElementById(`${itemId}_pct`).innerText = '❌ Error';
                };

                xhr.send(formData);
            });
        }

        function getFileIcon(filename) {
            const ext = filename.split('.').pop().toLowerCase();
            if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'svg'].includes(ext)) return '🖼️';
            if (['mp4', 'mov', 'avi', 'mkv', 'webm'].includes(ext)) return '🎬';
            if (['mp3', 'wav', 'aac', 'm4a', 'flac'].includes(ext)) return '🎵';
            if (['pdf'].includes(ext)) return '📕';
            if (['zip', 'rar', '7z', 'tar', 'gz', 'iso'].includes(ext)) return '📦';
            if (['docx', 'doc', 'txt', 'md', 'json', 'py', 'js', 'html', 'css'].includes(ext)) return '📄';
            if (['xlsx', 'csv'].includes(ext)) return '📊';
            if (['exe', 'msi', 'dmg', 'deb', 'apk'].includes(ext)) return '⚙️';
            return '📁';
        }

        function fetchFiles() {
            fetch('/api/files')
                .then(res => res.json())
                .then(files => {
                    const list = document.getElementById('fileList');
                    if (files.length === 0) {
                        list.innerHTML = `<div class="empty-state">No files in shared storage yet. Drop files above to share!</div>`;
                        return;
                    }
                    list.innerHTML = files.map(f => `
                        <div class="file-card">
                            <div class="file-left">
                                <div class="file-icon">${getFileIcon(f.name)}</div>
                                <div class="file-details">
                                    <div class="file-name" title="${f.name}">${f.name}</div>
                                    <div class="file-meta">${f.size_formatted} • ${f.modified}</div>
                                </div>
                            </div>
                            <div class="file-actions">
                                <a href="/api/download/${encodeURIComponent(f.name)}" download class="btn-icon" title="Download">⬇</a>
                                <button onclick="deleteFile('${encodeURIComponent(f.name)}')" class="btn-icon delete" title="Delete">🗑</button>
                            </div>
                        </div>
                    `).join('');
                })
                .catch(err => console.error(err));
        }

        function deleteFile(filename) {
            if (!confirm(`Delete ${decodeURIComponent(filename)}?`)) return;
            fetch(`/api/delete/${filename}`, { method: 'DELETE' })
                .then(res => res.json())
                .then(data => {
                    showToast('File deleted');
                    fetchFiles();
                });
        }

        // Direct OS Clipboard Push (writes to host PC clipboard)
        function pushToOSClipboard(customText = null) {
            const textarea = document.getElementById('clipboardText');
            const text = customText !== null ? customText : textarea.value;
            if (!text) {
                showToast('Please type or paste some text first!');
                return;
            }

            fetch('/api/os-clipboard/push', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, device: deviceName })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showToast('⚡ Written to Host PC Clipboard! Press Ctrl+V on PC.');
                    fetchHistory();
                } else {
                    showToast('Failed to sync: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(err => {
                showToast('Error communicating with host PC');
            });
        }

        // Direct OS Clipboard Pull (reads from host PC clipboard)
        function pullFromOSClipboard() {
            fetch('/api/os-clipboard/pull')
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        const textarea = document.getElementById('clipboardText');
                        textarea.value = data.text || "";
                        showToast('📥 Pulled text from Host PC OS Clipboard!');
                    } else {
                        showToast('Failed to pull from host PC');
                    }
                })
                .catch(err => {
                    showToast('Error connecting to host PC clipboard');
                });
        }

        // Universal Copy to THIS Device's local clipboard
        function copyThisDevice(textToCopy = null) {
            const textarea = document.getElementById('clipboardText');
            const val = textToCopy !== null ? textToCopy : textarea.value;
            if (!val) {
                showToast('Nothing to copy!');
                return;
            }

            function execCopy() {
                const temp = document.createElement('textarea');
                temp.value = val;
                temp.style.position = 'fixed';
                temp.style.left = '-9999px';
                document.body.appendChild(temp);
                temp.focus();
                temp.select();
                temp.setSelectionRange(0, 99999);
                try {
                    document.execCommand('copy');
                    showToast('Copied to this device!');
                } catch(e) {
                    showToast('Selected text!');
                }
                document.body.removeChild(temp);
            }

            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(val)
                    .then(() => showToast('Copied to this device!'))
                    .catch(() => execCopy());
            } else {
                execCopy();
            }
        }

        function fetchHistory() {
            fetch('/api/clipboard/history')
                .then(res => res.json())
                .then(history => {
                    const list = document.getElementById('historyList');
                    if (history.length === 0) {
                        list.innerHTML = `<div class="empty-state">No clipboard history yet.</div>`;
                        return;
                    }
                    list.innerHTML = history.map(item => `
                        <div class="history-card">
                            <div style="min-width: 0; flex: 1;">
                                <div class="history-text" title="${escapeHtml(item.text)}">${escapeHtml(item.text)}</div>
                                <div class="history-meta">${escapeHtml(item.device_name || 'Device')} • ${item.time}</div>
                            </div>
                            <div style="display: flex; gap: 6px;">
                                <button class="btn-icon" style="width:28px; height:28px; font-size:12px;" onclick="setAndCopy(${JSON.stringify(item.text)})" title="Copy to this device">📋</button>
                                <button class="btn-icon" style="width:28px; height:28px; font-size:12px;" onclick="pushToOSClipboard(${JSON.stringify(item.text)})" title="Push to Host OS Clipboard">⚡</button>
                            </div>
                        </div>
                    `).join('');
                })
                .catch(err => console.error(err));
        }

        function setAndCopy(text) {
            document.getElementById('clipboardText').value = text;
            copyThisDevice(text);
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.innerText = text;
            return div.innerHTML;
        }

        // Real-Time Server-Sent Events (SSE) for instant live sync across multiple computers
        function initSSE() {
            const sse = new EventSource('/api/events');
            sse.onopen = () => {
                document.getElementById('sseStatus').innerText = 'Live Synced';
            };
            sse.addEventListener('file_change', () => {
                fetchFiles();
            });
            sse.addEventListener('clipboard_change', (e) => {
                const data = JSON.parse(e.data);
                const textarea = document.getElementById('clipboardText');
                if (data.text && textarea.value !== data.text) {
                    textarea.value = data.text;
                    showToast(`⚡ Clipboard synced from ${data.device_name || 'network'}!`);
                }
                fetchHistory();
            });
            sse.onerror = () => {
                document.getElementById('sseStatus').innerText = 'Reconnecting...';
            };
        }

        // Initial Load
        fetchFiles();
        fetchHistory();
        initSSE();

        // Fallback polling every 8 seconds
        setInterval(() => {
            fetchFiles();
            fetchHistory();
        }, 8000);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/events')
def sse_events():
    """Server-Sent Events endpoint for real-time push to all connected computers."""
    q = queue.Queue(maxsize=100)
    with event_lock:
        event_listeners.append(q)

    def event_stream():
        try:
            # Send initial ping
            yield "event: ping\ndata: {}\n\n"
            while True:
                try:
                    msg = q.get(timeout=25)
                    yield msg
                except queue.Empty:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            with event_lock:
                if q in event_listeners:
                    event_listeners.remove(q)

    return Response(event_stream(), mimetype="text/event-stream")


@app.route('/api/files', methods=['GET'])
def list_files():
    files_list = []
    if os.path.exists(TRANSFERS_DIR):
        for entry in os.scandir(TRANSFERS_DIR):
            if entry.is_file():
                stat = entry.stat()
                mod_time = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %I:%M %p")
                files_list.append({
                    "name": entry.name,
                    "size_bytes": stat.st_size,
                    "size_formatted": format_size(stat.st_size),
                    "modified": mod_time,
                    "timestamp": stat.st_mtime
                })
    # Sort newest files first
    files_list.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify(files_list)


@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file in request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    filename = file.filename
    device = request.form.get("device", "Remote Device")
    client_ip = request.remote_addr
    target_path = os.path.join(TRANSFERS_DIR, filename)

    # Save file
    file.save(target_path)
    file_size = os.path.getsize(target_path)
    print(f"\n[NETWORK UPLOAD] [OK] {filename} ({format_size(file_size)}) received from {device} [{client_ip}]")

    # Broadcast file change to all connected computers
    notify_clients('file_change', {"filename": filename, "device": device})

    return jsonify({
        "success": True,
        "filename": filename,
        "size": format_size(file_size)
    })


@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(TRANSFERS_DIR, filename, as_attachment=True)


@app.route('/api/download-all', methods=['GET'])
def download_all_zip():
    """Zips all files in transfers/ on the fly for batch 1-click download from another PC."""
    memory_zip = io.BytesIO()
    with zipfile.ZipFile(memory_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(TRANSFERS_DIR):
            for entry in os.scandir(TRANSFERS_DIR):
                if entry.is_file():
                    zf.write(entry.path, arcname=entry.name)
    memory_zip.seek(0)
    zip_filename = f"wireless_transfers_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    print(f"[ZIP DOWNLOAD] Created and served {zip_filename}")
    return send_file(
        memory_zip,
        mimetype='application/zip',
        as_attachment=True,
        download_name=zip_filename
    )


@app.route('/api/delete/<path:filename>', methods=['DELETE'])
def delete_file(filename):
    target_path = os.path.join(TRANSFERS_DIR, filename)
    if os.path.exists(target_path):
        os.remove(target_path)
        print(f"[WEB] [DEL] Deleted File: {filename}")
        notify_clients('file_change', {"deleted": filename})
        return jsonify({"success": True})
    return jsonify({"error": "File not found"}), 404


@app.route('/api/clipboard', methods=['GET', 'POST'])
def handle_clipboard():
    global current_clipboard
    client_ip = request.remote_addr
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        device = data.get("device", "Remote Device")
        
        current_clipboard = {
            "id": int(time.time() * 1000),
            "text": text,
            "timestamp": time.time(),
            "time": datetime.datetime.now().strftime("%I:%M %p"),
            "source_ip": client_ip,
            "device_name": device
        }

        # Add to history
        clipboard_history.insert(0, current_clipboard)
        if len(clipboard_history) > MAX_CLIPBOARD_HISTORY:
            clipboard_history.pop()

        # Write to Host OS Clipboard
        if HAS_PYPERCLIP:
            try:
                pyperclip.copy(text)
                print(f"\n[OS CLIPBOARD] [OK] Written to Host Windows OS Clipboard ({len(text)} chars)")
            except Exception as e:
                print(f"[OS CLIPBOARD] Warning: {e}")

        # Broadcast in real-time to all other computers
        notify_clients('clipboard_change', current_clipboard)

        return jsonify({"success": True})
    return jsonify(current_clipboard)


@app.route('/api/clipboard/history', methods=['GET'])
def get_clipboard_history():
    return jsonify(clipboard_history)


@app.route('/api/os-clipboard/push', methods=['POST'])
def push_to_os_clipboard():
    """Directly copies text from any computer to the host Windows OS clipboard."""
    global current_clipboard
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    device = data.get("device", "Remote Computer")
    client_ip = request.remote_addr

    if HAS_PYPERCLIP:
        try:
            pyperclip.copy(text)
            current_clipboard = {
                "id": int(time.time() * 1000),
                "text": text,
                "timestamp": time.time(),
                "time": datetime.datetime.now().strftime("%I:%M %p"),
                "source_ip": client_ip,
                "device_name": device
            }
            clipboard_history.insert(0, current_clipboard)
            if len(clipboard_history) > MAX_CLIPBOARD_HISTORY:
                clipboard_history.pop()

            notify_clients('clipboard_change', current_clipboard)
            print(f"\n[OS CLIPBOARD] [DIRECT PUSH] Written to Host OS Clipboard from {device} ({len(text)} chars)")
            return jsonify({"success": True, "message": "Written directly to Host PC OS Clipboard!"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "pyperclip is not available"}), 500


@app.route('/api/os-clipboard/pull', methods=['GET'])
def pull_from_os_clipboard():
    """Reads whatever text is currently inside the host Windows OS clipboard."""
    if HAS_PYPERCLIP:
        try:
            text = pyperclip.paste()
            print(f"\n[OS CLIPBOARD] [DIRECT PULL] Read from Host OS Clipboard ({len(text)} chars)")
            return jsonify({"success": True, "text": text})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "pyperclip is not available"}), 500


def run_web_server(host='0.0.0.0', port=8080):
    """Starts the Flask web server."""
    local_ip = get_local_ip()
    print("=" * 60)
    print(" >> UNIVERSAL NETWORK SHARE & SYNC RUNNING")
    print("=" * 60)
    print(f" Local Web URL : http://{local_ip}:{port}")
    print(f" Shared Folder : {TRANSFERS_DIR}")
    print(f" Direct OS Clipboard: {'Enabled' if HAS_PYPERCLIP else 'Disabled'}")
    print(f" Real-time Multi-PC Push (SSE): Active")
    print("=" * 60)
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Start Universal Web Transfer Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind Web server (default: 8080)")
    args = parser.parse_args()
    run_web_server(port=args.port)
