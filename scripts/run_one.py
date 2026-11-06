import os
import signal
import random
import string
import re
import time
import httpx
from playwright.sync_api import sync_playwright

# Mail.tm helper
def get_temp_email():
    with httpx.Client() as client:
        r = client.get("https://api.mail.tm/domains")
        domain = r.json()['hydra:member'][0]['domain']
        local = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{local}@{domain}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        
        client.post("https://api.mail.tm/accounts", json={"address": address, "password": password})
        r = client.post("https://api.mail.tm/token", json={"address": address, "password": password})
        return address, r.json()['token']

def get_otp(token):
    with httpx.Client() as client:
        for _ in range(30):
            r = client.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {token}"})
            msgs = r.json()['hydra:member']
            if msgs:
                msg_id = msgs[0]['id']
                msg = client.get(f"https://api.mail.tm/messages/{msg_id}", headers={"Authorization": f"Bearer {token}"}).json()
                text = msg.get('text', '') + " ".join(msg.get('html', []))
                match = re.search(r'\b(\d{6})\b', text)
                if match:
                    return match.group(1)
            time.sleep(3)
    raise Exception("OTP tidak ditemukan")

def run_one(headless=True):
    # 1. Setup environment
    env = dict(os.environ)
    proxy_url = env.get("PROXY_URL")
    invite_code = env.get("INVITE_CODE")
    
    email, token = get_temp_email()
    print(f"[*] Menggunakan email: {email}")
    
    # 2. Launch Browser
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            proxy={"server": proxy_url} if proxy_url else None,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context()
        page = context.new_page()
        
        try:
            print("[*] Membuka halaman Muse.ai...")
            page.goto("https://muse.ai/join", wait_until="domcontentloaded")
            time.sleep(3)
            
            # ... (Muse.ai specific selectors)
            page.fill('input[type="email"]', email)
            page.click('button[type="submit"]')
            time.sleep(5)
            
            print("[*] Menunggu OTP...")
            otp = get_otp(token)
            print(f"[+] OTP didapat: {otp}")
            
            page.fill('input[type="text"]', otp)
            page.click('button[type="submit"]')
            time.sleep(10)
            
            # Apply referral
            if invite_code:
                print("[*] Menerapkan kode referral...")
                page.goto("https://muse.ai/settings", wait_until="domcontentloaded")
                time.sleep(3)
                # ... logic
            
            # Save account
            with open("accounts.txt", "a") as f:
                f.write(f"{email}:{otp}\n")
                
        except Exception as e:
            print(f"[-] Error: {e}")
        finally:
            browser.close() # This is the safe way
            
if __name__ == "__main__":
    run_one(headless=True)
