# Gunakan image Node.js sebagai basis (karena ada package.json)
FROM node:20-bookworm

# 1. Instal dependensi sistem untuk Chromium/Playwright
# Ini penting agar browser bisa berjalan headless di container Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    libgbm1 \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libasound2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /app

# 3. Copy file dependensi terlebih dahulu (untuk caching)
COPY package*.json ./
COPY requirements.txt ./

# 4. Instal dependensi Node.js
RUN npm install

# 5. Instal dependensi Python (gunakan virtual environment agar bersih)
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# 6. Instal browser Playwright (Chromium) beserta dependensinya
# Flag --with-deps akan menginstal library sistem yang mungkin terlewat
RUN npx playwright install --with-deps chromium

# 7. Copy sisa kode proyek
COPY . .

# 8. (Opsional) Jika CloakBrowser memerlukan binary khusus, letakkan di sini
# Pastikan file binary CloakBrowser sudah ada di repo atau diunduh saat build.

# 9. Tentukan perintah default (bisa dioverride di Railway)
# Contoh: Menjalankan satu akun secara otomatis
CMD ["python", "scripts/run_one.py"]
