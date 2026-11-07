import os
import random
import string
import re
import time
import httpx
from patchright.sync_api import sync_playwright # Ganti import

# --- FUNGSI EMAIL GACORMAIL ---
def get_gacormail():
    # Catatan: Gacormail tidak memiliki API publik resmi.
    # Kita menggunakan endpoint internal yang biasanya dipakai frontend.
    # Jika gagal, fallback ke Mail.tm.
    with httpx.Client() as client:
        try:
            # 1. Buat inbox baru
            r = client.post("https://www.gacormail.me/api/v1/inbox", timeout=15)
            data = r.json()
            email_address = data.get("address")
            token = data.get("token") # Atau sesuaikan dengan response API mereka
            
            if email_address and token:
                print(f"[+] Berhasil membuat email Gacormail: {email_address}")
                return email_address, token, "gacormail"
        except Exception as e:
            print(f"[-] Gacormail gagal: {e}. Fallback ke Mail.tm...")
        
        # Fallback ke Mail.tm jika Gacormail error
        try:
            r = client.get("https://api.mail.tm/domains", timeout=10)
            domain = r.json()['hydra:member'][0]['domain']
            local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
            address = f"{local}@{domain}"
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            client.post("https://api.mail.tm/accounts", json={"address": address, "password": password}, timeout=10)
            r = client.post("https://api.mail.tm/token", json={"address": address, "password": password}, timeout=10)
            return address, r.json()['token'], "mailtm"
        except Exception as e:
            raise Exception(f"Semua provider email gagal: {e}")

def get_otp(provider, token, timeout=120):
    with httpx.Client() as client:
        start = time.time()
        while time.time() - start < timeout:
            try:
                if provider == "gacormail":
                    # Endpoint baca pesan Gacormail (sesuaikan jika berbeda)
                    r = client.get(f"https://www.gacormail.me/api/v1/inbox/{token}/messages", timeout=10)
                    msgs = r.json().get("messages", [])
                    if msgs:
                        text = msgs[0].get("body", "") + msgs[0].get("html", "")
                        match = re.search(r'\b(\d{6})\b', text)
                        if match: return match.group(1)
                else:
                    # Mail.tm
                    r = client.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {token}"}, timeout=10)
                    msgs = r.json()['hydra:member']
                    if msgs:
                        msg_id = msgs[0]['id']
                        msg = client.get(f"https://api.mail.tm/messages/{msg_id}", headers={"Authorization": f"Bearer {token}"}, timeout=10).json()
                        text = msg.get('text', '') + " ".join(msg.get('html', []))
                        match = re.search(r'\b(\d{6})\b', text)
                        if match: return match.group(1)
            except Exception:
                pass
            time.sleep(4)
        raise Exception("OTP tidak ditemukan dalam batas waktu")

# --- FUNGSI UTAMA ---
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

    email_address, email_token, provider = get_gacormail()
    print(f"[*] Menggunakan email: {email_address}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            proxy={"server": proxy_url} if proxy_url else None,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors"]
        )
        # Patchright otomatis menangani stealth, tapi kita tetap bisa menambahkan context
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
            time.sleep(15) # Patchright mungkin butuh waktu lebih untuk menyelesaikan challenge
            
            email_input = page.locator('input[type="email"]').first
            if not email_input.is_visible():
                raise Exception("Form email tidak muncul. Proxy mungkin masih diblokir atau Patchright gagal menyelesaikan challenge.")
            
            print("[*] Form email ditemukan. Mengisi email...")
            email_input.fill(email_address)
            page.locator('button[type="submit"]').first.click()
            
            print("[*] Menunggu OTP dari email...")
            time.sleep(5)
            otp = get_otp(provider, email_token)
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
            print(f"[-] Error Utama: {e}")
            try:
                page.screenshot(path=f"/tmp/muse_fail_{email_address}.png", timeout=5000)
            except Exception:
                pass
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    run_one(headless=True)
