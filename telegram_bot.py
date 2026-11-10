import os
import subprocess
import asyncio
import re
import html
import csv
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN belum di-set di environment")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 <b>Muse.ai Farming Bot</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "1. Ketik /farm untuk membuat akun baru secara otomatis.\n"
        "2. Ketik /login email@domain.com untuk mengambil kode OTP saat login manual."
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Format: <code>/login email@domain.com</code>", parse_mode="HTML")
        return
    
    email = context.args[0]
    msg = await update.message.reply_text(f"⏳ Mencari data untuk <code>{email}</code>...", parse_mode="HTML")
    
    # 1. Cari password di accounts.csv
    password = None
    try:
        with open('/app/accounts.csv', mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('email') == email or row.get('Email') == email:
                    password = row.get('password') or row.get('Password') or row.get('pass')
                    break
    except Exception as e:
        await msg.edit_text(f"❌ Gagal membaca database: <code>{html.escape(str(e))}</code>", parse_mode="HTML")
        return

    if not password:
        await msg.edit_text("❌ Email tidak ditemukan di database bot. Pastikan email tersebut dibuat oleh bot ini.", parse_mode="HTML")
        return
        
    await msg.edit_text("✅ Data ditemukan! Mengecek inbox email...", parse_mode="HTML")
    
    # 2. Buka inbox mail.tm
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            token_res = await client.post("https://api.mail.tm/token", json={"address": email, "password": password})
            token = token_res.json().get("token")
            if not token:
                await msg.edit_text("❌ Gagal login ke server email. Sesi mungkin sudah expired.", parse_mode="HTML")
                return
            
            msg_res = await client.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {token}"})
            messages = msg_res.json().get("hydra:member", [])
            
            if not messages:
                await msg.edit_text("❌ Inbox kosong.\n\nSilakan buka web Muse.ai, klik 'Lupa Password' atau minta kode verifikasi, lalu ketik /login lagi.", parse_mode="HTML")
                return
                
            # Ambil pesan terbaru
            msg_id = messages[0]["id"]
            detail_res = await client.get(f"https://api.mail.tm/messages/{msg_id}", headers={"Authorization": f"Bearer {token}"})
            detail = detail_res.json()
            
            text = detail.get("text", "") or detail.get("html", "")
                
            # Cari kode 6 digit
            otp_match = re.search(r'\b(\d{6})\b', text)
            if otp_match:
                otp = otp_match.group(1)
                await msg.edit_text(
                    f"🔑 <b>Kode Verifikasi Ditemukan!</b>\n\n"
                    f"Kode: <code>{otp}</code>\n\n"
                    f"Masukkan kode ini di web Muse.ai untuk login.", 
                    parse_mode="HTML"
                )
            else:
                # Cari link jika bukan OTP
                link_match = re.search(r'https?://[^\s"\'<>]+', text)
                if link_match:
                    link = link_match.group(0).replace('&amp;', '&')
                    await msg.edit_text(
                        f"🔗 <b>Link Login Ditemukan!</b>\n\n"
                        f"<a href='{link}'>Klik di sini untuk login</a>", 
                        parse_mode="HTML", 
                        disable_web_page_preview=True
                    )
                else:
                    await msg.edit_text("❌ Email masuk, tapi kode verifikasi tidak ditemukan di dalamnya.", parse_mode="HTML")
                    
    except Exception as e:
        await msg.edit_text(f"❌ Error: <code>{html.escape(str(e))}</code>", parse_mode="HTML")


async def farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "⏳ <b>Memulai proses farming Muse.ai...</b>\n"
        "1. Membaca proxy dari file...\n"
        "2. Membuka CloakBrowser...\n"
        "3. Menjalankan otomasi...", 
        parse_mode="HTML"
    )

    try:
        process = subprocess.Popen(
            ["python3", "scripts/run_one.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as e:
        await msg.edit_text(f"❌ <b>Gagal menjalankan script:</b>\n<code>{html.escape(str(e))}</code>", parse_mode="HTML")
        return

    last_update_time = asyncio.get_event_loop().time()
    log_buffer = []      
    full_logs = []       

    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            line = output.strip()
            full_logs.append(line)
            log_buffer.append(line)
            
            if len(log_buffer) > 5:
                log_buffer.pop(0)

            current_time = asyncio.get_event_loop().time()
            is_important = any(keyword in line for keyword in ["BERHASIL", "BYPASS", "GAGAL", "Error", "Workspace", "proxy", "Email", "Password"])
            
            if current_time - last_update_time > 5 or is_important:
                try:
                    display_logs = "\n".join([f"• {html.escape(l)}" for l in log_buffer[-3:]])
                    await msg.edit_text(
                        f"⏳ <b>Proses Farming...</b>\n\n<code>{display_logs}</code>", 
                        parse_mode="HTML"
                    )
                    last_update_time = current_time
                except Exception:
                    pass 

    rc = process.poll()
    full_text = "\n".join(full_logs)
    
    if rc == 0:
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', full_text)
        pass_match = re.search(r'(?:pass|password|pwd)[\s:=]+([^\s,]+)', full_text, re.IGNORECASE)
        
        if email_match:
            email = email_match.group(1)
            password = pass_match.group(1) if pass_match else "Cek log di bawah"
            success_msg = (
                f"✅ <b>Akun Muse.ai Berhasil Dibuat!</b>\n\n"
                f"📧 <b>Email:</b> <code>{html.escape(email)}</code>\n"
                f"🔑 <b>Password:</b> <code>{html.escape(password)}</code>\n\n"
                f"<i>Untuk login, buka web Muse.ai, masukkan email di atas, lalu ketik <code>/login {html.escape(email)}</code> di bot ini untuk mendapatkan kode OTP.</i>"
            )
            await msg.edit_text(success_msg, parse_mode="HTML")
        else:
            last_logs = "\n".join([html.escape(l) for l in full_logs[-15:]])
            await msg.edit_text(
                f"✅ <b>Farming Selesai!</b> (Tapi format email tidak terdeteksi)\n\n"
                f"<b>Log Akhir:</b>\n<code>{last_logs}</code>", 
                parse_mode="HTML"
            )
    else:
        error_logs = "\n".join([html.escape(l) for l in full_logs[-10:]])
        await msg.edit_text(
            f"❌ <b>Farming Gagal!</b> (Exit code: {rc})\n\n"
            f"<b>Log Error:</b>\n<code>{error_logs}</code>", 
            parse_mode="HTML"
        )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("farm", farm))
    app.add_handler(CommandHandler("login", cmd_login)) # Daftarkan command /login
    print("Bot Telegram berjalan...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
