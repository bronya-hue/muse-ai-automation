# Gunakan Node.js sebagai basis
FROM node:20-slim

# Instal Python, Pip, dan semua library OS yang dibutuhkan Chromium (Puppeteer)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    chromium \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Beritahu Puppeteer agar menggunakan Chromium yang sudah diinstal di atas
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

WORKDIR /app

# Install dependensi Node.js
COPY package*.json ./
RUN npm install

# Install dependensi Python
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# Copy semua file project
COPY . .

# Jalankan Bot Telegram
CMD ["python3", "telegram_bot.py"]
