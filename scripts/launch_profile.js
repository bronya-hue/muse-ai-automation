const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');

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
        if (!fs.existsSync(proxyFile)) {
            console.log("[NODE] proxies.txt tidak ditemukan, jalan tanpa proxy.");
            return null;
        }
        
        const proxies = fs.readFileSync(proxyFile, 'utf8').split('\n').map(p => p.trim()).filter(p => p);
        if (proxies.length === 0) return null;
        
        const rawProxy = proxies[Math.floor(Math.random() * proxies.length)];
        const parts = rawProxy.split(':');
        
        // Format FloppyData: host:port:user:pass
        if (parts.length === 4) {
            console.log(`[NODE] Memilih Proxy Auth: ${parts[0]}:${parts[1]}`);
            return { 
                server: `http://${parts[0]}:${parts[1]}`, 
                username: parts[2], 
                password: parts[3] 
            };
        } 
        // Format: host:port
        else if (parts.length === 2) {
            console.log(`[NODE] Memilih Proxy No-Auth: ${parts[0]}:${parts[1]}`);
            return { server: `http://${parts[0]}:${parts[1]}` };
        }
        return { server: `http://${rawProxy}` };
    } catch (e) {
        console.log(`[NODE] Error baca proxy: ${e.message}`);
        return null;
    }
}

(async () => {
    const proxy = getRandomProxy();
    let args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=1920,1080',
        `--remote-debugging-port=${CDP_PORT}`
    ];

    if (proxy) {
        args.push(`--proxy-server=${proxy.server}`);
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

        // 🔥 KUNCI PERBAIKAN: Menyuntikkan Password Proxy ke setiap tab baru
        if (proxy && proxy.username) {
            browser.on('targetcreated', async (target) => {
                const page = await target.page();
                if (page) {
                    await page.authenticate({
                        username: proxy.username,
                        password: proxy.password
                    }).catch(err => console.log(`[NODE] Auth error: ${err.message}`));
                }
            });
        }

        console.log(`[NODE] Browser berhasil menyala! CDP aktif di port ${CDP_PORT}`);
        
        process.on('SIGINT', async () => { await browser.close(); process.exit(0); });
        process.on('SIGTERM', async () => { await browser.close(); process.exit(0); });

    } catch (error) {
        console.error(`[NODE] GAGAL MENYALAKAN BROWSER: ${error.message}`);
        process.exit(1);
    }
})();
