const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');
const { HttpsProxyAgent } = require('https-proxy-agent');

// Aktifkan plugin stealth agar tidak terdeteksi bot
puppeteer.use(StealthPlugin());

// Konfigurasi
const CDP_PORT = process.env.CDP_PORT || 9222;
const HEADLESS = process.env.HEADLESS === '0' ? false : true; // Default headless true
const PROFILE_NAME = process.env.PROFILE_NAME || `muse_${Date.now()}`;
const USER_DATA_DIR = path.join(__dirname, `../tmp_profiles/${PROFILE_NAME}`);

// Pastikan folder profile ada
if (!fs.existsSync(path.dirname(USER_DATA_DIR))) {
    fs.mkdirSync(path.dirname(USER_DATA_DIR), { recursive: true });
}

// ==========================================
// FUNGSI AMBIL PROXY ACak DARI PROXIES.TXT
// ==========================================
function getRandomProxy() {
    try {
        const proxyFile = path.join(__dirname, '../proxies.txt');
        if (!fs.existsSync(proxyFile)) {
            console.log("[NODE] proxies.txt tidak ditemukan, jalan tanpa proxy.");
            return null;
        }
        
        const proxies = fs.readFileSync(proxyFile, 'utf8')
            .split('\n')
            .map(p => p.trim())
            .filter(p => p.length > 0);
            
        if (proxies.length === 0) return null;
        
        const rawProxy = proxies[Math.floor(Math.random() * proxies.length)];
        const parts = rawProxy.split(':');
        
        let proxyUrl = '';
        // Format FloppyData: host:port:user:pass
        if (parts.length === 4) {
            proxyUrl = `http://${parts[2]}:${parts[3]}@${parts[0]}:${parts[1]}`;
        } 
        // Format: host:port
        else if (parts.length === 2) {
            proxyUrl = `http://${parts[0]}:${parts[1]}`;
        } else {
            proxyUrl = `http://${rawProxy}`;
        }
        
        console.log(`[NODE] Menggunakan Proxy: ${parts[0]}:${parts[1]}`);
        return proxyUrl;
    } catch (e) {
        console.log(`[NODE] Error membaca proxy: ${e.message}`);
        return null;
    }
}

// ==========================================
// LAUNCH BROWSER
// ==========================================
(async () => {
    const proxyUrl = getRandomProxy();
    let args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=1920,1080',
        `--remote-debugging-port=${CDP_PORT}`
    ];

    // Jika ada proxy, masukkan ke argumen Chromium
    if (proxyUrl) {
        args.push(`--proxy-server=${proxyUrl}`);
    }

    try {
        console.log(`[NODE] Menyalakan Chromium... (Headless: ${HEADLESS})`);
        
        const browser = await puppeteer.launch({
            headless: HEADLESS ? 'new' : false,
            executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium',
            args: args,
            userDataDir: USER_DATA_DIR,
            ignoreHTTPSErrors: true,
            defaultViewport: null
        });

        console.log(`[NODE] Browser berhasil menyala! CDP aktif di port ${CDP_PORT}`);
        
        // Biarkan browser tetap hidup agar Python bisa connect
        process.on('SIGINT', async () => {
            await browser.close();
            process.exit(0);
        });
        
        process.on('SIGTERM', async () => {
            await browser.close();
            process.exit(0);
        });

    } catch (error) {
        console.error(`[NODE] GAGAL MENYALAKAN BROWSER: ${error.message}`);
        process.exit(1);
    }
})();
