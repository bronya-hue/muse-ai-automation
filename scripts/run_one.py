import os
import subprocess
import asyncio
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
        "Bot ini akan otomatis menggunakan proxy acak dari <code>proxies.txt</code> Anda.\n\n"
        "Ketik /farm untuk mulai membuat akun Muse.ai."
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "⏳ <b>Memulai proses farming Muse.ai...</b>\n"
        "1. Membaca proxy dari file...\n"
        "2. Membuka Cloud Browser...\n"
        "3. Menjalankan otomasi...", 
        parse_mode="HTML"
    )

    # Menjalankan script cloud_runner.py di background
    process = subprocess.Popen(
        ["python", "scripts/cloud_runner.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    last_update_time = asyncio.get_event_loop().time()
    log_buffer = []

    # Membaca log secara real-time
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            line = output.strip()
            log_buffer.append(line)
            
            if len(log_buffer) > 10:
                log_buffer.pop(0)

            current_time = asyncio.get_event_loop().time()
            is_important = any(keyword in line for keyword in ["BERHASIL", "BYPASS", "GAGAL", "Error", "Workspace"])
            
            if current_time - last_update_time > 5 or is_important:
                try:
                    display_logs = "\n".join([f"• {l}" for l in log_buffer[-3:]])
                    await msg.edit_text(
                        f"⏳ <b>Proses Farming...</b>\n\n"
                        f"<code>{display_logs}</code>", 
                        parse_mode="HTML"
                    )
                    last_update_time = current_time
                except Exception:
                    pass 

    rc = process.poll()
    if rc == 0:
        await msg.edit_text(
            "✅ <b>Farming Selesai!</b>\n\n"
            "Akun Muse.ai berhasil dibuat. Cek console Railway untuk melihat detail email/password.", 
            parse_mode="HTML"
        )
    else:
        error_logs = "\n".join([f"• {l}" for l in log_buffer[-5:]])
        await msg.edit_text(
            f"❌ <b>Farming Gagal!</b> (Exit code: {rc})\n\n"
            f"<b>Log Terakhir:</b>\n<code>{error_logs}</code>", 
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
