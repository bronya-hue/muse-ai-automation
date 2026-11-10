const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');
const proxyChain = require('proxy-chain');

puppeteer.use(StealthPlugin());

const CDP_PORT = process.env.CDP_PORT || 9222;
const HEADLESS = process.env.HEADLESS === '0' ? false : true;
const PROFILE_NAME = process.env.PROFILE_NAME || `muse_${Date.now()}`;
const USER_DATA_DIR = path.join(__dirname, `../tmp_profiles/${PROFILE_NAME}`);

if (!fs.existsSync(path.dirname(USER_DATA_DIR))) {
    fs.mkdirSync(path.dirname(USER_DATA_DIR), { recursive: true });
}

function getRandomProxy() {
    try {
        const proxyFile = path.join(__dirname, '../proxies.txt');
        if (!fs.existsSync(proxyFile)) return null;
        
        const proxies = fs.readFileSync(proxyFile, 'utf8').split('\n').map(p => p.trim()).filter(p => p);
        if (proxies.length === 0) return null;
        
        const rawProxy = proxies[Math.floor(Math.random() * proxies.length)];
        const parts = rawProxy.split(':');
        
        if (parts.length === 4) {
            return `http://${parts[2]}:${parts[3]}@${parts[0]}:${parts[1]}`;
        } else if (parts.length === 2) {
            return `http://${parts[0]}:${parts[1]}`;
        }
        return `http://${rawProxy}`;
    } catch (e) {
        return null;
    }
}

(async () => {
    let success = false;
    let attempts = 0;
    let browser = null;
    let anonymizedProxyUrl = null;

    while (!success && attempts < 15) {
        attempts++;
        const proxyUrl = getRandomProxy();
        anonymizedProxyUrl = null;
        
        let args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=1920,1080',
            '--disable-software-rasterizer', // Tambahan untuk hemat RAM
            `--remote-debugging-port=${CDP_PORT}`
        ];

        if (proxyUrl) {
            try {
                anonymizedProxyUrl = await proxyChain.anonymizeProxy(proxyUrl);
                args.push(`--proxy-server=${anonymizedProxyUrl}`);
                console.log(`[NODE] Percobaan ${attempts}: Menggunakan proxy lokal -> ${anonymizedProxyUrl}`);
            } catch (error) {
                console.error(`[NODE] Gagal buat proxy-chain: ${error.message}`);
                continue;
            }
        }

        try {
            console.log(`[NODE] Menyalakan Chromium...`);
            browser = await puppeteer.launch({
                headless: HEADLESS ? 'new' : false,
                executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium',
                args: args,
                userDataDir: USER_DATA_DIR,
                ignoreHTTPSErrors: true,
                defaultViewport: null
            });

            console.log(`[NODE] Mengetes koneksi ke muse.ai/join...`);
            const page = await browser.newPage();
            await page.goto('https://muse.ai/join', { waitUntil: 'domcontentloaded', timeout: 20000 });
            
            console.log(`[NODE] Proxy HIDUP! Halaman Muse.ai berhasil dimuat.`);
            success = true;

        } catch (error) {
            console.error(`[NODE] Proxy MATI (Gagal load halaman): ${error.message}`);
            
            if (browser) {
                await browser.close();
                browser = null;
            }
            if (anonymizedProxyUrl) {
                await proxyChain.closeAnonymizedProxy(anonymizedProxyUrl, true);
            }
        }
    }

    if (!success) {
        console.error(`[NODE] GAGAL TOTAL: Sudah mencoba 15 proxy tapi semuanya mati.`);
        process.exit(1);
    }

    console.log(`[NODE] Browser siap digunakan oleh Python. CDP aktif di port ${CDP_PORT}`);
    
    // 🔥 KUNCI PERBAIKAN: setInterval menahan Node.js agar tidak mati
    // selama Python (muse_bot.py) masih menggunakannya.
    const keepAlive = setInterval(() => {
        // Proses idle untuk menahan browser tetap hidup
    }, 10000);

    const cleanup = async () => {
        console.log(`[NODE] Menerima sinyal berhenti. Menutup browser...`);
        clearInterval(keepAlive);
        if (browser) await browser.close();
        if (anonymizedProxyUrl) await proxyChain.closeAnonymizedProxy(anonymizedProxyUrl, true);
        process.exit(0);
    };

    process.on('SIGINT', cleanup);
    process.on('SIGTERM', cleanup);

})();
