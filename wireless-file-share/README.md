# 📡 Universal Local Network Share & Sync Hub

A high-speed, local wireless file sharing and real-time clipboard sync suite that works **universally across all devices on your Wi-Fi network**:
- **PC ⇄ PC** (Windows, Mac, Linux)
- **Laptop ⇄ Desktop**
- **PC ⇄ Phone / Tablet** (Android, iPhone, iPad)

---

## ⚡ Quick Start on Host Computer

### Option 1: One-Click Launcher
Double-click `start.bat` in this folder.

### Option 2: Command Line
```powershell
cd wireless-file-share
python server.py
```

Once running, your local network URL (e.g., `http://192.168.1.5:8080`) and QR code will appear.

---

## 💻 How to Connect From Another Computer / Laptop (PC ⇄ PC)

Make sure both computers are connected to the **SAME Wi-Fi or Local Network**.

### Method 1: Web Portal (Zero-Install in Chrome / Edge / Safari) ⭐ **Recommended**
1. Open the browser on Computer B and navigate to `http://<Host-IP>:8080`.
2. **Drag & Drop Files Anywhere**: Drag any file or folder from your computer's File Explorer / Finder directly onto the browser window to transfer at multi-gigabit LAN speeds.
3. **Download All in 1-Click**: Click **"📦 Download All (.ZIP)"** to batch download everything in a compressed archive.
4. **Universal Clipboard Hub**:
   - Paste or type text and click **"⚡ Write Directly to Host PC OS Clipboard"** — the text is instantly ready for `Ctrl+V` on the host PC.
   - Click **"📥 Pull from Host PC Clipboard"** to fetch what's currently copied on the host PC.
   - **Recent Clipboard Stream**: View recent snippets shared by any computer on the network with 1-click copy.

---

### Method 2: Multi-PC Companion Client (`client.py`)
Run on any other computer (Windows/Mac/Linux) for background 2-way OS clipboard mirroring and CLI transfers:

```bash
# 1. Start 2-way automatic OS clipboard mirroring in background
python client.py sync --server http://192.168.1.5:8080

# 2. Or send a file directly from terminal
python client.py send "C:\path\to\my_file.zip" --server http://192.168.1.5:8080

# 3. List shared network files
python client.py list --server http://192.168.1.5:8080
```

---

## 📱 Mobile Usage (Android & iOS)

- **Scan QR Code**: Scan the terminal QR code with your phone camera to open the mobile transfer portal.
- **Upload**: Tap "Choose Files" or "Camera" to transfer photos, 4K videos, and files.
- **FTP Apps**: Connect via *CX File Explorer* or *Solid Explorer* to `ftp://<Host-IP>:2121` (Anonymous mode).

---

## 📁 Shared Folder Location
All files received across all computers and phones are stored in:
```
wireless-file-share/transfers/
```

---

## 🧪 Automated Testing
To verify all services, endpoints, and multi-PC sync:
```powershell
python test_suite.py
```
