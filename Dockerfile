# Gunakan image resmi Playwright Python (sudah termasuk Chromium + semua dependensi sistem)
FROM mcr.microsoft.com/playwright/python:v1.41.2-jammy

WORKDIR /app

# Copy requirements dan install library Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy sisa file proyek
COPY . .

# Jalankan bot Telegram
CMD ["python", "telegram_bot.py"]
