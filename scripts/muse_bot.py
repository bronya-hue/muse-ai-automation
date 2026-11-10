import os
import sys
import time
import random
import csv
import argparse
import re
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
        log(f"❌ Gagal simpan ke ledger: {e}")

def wait_and_find_email_input(page, timeout=45):
    """Mencari form email dengan SABAR (looping), termasuk ngecek iframe & klik tombol alternatif."""
    log("Mencari form email (sabar menunggu render hingga 45 detik)...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # 1. Cek di halaman utama
        for sel in ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="email" i]', 'input[autocomplete="email"]']:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0 and loc.is_visible():
                    log(f"✅ Form email ketemu di halaman utama: {sel}")
                    return loc
            except Exception:
                pass
                
        # 2. Cek di dalam iframe (jika ada)
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            for sel in ['input[type="email"]', 'input[name="email"]']:
                try:
                    loc = frame.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        log(f"✅ Form email ketemu di iframe: {sel}")
                        return loc
                except Exception:
                    pass

        # 3. Kalau belum ketemu, coba cari tombol alternatif (misal "Email") dan klik
        alt_buttons = [
            'button:has-text("Sign up with email")',
            'button:has-text("Continue with email")',
            'button:has-text("Email")',
            'a:has-text("Email")'
        ]
        for btn_sel in alt_buttons:
            try:
                btn = page.locator(btn_sel).first
                if btn.count() > 0 and btn.is_visible():
                    log(f"Menemukan tombol alternatif: '{btn_sel}'. Mencoba klik...")
                    btn.click(force=True, timeout=3000)
                    time.sleep(2) # Tunggu transisi
                    break
            except Exception:
                pass
                
        time.sleep(2) # Jeda sebelum loop berikutnya
        
    return None

def create_full_account():
    log("Menyiapkan inbox email...")
    try:
        email, inbox_token = create_inbox()
        password = f"muse_{random.randint(100000, 999999)}_{random.randint(1000, 9999)}"
        log(f"[*] Email : {email}")
        log(f"[*] Password : {password}")
    except Exception as e:
        log(f"❌ Gagal buat inbox: {e}")
        return None

    log("Menghubungkan ke Chromium via CDP...")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()
            
            if "muse.ai/join" not in page.url:
                page.goto("https://muse.ai/join", wait_until="domcontentloaded", timeout=60000)

            log("Menunggu Next.js selesai loading (hydration)...")
            try:
                page.wait_for_selector("#__next-route-announcer__", timeout=60000)
                log("✅ Next.js sudah siap.")
            except PlaywrightTimeoutError:
                log("❌ Next.js loading timeout. Proxy mungkin terlalu lambat.")

            email_input = wait_and_find_email_input(page)

            if not email_input:
                log("❌ Tetap nggak nemu form email setelah menunggu 45 detik.")
                log("⚠️ Mengambil screenshot untuk melihat layar sebenarnya...")
                path_ss = os.path.join(ROOT, "artifacts", "gagal_nemu_form.png")
                page.screenshot(path=path_ss, full_page=True)
                log(f"📸 Screenshot disimpan di: {path_ss}")
                log("Silakan cek file tersebut di repo Anda. Kemungkinan ada Captcha atau tampilan berubah.")
                return None

            # Isi email
            log(f"Mengisi email: {email}")
            type_verified(page, email_input, email)
            time.sleep(1)

            # Klik lanjut
            log("Mengklik tombol Continue...")
            submit_btn = page.locator('button:has-text("Continue"), button[type="submit"]').first
            submit_btn.click(force=True)
            
            # Tunggu OTP
            log("Menunggu form OTP (20 detik)...")
            otp_selector = 'input[autocomplete="one-time-code"], input[name="code"], input[placeholder*="code" i]'
            try:
                page.wait_for_selector(otp_selector, state="visible", timeout=20000)
                log("Form OTP muncul. Ngambil kode dari email...")
                
                otp = fetch_otp(inbox_token)
                if not otp:
                    log("❌ Gagal dapet OTP dari email (email tidak masuk).")
                    return None
                
                log(f"Kode OTP: {otp}")
                otp_input = page.locator(otp_selector).first
                type_verified(page, otp_input, otp)
                
                page.locator('button:has-text("Continue"), button[type="submit"]').first.click(force=True)
                time.sleep(3)
            except PlaywrightTimeoutError:
                log("Form OTP nggak muncul, lanjut ke step berikutnya (mungkin langsung minta umur).")

            # Lanjut ke automate_account (isi umur -> skip kartu)
            log("Menjalankan otomasi lanjutan (Birthday -> Skip Card)...")
            success = run_all_after_email(page, browser, INVITE_CODE)
            
            if success:
                save_to_ledger(email, password)
                log("🎉 AKUN BERHASIL DIBUAT!")
                return {"email": email, "password": password}
            else:
                log("❌ Pipeline gagal (kena CARD/403).")
                return None

        except Exception as e:
            log(f"❌ Error nggak terduga: {e}")
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
