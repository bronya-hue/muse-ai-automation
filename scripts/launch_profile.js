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

// ==========================================
// UBAH USERNAME PROXY ANDA DI SINI
// Jika username asli: XJ4vimAJnvUfIfye
// Coba tambahkan "-country-jp" di belakangnya
// ==========================================
const FORCE_COUNTRY = "-country-jp"; // Bisa diganti "-country-sg" atau "-country-us"

if (!fs.existsSync(path.dirname(USER_DATA_DIR))) {
    fs.mkdirSync(path.dirname(USER_DATA_DIR), { recursive: true });
}

function getRandomProxy() {
    try {
        const proxyFile = path.join(__dirname, '../proxies.txt');
        if (!fs.existsSync(proxyFile)) return null;
        
        const allProxies = fs.readFileSync(proxyFile, 'utf8').split('\n').map(p => p.trim()).filter(p => p);
        if (allProxies.length === 0) return null;

        const selectedProxy = allProxies[Math.floor(Math.random() * allProxies.length)];
        const parts = selectedProxy.split(':');
        
        if (parts.length === 4) {
            let user = parts[2];
            // Tambahkan kode negara ke username (khusus FloppyData)
            if (!user.includes('-country-')) {
                user = user + FORCE_COUNTRY;
            }
            return `http://${user}:${parts[3]}@${parts[0]}:${parts[1]}`;
        }
        return `http://${selectedProxy}`;
    } catch (e) {
        return null;
    }
}

(async () => {
    let success = false;
    let attempts = 0;
    let browser = null;
    let anonymizedProxyUrl = null;

    // Konfigurasi Emulasi iPhone
    const iphoneUserAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1';

    while (!success && attempts < 10) {
        attempts++;
        const proxyUrl = getRandomProxy();
        anonymizedProxyUrl = null;
        
        let args = [
            '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
            '--disable-gpu', '--disable-software-rasterizer', '--single-process', '--no-zygote',
            `--remote-debugging-port=${CDP_PORT}`
        ];

        if (proxyUrl) {
            try {
                anonymizedProxyUrl = await proxyChain.anonymizeProxy(proxyUrl);
                args.push(`--proxy-server=${anonymizedProxyUrl}`);
                console.log(`[NODE] Percobaan ${attempts}: Menggunakan Proxy ${FORCE_COUNTRY}`);
            } catch (error) {
                continue;
            }
        }

        try {
            browser = await puppeteer.launch({
                headless: HEADLESS ? 'new' : false,
                executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium',
                args: args,
                userDataDir: USER_DATA_DIR,
                ignoreHTTPSErrors: true
            });

            // Buka halaman untuk tes
            const page = await browser.newPage();
            
            // Set User Agent & Viewport iPhone
            await page.setUserAgent(iphoneUserAgent);
            await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });

            await page.goto('https://muse.ai/join', { waitUntil: 'domcontentloaded', timeout: 25000 });
            
            console.log(`[NODE] Proxy HIDUP! Halaman Muse.ai berhasil dimuat.`);
            success = true;

        } catch (error) {
            console.log(`[NODE] Proxy MATI: ${error.message}`);
            if (browser) { await browser.close(); browser = null; }
            if (anonymizedProxyUrl) { await proxyChain.closeAnonymizedProxy(anonymizedProxyUrl, true); }
        }
    }

    if (!success) {
        console.error(`[NODE] GAGAL TOTAL: Semua proxy mati.`);
        process.exit(1);
    }

    console.log(`[NODE] Browser Mobile siap digunakan oleh Python. CDP aktif di port ${CDP_PORT}`);
    
    const keepAlive = setInterval(() => {}, 10000);
    const cleanup = async () => {
        clearInterval(keepAlive);
        if (browser) await browser.close();
        if (anonymizedProxyUrl) await proxyChain.closeAnonymizedProxy(anonymizedProxyUrl, true);
        process.exit(0);
    };
    process.on('SIGINT', cleanup);
    process.on('SIGTERM', cleanup);
})();
