import os
import random
import string
import re
import time
import httpx
from playwright.sync_api import sync_playwright

# --- FUNGSI EMAIL SEMENTARA (Mail.tm) ---
def get_temp_email():
    with httpx.Client() as client:
        try:
            r = client.get("https://api.mail.tm/domains", timeout=10)
            domain = r.json()['hydra:member'][0]['domain']
        except Exception:
            domain = "mail.tm"
            
        local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        address = f"{local}@{domain}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        
        client.post("https://api.mail.tm/accounts", json={"address": address, "password": password}, timeout=10)
        r = client.post("https://api.mail.tm/token", json={"address": address, "password": password}, timeout=10)
        return address, r.json()['token']

def get_otp(token, timeout=120):
    with httpx.Client() as client:
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = client.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {token}"}, timeout=10)
                msgs = r.json()['hydra:member']
                if msgs:
                    msg_id = msgs[0]['id']
                    msg = client.get(f"https://api.mail.tm/messages/{msg_id}", headers={"Authorization": f"Bearer {token}"}, timeout=10).json()
                    text = msg.get('text', '') + " ".join(msg.get('html', []))
                    match = re.search(r'\b(\d{6})\b', text)
                    if match:
                        return match.group(1)
            except Exception:
                pass
            time.sleep(4)
        raise Exception("OTP tidak ditemukan dalam batas waktu")

# --- FUNGSI UTAMA FARMING MUSE.AI ---
def run_one(headless=True):
    proxy_url = os.getenv("PROXY_URL")
    invite_code = os.getenv("INVITE_CODE")
    
    if proxy_url:
        print(f"[*] Mengetes koneksi Proxy...")
        try:
            with httpx.Client(proxy=proxy_url, timeout=15) as client:
                ip_check = client.get("https://api.ipify.org?format=json")
                print(f"[+] Proxy Terhubung! IP Keluar: {ip_check.json()['ip']}")
        except Exception as e:
            print(f"[-] Peringatan: Proxy gagal terhubung atau lambat. ({e})")

    email_address, email_token = get_temp_email()
    print(f"[*] Menggunakan email: {email_address}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            proxy={"server": proxy_url} if proxy_url else None,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        page = context.new_page()
        page.set_default_timeout(90000) 
        
        try:
            print("[*] Membuka halaman Muse.ai...")
            page.goto("https://muse.ai/join", wait_until="commit", timeout=90000)
            print("[*] Halaman terhubung. Menunggu React/Cloudflare selesai...")
            time.sleep(10)
            
            email_input = page.locator('input[type="email"]').first
            if not email_input.is_visible():
                raise Exception("Form email tidak muncul. Kemungkinan diblokir Cloudflare (IP Proxy buruk).")
            
            print("[*] Form email ditemukan. Mengisi email...")
            email_input.fill(email_address)
            page.locator('button[type="submit"]').first.click()
            
            print("[*] Menunggu OTP dari email...")
            time.sleep(5)
            otp = get_otp(email_token)
            print(f"[+] OTP diterima: {otp}")
            
            page.locator('input[type="text"]').first.fill(otp)
            page.locator('button[type="submit"]').first.click()
            
            print("[*] Menunggu verifikasi akun...")
            time.sleep(10)
            
            if invite_code:
                print(f"[*] Menerapkan kode referral: {invite_code}")
                try:
                    page.goto("https://muse.ai/settings", wait_until="domcontentloaded", timeout=60000)
                    time.sleep(5)
                    ref_input = page.locator('input[placeholder*="invite" i], input[placeholder*="referral" i]').first
                    if ref_input.is_visible():
                        ref_input.fill(invite_code)
                        page.locator('button:has-text("Redeem"), button:has-text("Apply")').first.click()
                        time.sleep(5)
                except Exception as e:
                    print(f"[-] Gagal memasukkan referral: {e}")
            
            print(f"[+] SUKSES! Akun {email_address} berhasil dibuat.")
            return True

        except Exception as e:
            # 1. CETAK ERROR ASLINYA DULU
            print(f"[-] Error Utama: {e}")
            
            # 2. Screenshot dengan batas waktu sangat pendek (5 detik saja)
            try:
                page.screenshot(path=f"/tmp/muse_fail_{email_address}.png", timeout=5000)
                print("[*] Screenshot error berhasil disimpan.")
            except Exception as ss_err:
                print(f"[-] Gagal mengambil screenshot (Browser hang): {ss_err}")
                
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    run_one(headless=True)
