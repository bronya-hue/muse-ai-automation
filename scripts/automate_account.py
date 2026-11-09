import time
import random
import re
import os
import sys
from playwright.sync_api import Page

# ==========================================
# FUNGSI UTILITY & LOGGING
# ==========================================
def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def wait_hydrated(page: Page, selector: str, timeout: int = 15):
    """Menunggu elemen muncul dan siap diinteraksi."""
    try:
        page.wait_for_selector(selector, state="visible", timeout=timeout * 1000)
    except Exception:
        pass

def type_verified(page: Page, element, text: str):
    """Mengetik teks dengan jeda acak agar terlihat seperti manusia."""
    element.click()
    time.sleep(0.2)
    for char in text:
        element.type(char)
        time.sleep(random.uniform(0.05, 0.15))

def dismiss_dialog(page: Page):
    """Menutup popup/dialog jika ada."""
    try:
        close_btns = page.locator('button[aria-label="Close"], button:has-text("Cancel")').all()
        for btn in close_btns:
            if btn.is_visible():
                btn.click(force=True)
                time.sleep(0.5)
    except Exception:
        pass

def take_status_snapshot(page: Page, filename: str):
    """Menyimpan screenshot untuk debugging."""
    try:
        page.screenshot(path=filename, full_page=True)
        log(f"Screenshot disimpan: {filename}")
    except Exception as e:
        log(f"Gagal mengambil screenshot: {e}")

# ==========================================
# DETEKSI SCREEN (STATE MACHINE)
# ==========================================
def screen_of(page: Page) -> str:
    """Mendeteksi halaman apa yang sedang aktif berdasarkan elemen DOM."""
    url = page.url.lower()
    
    if "workspace" in url or "dashboard" in url:
        return "workspace"
    
    content = page.content().lower()
    
    if "add a payment method" in content or "credit card" in content or "card number" in content:
        return "card"
    if "date of birth" in content or "birthday" in content or "year" in content and "month" in content:
        return "birthday"
    if "terms" in content or "privacy policy" in content or "agree" in content:
        return "disclosure"
    if "redeem" in content or "invite code" in content:
        return "redeem_entry"
    
    return "unknown"

# ==========================================
# AKSI-AKSI OTOMASI (HANDLERS)
# ==========================================
def do_birthday(page: Page):
    """Mengisi tanggal lahir (dibuat umur > 20 tahun)."""
    log("Mengisi tanggal lahir...")
    dismiss_dialog(page)
    try:
        # Cari input bulan, tanggal, tahun (bisa berupa select atau input text)
        month_input = page.locator('select[name="month"], input[name="month"]').first
        day_input = page.locator('select[name="day"], input[name="day"]').first
        year_input = page.locator('select[name="year"], input[name="year"]').first

        if month_input.count() > 0:
            # Gunakan nilai acak (tahun 1995-2000)
            month = str(random.randint(1, 12))
            day = str(random.randint(1, 28))
            year = str(random.randint(1995, 2000))
            
            # Isi (handle jika select vs input)
            if month_input.evaluate("el => el.tagName") == "SELECT":
                month_input.select_option(month)
                day_input.select_option(day)
                year_input.select_option(year)
            else:
                month_input.fill(month)
                day_input.fill(day)
                year_input.fill(year)

        # Klik tombol lanjut
        submit_btn = page.locator('button[type="submit"], button:has-text("Next"), button:has-text("Continue")').first
        if submit_btn.is_visible():
            submit_btn.click(force=True)
        time.sleep(3)
    except Exception as e:
        log(f"Error di do_birthday: {e}")

def do_disclosure(page: Page):
    """Menyetujui terms & conditions."""
    log("Menyetujui disclosure/terms...")
    dismiss_dialog(page)
    try:
        # Centang checkbox jika ada
        checkboxes = page.locator('input[type="checkbox"]').all()
        for cb in checkboxes:
            if not cb.is_checked():
                cb.check(force=True)
        
        # Klik tombol Agree/Continue
        agree_btn = page.locator('button:has-text("Agree"), button:has-text("I accept"), button:has-text("Continue")').first
        if agree_btn.is_visible():
            agree_btn.click(force=True)
        time.sleep(3)
    except Exception as e:
        log(f"Error di do_disclosure: {e}")

def do_skip_card(page: Page) -> bool:
    """
    Mencoba melewati verifikasi kartu (VCC).
    Mencari tombol 'Link Facebook', 'Instagram', atau 'Skip'.
    """
    log("Terdeteksi halaman minta kartu. Mencoba BYPASS...")
    dismiss_dialog(page)
    
    # 1. Cari tombol Social Linking
    social_selectors = [
        'button:has-text("Link Facebook")',
        'button:has-text("Continue with Facebook")',
        'button:has-text("Facebook")',
        'button:has-text("Instagram")',
        'a:has-text("Link Facebook")',
        '[data-pel-click*="facebook"]',
        '[data-pel-click*="social"]'
    ]
    
    for sel in social_selectors:
        btn = page.locator(sel).first
        if btn.count() > 0 and btn.is_visible():
            log(f"Menemukan tombol social: {sel}. Mengklik...")
            try:
                btn.click(force=True)
                time.sleep(5)
                # Jika layar berubah dari 'card', berarti berhasil
                if screen_of(page) != "card":
                    log("✅ BERHASIL BYPASS KARTU via Social Link!")
                    return True
            except Exception as e:
                log(f"Gagal klik social link: {e}")

    # 2. Cari tombol Skip / Not Now
    skip_selectors = [
        'button:has-text("Skip")',
        'button:has-text("Not now")',
        'button:has-text("Later")',
        'a:has-text("Skip for now")'
    ]
    
    for sel in skip_selectors:
        btn = page.locator(sel).first
        if btn.count() > 0 and btn.is_visible():
            log(f"Menemukan tombol skip: {sel}. Mengklik...")
            try:
                btn.click(force=True)
                time.sleep(3)
                return True
            except Exception as e:
                log(f"Gagal klik skip: {e}")

    # 3. Jika pakai Cloud Browser yang sangat bersih, kadang halaman ini auto-lolos
    # Coba refresh halaman sekali
    log("Mencoba refresh halaman untuk cek apakah verifikasi hilang...")
    page.reload(wait_until="networkidle")
    time.sleep(3)
    if screen_of(page) != "card":
        log("✅ Verifikasi kartu hilang setelah refresh!")
        return True

    log("❌ Tidak ada tombol bypass. Lingkungan (IP) mungkin terdeteksi bot.")
    return False

def do_redeem(page: Page, invite_code: str):
    """Memasukkan kode invite (jika ada)."""
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
def run_all_after_email(page: Page, invite_code: str = ""):
    """
    Dijalankan setelah email & OTP berhasil dimasukkan.
    Akan melakukan loop sampai masuk ke Workspace.
    """
    last_screen = None
    card_skipped = False
    
    for step in range(25):
        current_screen = screen_of(page)
        
        if current_screen != last_screen:
            log(f"--> Screen terdeteksi: {current_screen.upper()}")
            last_screen = current_screen

        # --- STATE MACHINE ---
        if current_screen == "birthday":
            do_birthday(page)
            
        elif current_screen == "disclosure":
            do_disclosure(page)
            
        elif current_screen == "card":
            if not card_skipped:
                success = do_skip_card(page)
                if success:
                    card_skipped = True
                else:
                    log("GAGAL SKIP KARTU. Silakan ganti proxy atau coba lagi nanti.")
                    take_status_snapshot(page, "card_stuck.png")
                    return False
            else:
                time.sleep(3) # Tunggu transisi
                
        elif current_screen == "workspace":
            log("🎉 BERHASIL MASUK KE WORKSPACE MUSE.AI!")
            break
            
        elif current_screen == "unknown":
            # Kadang halaman sedang loading
            time.sleep(2)
            
        else:
            time.sleep(2)

    # Redeem code jika disediakan
    if invite_code and card_skipped:
        do_redeem(page, invite_code)
        
    return True
