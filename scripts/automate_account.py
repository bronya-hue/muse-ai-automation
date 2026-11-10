import time
import random
from playwright.sync_api import Page

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def type_verified(page: Page, element, text: str):
    element.click()
    time.sleep(0.2)
    for char in text:
        element.type(char)
        time.sleep(random.uniform(0.05, 0.15))

def dismiss_dialog(page: Page):
    try:
        close_btns = page.locator('button[aria-label="Close"], button:has-text("Cancel")').all()
        for btn in close_btns:
            if btn.is_visible():
                btn.click(force=True)
                time.sleep(0.5)
    except Exception:
        pass

def get_random_name():
    return random.choice(["James", "John", "Robert", "Michael", "David"]), random.choice(["Smith", "Johnson", "Williams", "Brown", "Jones"])

def screen_of(page: Page) -> str:
    content = page.content().lower()
    if "workspace" in page.url.lower(): return "workspace"
    if "add a payment method" in content or "card number" in content: return "card"
    if "selesaikan pembuatan akun" in content or "nama depan" in content: return "meta_signup"
    return "unknown"

# ==========================================
# 🔥 LOGIKA FORM META (FIX IFRAME & FORCE CLICK)
# ==========================================
def do_meta_signup(page: Page):
    log("Memproses form Meta (Nama & Tanggal)...")
    first_name, last_name = get_random_name()
    dob_str = f"{random.randint(1, 28):02d}/{random.randint(1, 12):02d}/{random.randint(1995, 2000)}"
    
    # Cari frame (bisa jadi halaman utama atau iframe)
    target_frame = page.main_frame
    for frame in page.frames:
        if "facebook.com" in frame.url or "meta.com" in frame.url or "login" in frame.url:
            target_frame = frame
            break

    try:
        # 1. Isi Nama Depan
        fn_input = target_frame.locator('input[name="firstname"], input[placeholder*="depan" i], input[aria-label*="depan" i]').first
        if fn_input.count() > 0:
            fn_input.fill(first_name, force=True)
            fn_input.dispatch_event("input")
            log(f"Nama Depan: {first_name}")

        # 2. Isi Nama Belakang
        ln_input = target_frame.locator('input[name="lastname"], input[placeholder*="belakang" i], input[aria-label*="belakang" i]').first
        if ln_input.count() > 0:
            ln_input.fill(last_name, force=True)
            ln_input.dispatch_event("input")
            log(f"Nama Belakang: {last_name}")

        # 3. Isi Tanggal Lahir
        dob_input = target_frame.locator('input[name="birthday"], input[placeholder*="tanggal" i], input[aria-label*="tanggal" i]').first
        if dob_input.count() > 0:
            dob_input.click(force=True)
            time.sleep(0.5)
            # Ketik manual karakter per karakter
            page.keyboard.type(dob_str, delay=100)
            time.sleep(1)
            page.keyboard.press("Enter")
            log(f"Tanggal Lahir: {dob_str}")

        time.sleep(2)

        # 4. Cari Tombol Konfirmasi
        submit_btn = target_frame.locator('button:has-text("Konfirmasi"), button:has-text("Confirm"), button[type="submit"]').first
        
        if submit_btn.count() > 0:
            log("Menemukan tombol Konfirmasi. Memaksa klik...")
            
            # Hapus atribut disabled dan klik paksa lewat JS di dalam frame
            target_frame.evaluate("""() => {
                const btn = document.querySelector('button[type="submit"]') || Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Konfirmasi'));
                if(btn) {
                    btn.removeAttribute('disabled');
                    btn.removeAttribute('aria-disabled');
                    btn.click();
                }
            }""")
            log("✅ Tombol Konfirmasi sudah ditekan paksa.")
        else:
            log("❌ Tombol Konfirmasi tidak ditemukan.")
            
        time.sleep(5)
    except Exception as e:
        log(f"Error di do_meta_signup: {e}")

def run_all_after_email(page: Page, browser, invite_code: str = ""):
    for step in range(15):
        current = screen_of(page)
        log(f"Screen: {current.upper()}")

        if current == "meta_signup":
            do_meta_signup(page)
        elif current == "workspace":
            log("🎉 BERHASIL MASUK KE WORKSPACE!")
            return True
        elif current == "card":
            log("❌ Kena verifikasi kartu (IP terdeteksi bot).")
            return False
            
        time.sleep(3)
    return False
