FROM python:3.11-slim

WORKDIR /app

# 1. Instal dependensi sistem untuk Chromium
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

# 2. Copy requirements dan install library Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. UNDUH CHROMIUM (Ini langkah yang sebelumnya gagal/terlewat)
RUN playwright install chromium

# 4. Copy sisa file
COPY . .

# 5. Jalankan bot
CMD ["python", "telegram_bot.py"]
