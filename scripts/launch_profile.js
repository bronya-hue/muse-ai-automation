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
        const allProxies = fs.readFileSync(proxyFile, 'utf8').split('\n').map(p => p.trim()).filter(p => p);
        if (allProxies.length === 0) return null;
        
        const selectedProxy = allProxies[Math.floor(Math.random() * allProxies.length)];
        const parts = selectedProxy.split(':');
        
        if (parts.length === 4) return `http://${parts[2]}:${parts[3]}@${parts[0]}:${parts[1]}`;
        if (parts.length === 2) return `http://${parts[0]}:${parts[1]}`;
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

    const iphoneUserAgent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1';

    while (!success && attempts < 10) {
        attempts++;
        const proxyUrl = getRandomProxy();
        anonymizedProxyUrl = null;
        
        let args = [
            '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
            '--disable-gpu', '--disable-software-rasterizer',
            `--remote-debugging-port=${CDP_PORT}`
        ];

        if (proxyUrl) {
            try {
                anonymizedProxyUrl = await proxyChain.anonymizeProxy(proxyUrl);
                args.push(`--proxy-server=${anonymizedProxyUrl}`);
                console.log(`[NODE] Percobaan ${attempts}: Menggunakan proxy lokal...`);
            } catch (error) {
                console.log(`[NODE] Gagal buat proxy-chain: ${error.message}`);
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
                ignoreHTTPSErrors: true
            });

            const page = await browser.newPage();
            await page.setUserAgent(iphoneUserAgent);
            await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });

            console.log(`[NODE] Mengetes koneksi ke muse.ai/join...`);
            await page.goto('https://muse.ai/join', { waitUntil: 'domcontentloaded', timeout: 25000 });
            
            console.log(`[NODE] Proxy HIDUP! Halaman Muse.ai berhasil dimuat.`);
            success = true;

        } catch (error) {
            console.log(`[NODE] Proxy MATI / Browser Crash: ${error.message}`);
            if (browser) { await browser.close(); browser = null; }
            if (anonymizedProxyUrl) { await proxyChain.closeAnonymizedProxy(anonymizedProxyUrl, true); }
        }
    }

    if (!success) {
        console.error(`[NODE] GAGAL TOTAL: Tidak bisa membuka Muse.ai setelah 10 percobaan.`);
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
