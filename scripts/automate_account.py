import time
import random
from playwright.sync_api import Page

# ==========================================
# FUNGSI UTILITY & LOGGING
# ==========================================
def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def wait_hydrated(page: Page, selector: str, timeout: int = 15):
    try:
        page.wait_for_selector(selector, state="visible", timeout=timeout * 1000)
    except Exception:
        pass

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

def take_status_snapshot(page: Page, filename: str):
    try:
        page.screenshot(path=filename, full_page=True)
        log(f"Screenshot disimpan: {filename}")
    except Exception as e:
        log(f"Gagal mengambil screenshot: {e}")

# ==========================================
# DATA NAMA ACAK UNTUK AKUN META
# ==========================================
FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

def get_random_name():
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)

# ==========================================
# DETEKSI SCREEN (STATE MACHINE)
# ==========================================
def screen_of(page: Page) -> str:
    url = page.url.lower()
    
    if "workspace" in url or "dashboard" in url:
        return "workspace"
    
    content = page.content().lower()
    
    # 🔥 DETEKSI FORM META BARU (Nama Depan, Belakang, Tanggal)
    if "selesaikan pembuatan akun" in content or "nama depan" in content or "nama belakang" in content:
        return "meta_signup"
    
    if "add a payment method" in content or "credit card" in content or "card number" in content:
        return "card"
    if "ulang tahun" in content or "date of birth" in content or "birthday" in content:
        return "birthday"
    if "terms" in content or "privacy policy" in content or "agree" in content or "konfirmasi" in content:
        return "disclosure"
    if "redeem" in content or "invite code" in content:
        return "redeem_entry"
    
    return "unknown"

# ==========================================
# AKSI-AKSI OTOMASI (HANDLERS)
# ==========================================
def do_meta_signup(page: Page):
    """Mengisi form pembuatan akun Meta (Nama Depan, Belakang, Tanggal Lahir)"""
    log("Mengisi form pembuatan akun Meta (Nama & Tanggal Lahir)...")
    dismiss_dialog(page)
    
    first_name, last_name = get_random_name()
    
    try:
        # Isi Nama Depan
        fn_input = page.locator('input[placeholder="Nama depan"], input[name="firstname"], input[name="first_name"]').first
        if fn_input.count() > 0 and fn_input.is_visible():
            type_verified(page, fn_input, first_name)
            
        # Isi Nama Belakang
        ln_input = page.locator('input[placeholder="Nama belakang"], input[name="lastname"], input[name="last_name"]').first
        if ln_input.count() > 0 and ln_input.is_visible():
            type_verified(page, ln_input, last_name)
            
        # Isi Tanggal Lahir (Format biasanya YYYY-MM-DD atau DD-MM-YYYY)
        # Gunakan tahun 1995-2000 agar aman dari "underage"
        dob_input = page.locator('input[placeholder="Tanggal"], input[type="date"], input[name="birthday"]').first
        if dob_input.count() > 0 and dob_input.is_visible():
            # Set nilai langsung lewat JS jika input tipe date, atau ketik manual
            dob = f"{random.randint(1, 12):02d}/{random.randint(1, 28):02d}/{random.randint(1995, 2000)}"
            type_verified(page, dob_input, dob)
            # Jika datepicker muncul, klik enter atau pilih tanggal
            page.keyboard.press("Enter")
            time.sleep(1)

        # Klik tombol Konfirmasi
        submit_btn = page.locator('button:has-text("Konfirmasi"), button:has-text("Confirm"), button[type="submit"]').first
        if submit_btn.is_visible():
            log("Mengklik tombol Konfirmasi...")
            submit_btn.click(force=True)
        
        time.sleep(5) # Tunggu loading setelah submit
    except Exception as e:
        log(f"Error di do_meta_signup: {e}")

def do_birthday(page: Page):
    """Fungsi lama untuk mengisi tanggal lahir jika terpisah"""
    log("Mengisi tanggal lahir...")
    dismiss_dialog(page)
    try:
        month_input = page.locator('select[name="month"], input[name="month"]').first
        day_input = page.locator('select[name="day"], input[name="day"]').first
        year_input = page.locator('select[name="year"], input[name="year"]').first

        if month_input.count() > 0:
            month = str(random.randint(1, 12))
            day = str(random.randint(1, 28))
            year = str(random.randint(1995, 2000))
            
            if month_input.evaluate("el => el.tagName") == "SELECT":
                month_input.select_option(month)
                day_input.select_option(day)
                year_input.select_option(year)
            else:
                month_input.fill(month)
                day_input.fill(day)
                year_input.fill(year)

        submit_btn = page.locator('button[type="submit"], button:has-text("Next"), button:has-text("Continue"), button:has-text("Lanjut")').first
        if submit_btn.is_visible():
            submit_btn.click(force=True)
        time.sleep(3)
    except Exception as e:
        log(f"Error di do_birthday: {e}")

def do_disclosure(page: Page):
    log("Menyetujui disclosure/terms...")
    dismiss_dialog(page)
    try:
        checkboxes = page.locator('input[type="checkbox"]').all()
        for cb in checkboxes:
            if not cb.is_checked():
                cb.check(force=True)
        
        agree_btn = page.locator('button:has-text("Agree"), button:has-text("I accept"), button:has-text("Continue"), button:has-text("Setuju")').first
        if agree_btn.is_visible():
            agree_btn.click(force=True)
        time.sleep(3)
    except Exception as e:
        log(f"Error di do_disclosure: {e}")

def do_skip_card(page: Page) -> bool:
    log("Terdeteksi halaman minta kartu. Mencoba BYPASS...")
    dismiss_dialog(page)
    
    social_selectors = [
        'button:has-text("Link Facebook")',
        'button:has-text("Continue with Facebook")',
        'button:has-text("Facebook")',
        'button:has-text("Instagram")',
    ]
    
    for sel in social_selectors:
        btn = page.locator(sel).first
        if btn.count() > 0 and btn.is_visible():
            log(f"Menemukan tombol social: {sel}. Mengklik...")
            try:
                btn.click(force=True)
                time.sleep(5)
                if screen_of(page) != "card":
                    log("✅ BERHASIL BYPASS KARTU via Social Link!")
                    return True
            except Exception:
                pass

    log("❌ Tidak ada tombol bypass. Lingkungan (IP) mungkin terdeteksi bot.")
    return False

def do_redeem(page: Page, invite_code: str):
    log(f"Memasukkan kode invite: {invite_code}")
    try:
        redeem_input = page.locator('input[name="code"], input[placeholder*="code"]').first
        if redeem_input.is_visible():
            type_verified(page, redeem_input, invite_code)
            submit_btn = page.locator('button:has-text("Redeem"), button:has-text("Submit")').first
            if submit_btn.is_visible():
                submit_btn.click(force=True)
            time.sleep(5)
    except Exception as e:
        log(f"Error di do_redeem: {e}")

# ==========================================
# PIPELINE UTAMA
# ==========================================
def run_all_after_email(page: Page, browser, invite_code: str = ""):
    last_screen = None
    card_skipped = False
    meta_signup_done = False
    
    for step in range(30):
        current_screen = screen_of(page)
        
        if current_screen != last_screen:
            log(f"--> Screen terdeteksi: {current_screen.upper()}")
            last_screen = current_screen

        if current_screen == "meta_signup":
            if not meta_signup_done:
                do_meta_signup(page)
                meta_signup_done = True
            else:
                time.sleep(3)
                
        elif current_screen == "birthday":
            do_birthday(page)
            
        elif current_screen == "disclosure":
            do_disclosure(page)
            
        elif current_screen == "card":
            if not card_skipped:
                success = do_skip_card(page)
                if success:
                    card_skipped = True
                else:
                    log("GAGAL SKIP KARTU.")
                    take_status_snapshot(page, "card_stuck.png")
                    return False
            else:
                time.sleep(3) 
                
        elif current_screen == "workspace":
            log("🎉 BERHASIL MASUK KE WORKSPACE MUSE.AI!")
            break
            
        elif current_screen == "unknown":
            time.sleep(2)
            
        else:
            time.sleep(2)

    if invite_code and card_skipped:
        do_redeem(page, invite_code)
        
    return True
