# Gunakan base image resmi Playwright
FROM mcr.microsoft.com/playwright/python:v1.41.2-jammy

WORKDIR /app

# Copy requirements dan install library Python (termasuk Patchright)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instal Chromium untuk Patchright (Patchright menggunakan binary yang sama)
RUN patchright install chromium

# Copy sisa file
COPY . .

# Jalankan bot
CMD ["python", "telegram_bot.py"]
