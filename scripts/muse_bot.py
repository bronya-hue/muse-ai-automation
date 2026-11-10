import os
import sys
import time
import random
import csv
import argparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = os.getcwd()
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass

from accounts import create_inbox, fetch_otp
from automate_account import run_all_after_email, type_verified, log

INVITE_CODE = os.getenv("INVITE_CODE", "")

def save_to_ledger(email, password):
    file_path = os.path.join(ROOT, "accounts.csv")
    file_exists = os.path.isfile(file_path)
    try:
        with open(file_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["email", "password", "created_at"])
            writer.writerow([email, password, time.strftime("%Y-%m-%d %H:%M:%S")])
        log(f"💾 Akun disimpan ke {file_path}")
    except Exception as e:
        log(f"❌ Gagal menyimpan ke ledger: {e}")

def find_email_input(page):
    """Mencari field email dengan berbagai selector dan memeriksa iframe."""
    selectors = [
        'input[type="email"]',
        'input[name="email"]',
        'input[placeholder*="email" i]',
        'input[aria-label*="email" i]',
        'input[autocomplete="email"]',
    ]
    
    for sel in selectors:
        try:
            # Cek di halaman utama
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible(timeout=2000):
                log(f"✅ Field email ditemukan di halaman utama: {sel}")
                return loc
        except Exception:
            continue
            
    # Jika tidak ketemu, cek semua iframe
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        for sel in selectors:
            try:
                loc = frame.locator(sel).first
                if loc.count() > 0 and loc.is_visible(timeout=2000):
                    log(f"✅ Field email ditemukan di dalam iframe ({frame.url[:50]}...): {sel}")
                    return loc
            except Exception:
                continue
                
    return None

def create_full_account():
    log("Menyiapkan inbox...")
    try:
        email, inbox_token = create_inbox()
        password = f"muse_{random.randint(100000, 999999)}_{random.randint(1000, 9999)}"
        log(f"[*] Inbox ready : {email}")
        log(f"[*] Inbox password: {password}")
    except Exception as e:
        log(f"❌ Gagal membuat inbox: {e}")
        return None

    log("Menghubungkan ke Chromium via CDP...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()
            
            if "muse.ai/join" not in page.url:
                page.goto("https://muse.ai/join", wait_until="domcontentloaded", timeout=60000)

            log("Menunggu Next.js hydration...")
            try:
                page.wait_for_selector("#__next-route-announcer__", timeout=60000)
                log("Next.js hydration marker found.")
            except PlaywrightTimeoutError:
                log("⚠️ Penanda Next.js tidak muncul, tetap lanjut...")

            # 🔥 Percobaan 1: Cari field email secara langsung
            log("Mencari field input email...")
            email_input = find_email_input(page)

            # 🔥 Percobaan 2: Jika tidak ketemu, klik tombol "Sign up with email" (jika ada)
            if not email_input:
                log("Field email tidak ditemukan langsung. Mencoba mencari tombol alternatif...")
                alt_buttons = [
                    'button:has-text("Sign up with email")',
                    'button:has-text("Continue with email")',
                    'button:has-text("Email")',
                    'a:has-text("Sign up with email")',
                ]
                for btn_sel in alt_buttons:
                    try:
                        btn = page.locator(btn_sel).first
                        if btn.count() > 0 and btn.is_visible():
                            log(f"Menemukan tombol alternatif: {btn_sel}. Mengklik...")
                            btn.click(force=True)
                            time.sleep(3)
                            # Coba cari lagi setelah klik
                            email_input = find_email_input(page)
                            if email_input:
                                break
                    except Exception:
                        continue

            if not email_input:
                log("❌ Field email tidak ditemukan setelah semua percobaan.")
                page.screenshot(path=os.path.join(ROOT, "artifacts", "muse_no_input_final.png"))
                log(f"url: {page.url}")
                return None

            # Isi email
            log(f"Mengisi email: {email}")
            type_verified(page, email_input, email)
            time.sleep(1)

            # Klik Continue
            log("Mengklik tombol Continue...")
            submit_btn = page.locator('button:has-text("Continue"), button[type="submit"]').first
            submit_btn.click(force=True)
            
            # Tunggu OTP
            log("Menunggu form OTP...")
            otp_selector = 'input[autocomplete="one-time-code"], input[name="code"], input[placeholder*="code" i]'
            try:
                page.wait_for_selector(otp_selector, state="visible", timeout=20000)
                log("Form OTP muncul. Mengambil kode dari email...")
                
                otp = fetch_otp(inbox_token)
                if not otp:
                    log("❌ Gagal mendapatkan kode OTP dari email.")
                    return None
                
                log(f"Kode OTP diterima: {otp}")
                otp_input = page.locator(otp_selector).first
                type_verified(page, otp_input, otp)
                
                page.locator('button:has-text("Continue"), button[type="submit"]').first.click(force=True)
                time.sleep(3)
            except PlaywrightTimeoutError:
                log("Form OTP tidak muncul, lanjut ke tahap berikutnya.")

            # Jalankan otomasi lanjutan
            log("Menjalankan otomasi lanjutan (Birthday -> Skip Card)...")
            success = run_all_after_email(page, browser, INVITE_CODE)
            
            if success:
                save_to_ledger(email, password)
                log("🎉 AKUN BERHASIL DIBUAT!")
                return {"email": email, "password": password}
            else:
                log("❌ Pipeline gagal di tahap verifikasi (CARD/403).")
                return None

        except Exception as e:
            log(f"❌ Error tidak terduga: {e}")
            return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--one", action="store_true")
    args = parser.parse_args()

    if args.one:
        result = create_full_account()
        if result is None:
            sys.exit(1)
        else:
            print(f"SUCCESS_EMAIL={result['email']}")
            print(f"SUCCESS_PASS={result['password']}")
            sys.exit(0)
