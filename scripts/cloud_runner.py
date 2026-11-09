import os
import time
import random
import argparse
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from browser_use_sdk import BrowserUseClient

# Import fungsi dari file automate_account.py yang barusan kita buat
from automate_account import (
    run_all_after_email, type_verified, wait_hydrated, log
)

# Import fungsi email dari repo asli Anda
from accounts import create_inbox, fetch_otp

load_dotenv()

BROWSER_USE_API_KEY = os.getenv("BROWSER_USE_API_KEY")
PROXY_FILE = "proxies.txt" # Pastikan file ini ada di root folder Railway

# ==========================================
# FUNGSI AMBIL PROXY DARI 28K LIST
# ==========================================
def get_random_proxy():
    """Membaca proxies.txt dan mengembalikan 1 proxy acak dalam format dictionary."""
    try:
        with open(PROXY_FILE, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        
        if not proxies:
            log("⚠️ File proxies.txt kosong. Jalan tanpa proxy.")
            return None
            
        raw = random.choice(proxies)
        parts = raw.split(':')
        
        # Format FloppyData: host:port:user:pass
        if len(parts) == 4:
            host, port, user, pwd = parts
            return {
                "server": f"http://{host}:{port}",
                "username": user,
                "password": pwd
            }
        # Format biasa: host:port
        elif len(parts) == 2:
            host, port = parts
            return {
                "server": f"http://{host}:{port}"
            }
        else:
            log(f"⚠️ Format proxy tidak dikenali: {raw}")
            return None
            
    except FileNotFoundError:
        log(f"❌ File {PROXY_FILE} tidak ditemukan! Jalan tanpa proxy.")
        return None

# ==========================================
# SETUP CLOUD BROWSER DENGAN PROXY
# ==========================================
def create_cloud_session():
    log("Membuat Cloud Browser session...")
    client = BrowserUseClient(api_key=BROWSER_USE_API_KEY)
    
    proxy_config = get_random_proxy()
    if proxy_config:
        log(f"Menggunakan Proxy: {proxy_config['server']}")
    
    # Buat sesi cloud browser dengan menyisipkan proxy FloppyData
    session = client.browsers.create(
        proxy=proxy_config  # <--- PROXY 28K ANDA DIPASANG DI SINI
    )
    
    log(f"Cloud session dibuat: {session.ws_endpoint}")
    return session.ws_endpoint

# ==========================================
# PIPELINE UTAMA
# ==========================================
def run_cloud_pipeline(custom_email=None):
    ws_endpoint = create_cloud_session()

    with sync_playwright() as p:
        # Hubungkan ke Cloud Browser via CDP
        browser = p.chromium.connect_over_cdp(ws_endpoint)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()

        # 1. Buka halaman signup Muse.ai
        log("Membuka muse.ai/join...")
        page.goto("https://muse.ai/join", wait_until="networkidle", timeout=60000)

        # 2. Masukkan email
        if custom_email:
            email = custom_email
            log(f"Menggunakan email kustom: {email}")
            inbox_token = None
        else:
            email, inbox_token = create_inbox()
            log(f"Email disposable dibuat: {email}")

        # Isi form email
        email_input = page.locator('input[type="email"]').first
        wait_hydrated(page, 'input[type="email"]', 15)
        type_verified(page, email_input, email)
        
        # Klik Continue
        page.locator('button:has-text("Continue")').first.click()
        time.sleep(4)

        # 3. Ambil OTP jika pakai email disposable
        if not custom_email and inbox_token:
            log("Menunggu OTP masuk...")
            otp_code = fetch_otp(inbox_token)
            if not otp_code:
                log("❌ Gagal mendapatkan OTP.")
                browser.close()
                return False
            log(f"OTP diterima: {otp_code}")
            
            # Ketik OTP
            page.keyboard.type(otp_code, delay=100)
            time.sleep(4)

        # 4. Serahkan ke automate_account.py untuk skip card & birthday
        log("Memulai proses otomasi (Birthday -> Skip VCC -> Workspace)...")
        success = run_all_after_email(page, invite_code=os.getenv("INVITE_CODE", ""))
        
        if success:
            log("🎉 Pipeline Selesai! Akun Muse.ai siap.")
        else:
            log("❌ Pipeline Gagal atau terhenti di verifikasi kartu.")
            
        browser.close()
        return success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Muse.ai Cloud Runner (Bypass VCC)")
    parser.add_argument("--email", help="Email kustom (opsional)")
    args = parser.parse_args()

    run_cloud_pipeline(custom_email=args.email)
