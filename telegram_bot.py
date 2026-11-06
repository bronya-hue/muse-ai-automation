import telebot
import subprocess
import os
import threading
import time

# Ambil token dari Environment Variable Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Kunci agar farming tidak jalan bersamaan (mencegah RAM penuh)
is_farming = False

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "🤖 *Muse.ai Auto-Farmer Bot*\n\n"
        "Perintah yang tersedia:\n"
        "`/farm` - Mulai membuat 1 akun Muse.ai\n"
        "`/status` - Cek status bot\n\n"
        "_Pastikan Anda sudah mengisi PROXY_URL dan INVITE_CODE di Railway._"
    )
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['status'])
def check_status(message):
    global is_farming
    if is_farming:
        bot.reply_to(message, "⏳ Bot sedang sibuk melakukan farming. Mohon tunggu.")
    else:
        bot.reply_to(message, "✅ Bot siap menerima perintah. Ketik `/farm` untuk mulai.")

@bot.message_handler(commands=['farm'])
def start_farming(message):
    global is_farming
    if is_farming:
        bot.reply_to(message, "❌ Proses farming sedang berjalan! Tunggu hingga selesai.")
        return
    
    is_farming = True
    msg = bot.reply_to(message, "⏳ Memulai proses farming Muse.ai...\nMembuka browser & mendaftar akun. Ini memakan waktu 1-2 menit.")
    
    # Jalankan di thread terpisah agar bot tidak freeze
    thread = threading.Thread(target=run_farm_script, args=(message.chat.id, msg.message_id))
    thread.start()

def run_farm_script(chat_id, message_id):
    global is_farming
    try:
        # Asumsi repo menggunakan script run_one.py (sesuaikan jika namanya beda)
        # Kita jalankan script Python bawaan repo menggunakan subprocess
        process = subprocess.run(
            ["python", "scripts/run_one.py"], 
            capture_output=True, 
            text=True,
            timeout=300 # Timeout 5 menit
        )
        
        output = process.stdout
        error = process.stderr
        
        # Cek apakah berhasil atau gagal berdasarkan output
        if process.returncode == 0:
            # Ambil info penting dari log (misal email/akun yang dibuat)
            # Sesuaikan parsing ini dengan output asli dari repo
            result_text = f"✅ *Farming Selesai!*\n\nLog:\n`{output[-500:]}`"
        else:
            result_text = f"❌ *Farming Gagal*\n\nError:\n`{error[-500:]}`"
            
    except subprocess.TimeoutExpired:
        result_text = "❌ *Error:* Proses farming melebihi batas waktu (5 menit). Server mungkin kehabisan RAM."
    except Exception as e:
        result_text = f"❌ *Error Sistem:* {str(e)}"
    finally:
        is_farming = False
        # Edit pesan loading menjadi hasil akhir
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=result_text,
            parse_mode='Markdown'
        )

if __name__ == '__main__':
    print("Bot Telegram berjalan...")
    bot.infinity_polling()
