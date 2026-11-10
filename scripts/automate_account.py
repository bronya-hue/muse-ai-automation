import time
import random
from playwright.sync_api import Page

# ==========================================
# FUNGSI UTILITY & LOGGING
# ==========================================
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

def take_status_snapshot(page: Page, filename: str):
    try:
        page.screenshot(path=filename, full_page=True)
        log(f"Screenshot disimpan: {filename}")
    except Exception as e:
        log(f"Gagal mengambil screenshot: {e}")

# ==========================================
# DATA NAMA ACAK
# ==========================================
FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David", "Kevin", "Brian", "Jason", "Eric"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Wilson", "Anderson"]

def get_random_name():
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)

# ==========================================
# DETEKSI SCREEN
# ==========================================
def screen_of(page: Page) -> str:
    url = page.url.lower()
    if "workspace" in url or "dashboard" in url:
        return "workspace"
    
    content = page.content().lower()
    
    if "selesaikan pembuatan akun" in content or "nama depan" in content or "nama belakang" in content or "complete your account" in content:
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
# JS INJECTION UNTUK REACT (SANGAT AGRESIF)
# ==========================================
def do_meta_signup(page: Page):
    log("Mengisi form Meta (Nama & Tanggal) via JS Injection...")
    dismiss_dialog(page)
    
    first_name, last_name = get_random_name()
    # Buat tanggal lahir acak (Tahun 1995-2000)
    dob = f"{random.randint(1, 28):02d}/{random.randint(1, 12):02d}/{random.randint(1995, 2000)}"

    # Script JS untuk memaksa React mendeteksi inputan
    js_script = """
    (args) => {
        const fn = args.fn, ln = args.ln, dob = args.dob;
        const inputs = Array.from(document.querySelectorAll('input'));
        
        const setNativeValue = (element, value) => {
            const valueSetter = Object.getOwnPropertyDescriptor(element, 'value').set;
            const prototype = Object.getPrototypeOf(element);
            const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
            if (valueSetter && valueSetter !== prototypeValueSetter) {
                prototypeValueSetter.call(element, value);
            } else {
                valueSetter.call(element, value);
            }
        };

        let fnInput = inputs.find(i => (i.placeholder||'').toLowerCase().includes('depan') || (i.placeholder||'').toLowerCase().includes('first'));
        let lnInput = inputs.find(i => (i.placeholder||'').toLowerCase().includes('belakang') || (i.placeholder||'').toLowerCase().includes('last'));
        let dobInput = inputs.find(i => (i.placeholder||'').toLowerCase().includes('tanggal') || (i.placeholder||'').toLowerCase().includes('date'));

        if(fnInput) { 
            setNativeValue(fnInput, fn); 
            fnInput.dispatchEvent(new Event('input', { bubbles: true })); 
            fnInput.dispatchEvent(new Event('change', { bubbles: true })); 
        }
        if(lnInput) { 
            setNativeValue(lnInput, ln); 
            lnInput.dispatchEvent(new Event('input', { bubbles: true })); 
            lnInput.dispatchEvent(new Event('change', { bubbles: true })); 
        }
        if(dobInput) { 
            setNativeValue(dobInput, dob); 
            dobInput.dispatchEvent(new Event('input', { bubbles: true })); 
            dobInput.dispatchEvent(new Event('change', { bubbles: true })); 
            dobInput.dispatchEvent(new Event('blur', { bubbles: true })); 
        }

        return { fn: !!fnInput, ln: !!lnInput, dob: !!dobInput };
    }
    """
    
    try:
        # Jalankan JS Injection
        result = page.evaluate(js_script, {"fn": first_name, "ln": last_name, "dob": dob})
        log(f"Status Pengisian: Nama Depan={result['fn']}, Nama Belakang={result['ln']}, Tanggal={result['dob']}")
        time.sleep(2)

        # Cari tombol Konfirmasi
        submit_btn = page.locator('button:has-text("Konfirmasi"), button:has-text("Confirm"), button[type="submit"]').first
        
        if submit_btn.count() > 0 and submit_btn.is_visible():
            # Cek apakah tombol masih disabled
            is_disabled = submit_btn.evaluate("el => el.disabled || el.getAttribute('aria-disabled') === 'true'")
            
            if is_disabled:
                log("⚠️ Tombol Konfirmasi masih disabled. Mencoba memaksa klik via JS...")
                # Paksa klik lewat JS
                page.evaluate("""() => {
                    const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Konfirmasi') || b.innerText.includes('Confirm'));
                    if (btn) {
                        btn.removeAttribute('disabled');
                        btn.removeAttribute('aria-disabled');
                        btn.click();
                    }
                }""")
            else:
                log("✅ Tombol Konfirmasi sudah aktif. Mengklik...")
                submit_btn.click(force=True)
        else:
            log("❌ Tombol Konfirmasi tidak ditemukan di layar.")

        time.sleep(5) # Tunggu proses Meta
    except Exception as e:
        log(f"Error di do_meta_signup: {e}")

def do_birthday(page: Page):
    log("Mengisi tanggal lahir (form terpisah)...")
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
