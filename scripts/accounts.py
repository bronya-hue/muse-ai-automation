import requests
import random
import string
import time
import re

MAILTM_BASE = "https://api.mail.tm"

def create_inbox():
    """Membuat email sementara di mail.tm dan mengembalikan (email, token)"""
    # 1. Ambil domain
    r = requests.get(f"{MAILTM_BASE}/domains", timeout=10)
    domains = r.json().get("hydra:member", [])
    if not domains:
        raise Exception("Tidak ada domain tersedia di mail.tm")
    
    domain = domains[0]["domain"]
    
    # 2. Buat username dan password acak
    username = "muse" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    email = f"{username}@{domain}"
    password = "".join(random.choices(string.ascii_letters + string.digits + "!@#", k=16))
    
    # 3. Daftarkan akun
    r = requests.post(f"{MAILTM_BASE}/accounts", json={"address": email, "password": password}, timeout=10)
    if r.status_code not in [200, 201]:
        raise Exception(f"Gagal membuat email: {r.text}")
        
    # 4. Ambil token untuk membaca inbox
    r = requests.post(f"{MAILTM_BASE}/token", json={"address": email, "password": password}, timeout=10)
    token = r.json().get("token")
    
    return email, token

def fetch_otp(token, timeout=120):
    """Menunggu email masuk dan mengambil 6 digit OTP"""
    start = time.time()
    headers = {"Authorization": f"Bearer {token}"}
    
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{MAILTM_BASE}/messages", headers=headers, timeout=10)
            messages = r.json().get("hydra:member", [])
            
            if messages:
                # Ambil pesan terbaru
                msg_id = messages[0]["id"]
                detail_r = requests.get(f"{MAILTM_BASE}/messages/{msg_id}", headers=headers, timeout=10)
                detail = detail_r.json()
                text = detail.get("text", "") or detail.get("html", "")
                
                # Cari kode 6 digit
                match = re.search(r'\b(\d{6})\b', text)
                if match:
                    return match.group(1)
        except Exception as e:
            pass # Abaikan error jaringan, coba lagi
            
        time.sleep(3)
    return None
