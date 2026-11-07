# Gunakan base image resmi Playwright (sesuai versi 1.41.2)
FROM mcr.microsoft.com/playwright/python:v1.41.2-jammy

WORKDIR /app

# Copy requirements dan install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy sisa file
COPY . .

# Jalankan bot
CMD ["python", "telegram_bot.py"]
