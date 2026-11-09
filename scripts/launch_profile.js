
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
            console.log(`[NODE] Memilih Proxy Auth: ${parts[0]}:${parts[1]}`);
            return `http://${parts[2]}:${parts[3]}@${parts[0]}:${parts[1]}`;
        } else if (parts.length === 2) {
            console.log(`[NODE] Memilih Proxy No-Auth: ${parts[0]}:${parts[1]}`);
            return `http://${parts[0]}:${parts[1]}`;
        }
        return `http://${rawProxy}`;
    } catch (e) {
        console.log(`[NODE] Error baca proxy: ${e.message}`);
        return null;
    }
}

(async () => {
    const proxyUrl = getRandomProxy();
    let anonymizedProxyUrl = null;
    
    let args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=1920,1080',
        `--remote-debugging-port=${CDP_PORT}`
    ];

    if (proxyUrl) {
        try {
            // 🔥 KUNCI PERBAIKAN: Buat proxy lokal tanpa password (bypass auth)
            anonymizedProxyUrl = await proxyChain.anonymizeProxy(proxyUrl);
            console.log(`[NODE] Proxy lokal (anonymized) siap: ${anonymizedProxyUrl}`);
            args.push(`--proxy-server=${anonymizedProxyUrl}`);
        } catch (error) {
            console.error(`[NODE] Gagal membuat proxy-chain: ${error.message}`);
        }
    }

    try {
        console.log(`[NODE] Menyalakan Chromium...`);
        const browser = await puppeteer.launch({
            headless: HEADLESS ? 'new' : false,
            executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium',
            args: args,
            userDataDir: USER_DATA_DIR,
            ignoreHTTPSErrors: true,
            defaultViewport: null
        });

        console.log(`[NODE] Browser berhasil menyala! CDP aktif di port ${CDP_PORT}`);
        
        // Pembersihan saat browser ditutup
        const cleanup = async () => {
            await browser.close();
            if (anonymizedProxyUrl) {
                await proxyChain.closeAnonymizedProxy(anonymizedProxyUrl, true);
            }
            process.exit(0);
        };

        process.on('SIGINT', cleanup);
        process.on('SIGTERM', cleanup);

    } catch (error) {
        console.error(`[NODE] GAGAL MENYALAKAN BROWSER: ${error.message}`);
        if (anonymizedProxyUrl) {
            await proxyChain.closeAnonymizedProxy(anonymizedProxyUrl, true);
        }
        process.exit(1);
    }
})();
