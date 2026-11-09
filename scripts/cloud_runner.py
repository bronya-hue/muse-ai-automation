"""
Cloud Browser Runner untuk Muse.ai (Bypass VCC)
Jalankan di Railway.app tanpa perlu CloakBrowser/Chromium lokal.
"""
import os
import time
import random
import argparse
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from browser_use_sdk import BrowserUseClient

# Import fungsi-fungsi dari repo asli
from muse_bot import log, wait_hydrated, type_verified, _connect
from automate_account import (
    screen_of, do_birthday, do_disclosure, do_redeem,
    dismiss_dialog, CARD_SEL, take_status_snapshot
)
from accounts import create_inbox, fetch_otp

load_dotenv()

# ==========================================
# KONFIGURASI CLOUD BROWSER
# ==========================================
BROWSER_USE_API_KEY = os.getenv("BROWSER_USE_API_KEY")
PROXY_URL = os.getenv("PROXY_URL")  # Format: http://user:pass@host:port
INVITE_CODE = os.getenv("INVITE_CODE", "")

def create_cloud_session():
    """Membuat sesi Cloud Browser dengan proxy US yang bersih."""
    log("Membuat Cloud Browser session (US Residential)...")
    client = BrowserUseClient(api_key=BROWSER_USE_API_KEY)
    
    # Gunakan proxy country US untuk lingkungan paling bersih
    # Jika ingin memakai 28k proxy FloppyData, ganti dengan parameter proxy kustom
    session = client.browsers.create(
        proxy_country_code="us",
        # Untuk proxy kustom FloppyData:
        # proxy={"server": "http://geo.floppydata.com:10080", "username": "...", "password": "..."}
    )
    log(f"Cloud session dibuat: {session.ws_endpoint}")
    return session.ws_endpoint

def do_skip_card(page):
    """
    Mencoba melewati verifikasi kartu dengan opsi 'Link Facebook' / 'Instagram'.
    Jika tidak ada opsi tersebut dan environment sangat bersih, halaman mungkin
    sudah otomatis lolos.
    """
    log("Terdeteksi halaman verifikasi kartu. Mencoba skip via Social Linking...")
    time.sleep(2)

    # Daftar kemungkinan selektor tombol Link Facebook/Instagram
    social_btns = [
        'button:has-text("Link Facebook")',
        'button:has-text("Continue with Facebook")',
        'button:has-text("Facebook")',
        'button:has-text("Instagram")',
        '[data-pel-click*="facebook"]',
        '[data-pel-click*="social"]'
    ]

    for sel in social_btns:
        btn = page.locator(sel).first
        if btn.count() > 0 and btn.is_visible():
            log(f"Menemukan tombol social: {sel}")
            try:
                btn.click(force=True)
                time.sleep(5)
                # Cek apakah masih di halaman kartu atau sudah pindah
                if screen_of(page) != "card":
                    log("Berhasil melewati verifikasi kartu via social link!")
                    return True
            except Exception as e:
                log(f"Gagal klik social button: {e}")

    # Jika tidak ada tombol social, coba cari tombol "Skip" atau "Not now"
    skip_btns = [
        'button:has-text("Skip")',
        'button:has-text("Not now")',
        'button:has-text("Later")'
    ]
    for sel in skip_btns:
        btn = page.locator(sel).first
        if btn.count() > 0 and btn.is_visible():
            log(f"Menemukan tombol skip: {sel}")
            btn.click(force=True)
            time.sleep(3)
            return True

    log("Tidak ada tombol skip. Environment mungkin meminta kartu secara mutlak.")
    return False

def run_cloud_pipeline(custom_email=None):
    """Pipeline lengkap: buat email -> OTP -> birthday -> skip card -> redeem."""
    # 1. Setup Cloud Browser
    ws_endpoint = create_cloud_session()

    with sync_playwright() as p:
        # Connect ke Cloud Browser via CDP (bukan launch lokal)
        browser = p.chromium.connect_over_cdp(ws_endpoint)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()

        # 2. Buka halaman signup
        log("Membuka muse.ai/join...")
        page.goto("https://muse.ai/join", wait_until="networkidle", timeout=60000)

        # 3. Masukkan email (custom atau disposable)
        if custom_email:
            email = custom_email
            log(f"Menggunakan email kustom: {email}")
        else:
            email, inbox_token = create_inbox()
            log(f"Email disposable dibuat: {email}")

        # Isi form email
        email_input = page.locator('input[type="email"]').first
        wait_hydrated(page, 'input[type="email"]', 15)
        type_verified(page, email_input, email)
        page.locator('button:has-text("Continue")').first.click()
        time.sleep(3)

        # 4. Ambil OTP (jika disposable)
        if not custom_email:
            log("Menunggu OTP...")
            otp_code = fetch_otp(inbox_token)
            if not otp_code:
                log("Gagal mendapatkan OTP.")
                return False
            log(f"OTP diterima: {otp_code}")
            # Isi OTP (gunakan logika sr-only input dari repo asli)
            otp_input = page.locator('input[autocomplete="one-time-code"]').first
            # ... (gunakan fungsi type_verified atau page.keyboard.type)
            page.keyboard.type(otp_code, delay=100)
            time.sleep(3)

        # 5. Loop menangani layar (birthday -> disclosure -> card -> workspace)
        last_screen = None
        card_skipped = False

        for step in range(20):
            current = screen_of(page)
            if current != last_screen:
                log(f"Screen: {current}")
                last_screen = current

            if current == "birthday":
                do_birthday(page)
            elif current == "disclosure":
                do_disclosure(page)
            elif current == "card":
                if not card_skipped:
                    if do_skip_card(page):
                        card_skipped = True
                    else:
                        log("Gagal skip kartu. Pipeline berhenti.")
                        take_status_snapshot(page, "muse_card_stuck.png")
                        return False
            elif current in ("workspace", "redeem_entry", "redeem_input"):
                log("Berhasil masuk workspace!")
                break
            else:
                time.sleep(2)

        # 6. Redeem invite code (opsional)
        if INVITE_CODE:
            log(f"Redeem invite code: {INVITE_CODE}")
            do_redeem(page, INVITE_CODE)

        # 7. Simpan status
        log("Pipeline selesai. Akun siap digunakan.")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Muse.ai Cloud Runner (Skip VCC)")
    parser.add_argument("--email", help="Email kustom (opsional)")
    args = parser.parse_args()

    run_cloud_pipeline(custom_email=args.email)
