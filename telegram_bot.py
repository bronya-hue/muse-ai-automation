import telebot
import subprocess
import os
import threading
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

CONFIG_FILE = "config.json"
is_farming = False

# --- FUNGSI KONFIGURASI ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(key, value):
    config = load_config()
    config[key] = value
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# --- MENU UTAMA ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "🤖 *Muse.ai Auto-Farmer Bot*\n\n"
        "🛠 *Pengaturan:*\n"
        "`/setproxy` - Atur Proxy (Wajib)\n"
        "`/setinvite` - Atur Kode Referral\n"
        "`/setcard` - Atur VCC (Nomor, Expiry, CVV)\n\n"
        "🚀 *Aksi:*\n"
        "`/farm` - Mulai buat 1 akun\n"
        "`/status` - Cek pengaturan & status bot"
    )
    bot.reply_to(message, text, parse_mode='Markdown')

# --- SET PROXY ---
@bot.message_handler(commands=['setproxy'])
def ask_proxy(message):
    msg = bot.reply_to(message, "🔗 Kirimkan URL Proxy Anda.\nContoh: `http://user:pass@ip:port`", parse_mode='Markdown')
    bot.register_next_step_handler(msg, save_proxy)

def save_proxy(message):
    proxy_url = message.text.strip()
    save_config("PROXY_URL", proxy_url)
    bot.reply_to(message, "✅ Proxy berhasil disimpan!")

# --- SET INVITE CODE ---
@bot.message_handler(commands=['setinvite'])
def ask_invite(message):
    msg = bot.reply_to(message, "🎟 Kirimkan Kode Referral Muse.ai Anda.")
    bot.register_next_step_handler(msg, save_invite)

def save_invite(message):
    invite_code = message.text.strip()
    save_config("INVITE_CODE", invite_code)
    bot.reply_to(message, "✅ Kode Referral berhasil disimpan!")

# --- SET CARD (VCC) ---
@bot.message_handler(commands=['setcard'])
def ask_card(message):
    msg = bot.reply_to(message, "💳 Kirimkan data kartu dengan format:\n`NomorKartu|MM/YY|CVV`\n\nContoh: `4000123456789010|12/26|123`", parse_mode='Markdown')
    bot.register_next_step_handler(msg, save_card)

def save_card(message):
    try:
        data = message.text.split("|")
        if len(data) != 3:
            raise ValueError("Format salah")
        
        save_config("CARD_NUMBER", data[0].strip())
        save_config("CARD_EXPIRY", data[1].strip())
        save_config("CARD_CVV", data[2].strip())
        bot.reply_to(message, "✅ Data VCC berhasil disimpan!")
    except Exception:
        bot.reply_to(message, "❌ Format salah! Gunakan format: `Nomor|MM/YY|CVV`", parse_mode='Markdown')

# --- CEK STATUS ---
@bot.message_handler(commands=['status'])
def check_status(message):
    global is_farming
    config = load_config()
    
    status_text = "📊 *Status Bot*\n\n"
    status_text += f"🔄 Farming: {'⏳ Berjalan' if is_farming else '✅ Idle'}\n\n"
    status_text += "⚙️ *Konfigurasi Tersimpan:*\n"
    
    proxy = config.get("PROXY_URL", "Belum diset ❌")
    if proxy != "Belum diset ❌" and len(proxy) > 15:
        proxy = proxy[:10] + "..." + proxy[-5:] # Sensor proxy
    status_text += f"🌐 Proxy: `{proxy}`\n"
    
    invite = config.get("INVITE_CODE", "Belum diset ❌")
    status_text += f"🎟 Invite: `{invite}`\n"
    
    card = config.get("CARD_NUMBER", "Belum diset ❌")
    if card != "Belum diset ❌":
        card = "**** **** **** " + card[-4:] # Sensor nomor kartu
    status_text += f"💳 Kartu: `{card}`\n"

    bot.reply_to(message, status_text, parse_mode='Markdown')

# --- JALANKAN FARMING ---
@bot.message_handler(commands=['farm'])
def start_farming(message):
    global is_farming
    if is_farming:
        bot.reply_to(message, "❌ Proses farming sedang berjalan! Tunggu hingga selesai.")
        return
    
    config = load_config()
    if "PROXY_URL" not in config:
        bot.reply_to(message, "⚠️ Proxy belum diset! Silakan ketik `/setproxy` terlebih dahulu.", parse_mode='Markdown')
        return

    is_farming = True
    msg = bot.reply_to(message, "⏳ Memulai proses farming Muse.ai...\nMembuka browser & mendaftar akun. Mohon tunggu 1-2 menit.")
    
    thread = threading.Thread(target=run_farm_script, args=(message.chat.id, msg.message_id, config))
    thread.start()

def run_farm_script(chat_id, message_id, config):
    global is_farming
    try:
        # Gabungkan environment variable bawaan sistem dengan config dari Telegram
        env_vars = os.environ.copy()
        env_vars.update(config)

        # Jalankan skrip farming
        process = subprocess.run(
            ["python", "scripts/run_one.py"], 
            capture_output=True, 
            text=True,
            timeout=300,
            env=env_vars # Masukkan environment variables yang baru
        )
        
        output = process.stdout
        error = process.stderr
        
        if process.returncode == 0:
            result_text = f"✅ *Farming Selesai!*\n\nLog:\n`{output[-600:]}`"
        else:
            result_text = f"❌ *Farming Gagal*\n\nError:\n`{error[-600:]}`"
            
    except subprocess.TimeoutExpired:
        result_text = "❌ *Error:* Proses farming melebihi batas waktu (5 menit). Server mungkin kehabisan RAM atau stuck."
    except Exception as e:
        result_text = f"❌ *Error Sistem:* {str(e)}"
    finally:
        is_farming = False
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=result_text,
            parse_mode='Markdown'
        )

if __name__ == '__main__':
    print("Bot Telegram berjalan...")
    bot.infinity_polling()
