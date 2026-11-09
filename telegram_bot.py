import os
import subprocess
import asyncio
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN belum di-set di environment")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 <b>Muse.ai Farming Bot</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Bot akan otomatis menggunakan proxy acak dari <code>proxies.txt</code>.\n\n"
        "Ketik /farm untuk mulai membuat akun Muse.ai."
    )
    await update.message.reply_text(text, parse_mode="HTML")

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
        await msg.edit_text(f"❌ <b>Gagal menjalankan script:</b>\n<code>{e}</code>", parse_mode="HTML")
        return

    last_update_time = asyncio.get_event_loop().time()
    log_buffer = []      # Untuk update live di Telegram
    full_logs = []       # Menyimpan SEMUA log untuk diekstrak

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
                    display_logs = "\n".join([f"• {l}" for l in log_buffer[-3:]])
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
        # Ekstrak Email & Password dari Log
        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', full_text)
        pass_match = re.search(r'(?:pass|password|pwd)[\s:=]+([^\s,]+)', full_text, re.IGNORECASE)
        
        if email_match:
            email = email_match.group(1)
            password = pass_match.group(1) if pass_match else "Cek log di bawah"
            
            success_msg = (
                f"✅ <b>Akun Muse.ai Berhasil Dibuat!</b>\n\n"
                f"📧 <b>Email:</b> <code>{email}</code>\n"
                f"🔑 <b>Password:</b> <code>{password}</code>\n\n"
                f"<i>Gunakan kredensial di atas untuk login ke muse.ai</i>"
            )
            await msg.edit_text(success_msg, parse_mode="HTML")
        else:
            # Jika regex gagal, tampilkan 15 baris terakhir
            last_logs = "\n".join(full_logs[-15:])
            await msg.edit_text(
                f"✅ <b>Farming Selesai!</b> (Tapi format email tidak terdeteksi otomatis)\n\n"
                f"<b>Log Akhir:</b>\n<code>{last_logs}</code>", 
                parse_mode="HTML"
            )
    else:
        # Tampilkan error
        error_logs = "\n".join(full_logs[-10:])
        await msg.edit_text(
            f"❌ <b>Farming Gagal!</b> (Exit code: {rc})\n\n"
            f"<b>Log Error:</b>\n<code>{error_logs}</code>", 
            parse_mode="HTML"
        )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("farm", farm))
    print("Bot Telegram berjalan...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
