# Gunakan Python versi slim yang ringan
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Instal dependensi sistem yang dibutuhkan Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan install library Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# PERINTAH WAJIB: Unduh Chromium untuk Playwright beserta dependensinya
RUN playwright install --with-deps chromium

# Copy sisa file proyek
COPY . .

# Jalankan Bot Telegram
CMD ["python", "telegram_bot.py"]
