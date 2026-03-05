**Multi-Browser Audit & System Diagnostic Tool**
This Python-based utility is designed for security auditing and digital forensics. It extracts saved credentials from Chromium-based browsers (Chrome, Edge), Firefox, and retrieves stored Wi-Fi profiles from the host Windows system.

[!WARNING]
Legal Disclaimer: This tool is for educational and authorized administrative purposes only. Running this script on a computer without the owner's explicit permission is illegal and a violation of privacy.

## Key Features
Chromium Extraction: Decrypts AES-256 GCM encrypted passwords from Google Chrome and Microsoft Edge using the Windows DPAPI Master Key.

Firefox Recovery: Interfaces with nss3.dll via ctypes to decrypt Mozilla's Triple-DES/AES encrypted logins.json.

Network Auditing: Recovers all saved Wi-Fi SSIDs and plaintext passwords using netsh.

Clipboard Capture: Records the current contents of the system clipboard.

Automatic Dependency Management: Self-installs required libraries (pycryptodome, pywin32, etc.) if they are missing.

## Technical Architecture
The script operates by targeting the specific encryption layers used by modern browsers:

Extraction Logic
Identity: Collects Hostname and Public IP.

Key Retrieval: Locates the Local State file to extract the Base64 encrypted key, then uses win32crypt to decrypt it into a raw Master Key.

Database Access: Creates a temporary shadow copy of Login Data (SQLite) to bypass file locks if the browser is currently running.

Decryption: Uses the Master Key and IV (Initialization Vector) to decrypt individual password blobs.

Output: Generates a timestamped JSON report (Audit_HHMMSS.json).

## Prerequisites
OS: Windows 10/11 (Required for win32crypt and netsh compatibility).

Python: 3.8 or higher.

Permissions: Standard user permissions are sufficient for browser data, but Administrative privileges are required to recover some Wi-Fi profiles.

## Usage
Clone or save the script to your local machine.

Run the script via the command line:

Bash
python audit_script.py
Review Results: The console will display a summary table, and a full report will be saved in the root directory.
# infostealer
