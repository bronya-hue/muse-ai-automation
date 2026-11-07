FROM python:3.11-slim

WORKDIR /app

# 1. Copy requirements dan install library Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. KUNCI UTAMA: Gunakan flag --with-deps
# Perintah ini akan otomatis menginstal Chromium + semua library Linux yang kurang
RUN playwright install --with-deps chromium

# 3. Copy sisa file
COPY . .

# 4. Jalankan bot
CMD ["python", "telegram_bot.py"]
