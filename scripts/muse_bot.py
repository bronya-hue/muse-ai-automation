import os
import sys
import time
import random
import csv
import re
import argparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Pastikan path bisa membaca folder scripts
ROOT = os.getcwd()
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass

# Import dari file lain di dalam folder scripts
try:
    from accounts import create_inbox, fetch_otp
    from automate_account import run_all_after_email, type_verified, log
except ImportError as e:
    print(f"[ERROR] Gagal import modul lokal: {e}")
    sys.exit(1)

INVITE_CODE = os.getenv("INVITE_CODE", "")

def save_to_ledger(email, password, uid):
    """Menyimpan akun yang berhasil dibuat ke accounts.csv"""
    file_path = os.path.join(ROOT, "accounts.csv")
    file_exists = os.path.isfile(file_path)
    
    try:
        with open(file_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["email", "password", "uid", "created_at"])
            writer.writerow([email, password, uid, time.strftime("%Y-%m-%d %H:%M:%S")])
        log(f"💾 Akun disimpan ke {file_path}")
    except Exception as e:
        log(f"❌ Gagal menyimpan ke ledger: {e}")

def create_full_account():
    log("Menyiapkan inbox...")
    try:
        email, inbox_token = create_inbox()
        # Buat password acak
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
            
            # Ambil halaman pertama yang sudah dibuka oleh launch_profile.js
            page = context.pages[0] if context.pages else context.new_page()
            
            # Pastikan di halaman signup
            if "muse.ai/join" not in page.url:
                page.goto("https://muse.ai/join", wait_until="domcontentloaded", timeout=60000)

            log("waiting for the signup form to hydrate...")
            
            # 🔥 KUNCI PERBAIKAN: Tunggu penanda Next.js selesai loading
            try:
                page.wait_for_selector("#__next-route-announcer__", timeout=60000)
                log("Next.js hydration marker found.")
            except PlaywrightTimeoutError:
                log("⚠️ Penanda Next.js tidak muncul, tapi kita coba lanjut...")

            # Tunggu input email benar-benar muncul dan siap
            try:
                page.wait_for_selector('input[type="email"]', state="visible", timeout=30000)
                log("Email input is ready.")
            except PlaywrightTimeoutError:
                log("❌ email form never hydrated")
                page.screenshot(path=os.path.join(ROOT, "artifacts", "muse_no_input.png"))
                log(f"url: {page.url}")
                return None

            # 1. Isi Email
            log(f"Mengisi email: {email}")
            email_input = page.locator('input[type="email"]').first
            type_verified(page, email_input, email)
            time.sleep(1)

            # 2. Klik Continue
            log("Mengklik tombol Continue...")
            submit_btn = page.locator('button:has-text("Continue"), button[type="submit"]').first
            submit_btn.click(force=True)
            
            # 3. Tunggu form OTP (jika ada)
            log("Menunggu form OTP...")
            otp_selector = 'input[autocomplete="one-time-code"], input[name="code"]'
            try:
                page.wait_for_selector(otp_selector, state="visible", timeout=15000)
                log("Form OTP muncul. Mengambil kode dari email...")
                
                otp = fetch_otp(inbox_token)
                if not otp:
                    log("❌ Gagal mendapatkan kode OTP dari email.")
                    return None
                
                log(f"Kode OTP diterima: {otp}")
                otp_input = page.locator(otp_selector).first
                type_verified(page, otp_input, otp)
                
                # Klik continue setelah isi OTP
                page.locator('button:has-text("Continue"), button[type="submit"]').first.click(force=True)
                time.sleep(3)
            except PlaywrightTimeoutError:
                log("Form OTP tidak muncul, mungkin langsung lanjut ke step berikutnya.")

            # 4. Serahkan ke automate_account.py (Birthday -> Skip Card -> Workspace)
            log("Menjalankan otomasi lanjutan...")
            success = run_all_after_email(page, browser, INVITE_CODE)
            
            if success:
                # Simpan ke ledger
                # (Karena kita tidak tahu UID-nya dari script asli, kita isi dengan '-')
                save_to_ledger(email, password, "-")
                log("🎉 AKUN BERHASIL DIBUAT!")
                return {"email": email, "password": password}
            else:
                log("❌ Pipeline gagal di tahap verifikasi (CARD/403).")
                return None

        except Exception as e:
            log(f"❌ Error tidak terduga: {e}")
            return None
        finally:
            # Kita TIDAK menutup browser di sini, biarkan run_one.py yang menutupnya
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--one", action="store_true", help="Jalankan satu akun")
    args = parser.parse_args()

    if args.one:
        result = create_full_account()
        if result is None:
            sys.exit(1)
        else:
            print(f"SUCCESS_EMAIL={result['email']}")
            print(f"SUCCESS_PASS={result['password']}")
            sys.exit(0)
    else:
        print("Gunakan --one untuk menjalankan satu akun.")
