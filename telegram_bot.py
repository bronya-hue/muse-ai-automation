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
        "🤖 <b>Muse.ai Farming Bot (Auto-Retry)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Bot akan otomatis mencari proxy yang bersih dan mencoba hingga 5 kali jika gagal.\n\n"
        "1. Ketik /farm untuk mulai.\n"
        "2. Ketik /login email@domain.com untuk ambil OTP."
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Format: <code>/login email@domain.com</code>", parse_mode="HTML")
        return
    
    email = context.args[0]
    msg = await update.message.reply_text(f"⏳ Mencari data untuk <code>{email}</code>...", parse_mode="HTML")
    
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
        await msg.edit_text("❌ Email tidak ditemukan di database.", parse_mode="HTML")
        return
        
    await msg.edit_text("✅ Data ditemukan! Mengecek inbox email...", parse_mode="HTML")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            token_res = await client.post("https://api.mail.tm/token", json={"address": email, "password": password})
            token = token_res.json().get("token")
            if not token:
                await msg.edit_text("❌ Gagal login ke server email.", parse_mode="HTML")
                return
            
            msg_res = await client.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {token}"})
            messages = msg_res.json().get("hydra:member", [])
            
            if not messages:
                await msg.edit_text("❌ Inbox kosong. Silakan minta kode di web Muse.ai dulu.", parse_mode="HTML")
                return
                
            msg_id = messages[0]["id"]
            detail_res = await client.get(f"https://api.mail.tm/messages/{msg_id}", headers={"Authorization": f"Bearer {token}"})
            detail = detail_res.json()
            
            text = detail.get("text", "") or detail.get("html", "")
            otp_match = re.search(r'\b(\d{6})\b', text)
            if otp_match:
                otp = otp_match.group(1)
                await msg.edit_text(f"🔑 <b>Kode Verifikasi:</b> <code>{otp}</code>", parse_mode="HTML")
            else:
                await msg.edit_text("❌ Email masuk, tapi kode OTP tidak ditemukan.", parse_mode="HTML")
                    
    except Exception as e:
        await msg.edit_text(f"❌ Error: <code>{html.escape(str(e))}</code>", parse_mode="HTML")

async def farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ <b>Memulai Auto-Retry Farming...</b>", parse_mode="HTML")

    max_attempts = 5
    success = False

    for attempt in range(1, max_attempts + 1):
        await msg.edit_text(f"⏳ <b>Percobaan {attempt}/{max_attempts}...</b>\nMencari proxy & membuka browser...", parse_mode="HTML")

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
            await msg.edit_text(f"❌ Gagal menjalankan script: <code>{html.escape(str(e))}</code>", parse_mode="HTML")
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
                is_important = any(keyword in line for keyword in ["BERHASIL", "BYPASS", "GAGAL", "Error", "Workspace", "proxy"])
                
                if current_time - last_update_time > 5 or is_important:
                    try:
                        display_logs = "\n".join([f"• {html.escape(l)}" for l in log_buffer[-3:]])
                        await msg.edit_text(
                            f"⏳ <b>Percobaan {attempt}/{max_attempts}...</b>\n\n<code>{display_logs}</code>", 
                            parse_mode="HTML"
                        )
                        last_update_time = current_time
                    except Exception:
                        pass 

        rc = process.poll()
        full_text = "\n".join(full_logs)
        
        if rc == 0:
            success = True
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', full_text)
            pass_match = re.search(r'(?:pass|password|pwd)[\s:=]+([^\s,]+)', full_text, re.IGNORECASE)
            
            if email_match:
                email = email_match.group(1)
                password = pass_match.group(1) if pass_match else "Cek log"
                await msg.edit_text(
                    f"✅ <b>Akun Muse.ai Berhasil! (Percobaan {attempt})</b>\n\n"
                    f"📧 Email: <code>{html.escape(email)}</code>\n"
                    f"🔑 Password: <code>{html.escape(password)}</code>\n\n"
                    f"<i>Ketik <code>/login {html.escape(email)}</code> untuk ambil OTP saat login.</i>",
                    parse_mode="HTML"
                )
            else:
                await msg.edit_text("✅ Selesai, tapi email tidak terdeteksi otomatis.", parse_mode="HTML")
            break # Keluar dari loop jika sukses
        else:
            # Jika gagal (kena CARD/403), lanjut ke percobaan berikutnya
            if attempt < max_attempts:
                await asyncio.sleep(2) # Jeda sebentar sebelum ganti proxy
            else:
                error_logs = "\n".join([html.escape(l) for l in full_logs[-5:]])
                await msg.edit_text(
                    f"❌ <b>Gagal setelah {max_attempts} percobaan.</b>\n\n"
                    f"Proxy yang didapat terus-menerus terdeteksi bot.\n\n"
                    f"<b>Log Terakhir:</b>\n<code>{error_logs}</code>", 
                    parse_mode="HTML"
                )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("farm", farm))
    app.add_handler(CommandHandler("login", cmd_login))
    print("Bot Telegram berjalan...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
