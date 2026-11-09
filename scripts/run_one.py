"""Single-account end-to-end runner with live streamed output."""
import os
import sys
import time
import subprocess
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Gunakan os.getcwd() agar path selalu tepat di dalam Docker (/app)
ROOT = os.getcwd()
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass

def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def cdp_ready(port: int, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def run_one(headless: bool = True):
    import secrets
    import random
    port = 9222
    env = dict(os.environ)
    env["CDP_URL"] = f"http://127.0.0.1:{port}"
    env["CDP_PORT"] = str(port)
    env["PROFILE_NAME"] = f"muse_{secrets.token_hex(4)}"
    env["FINGERPRINT"] = str(random.randint(100000, 999999))
    env["HEADLESS"] = "1" if headless else "0"

    # Gunakan os.path.join agar formatnya /app/scripts/launch_profile.js
    launch_js = os.path.join(SCRIPTS, "launch_profile.js")
    
    log(f"Launching CloakBrowser on port {port}...")
    
    browser_proc = subprocess.Popen(
        ["node", launch_js],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    try:
        log("Waiting for browser CDP endpoint...")
        if not cdp_ready(port, timeout=40):
            log("Browser CDP endpoint timed out!")
            # Tangkap error dari Node.js agar kelihatan penyebabnya
            try:
                browser_proc.terminate()
                out, _ = browser_proc.communicate(timeout=5)
                if out:
                    log("=== OUTPUT DARI NODE.JS (LAUNCH_PROFILE.JS) ===")
                    for line in out.splitlines():
                        log(f"NODE: {line}")
                    log("==============================================")
            except Exception as e:
                log(f"Gagal mengambil log Node.js: {e}")
            sys.exit(1) # Paksa keluar dengan kode error

        log("CDP ready! Starting muse_bot.py --one...")
        bot_py = os.path.join(SCRIPTS, "muse_bot.py")
        
        bot_proc = subprocess.Popen(
            [sys.executable, "-u", bot_py, "--one"],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        for line in bot_proc.stdout:
            print(line, end="", flush=True)

        bot_proc.wait()
        log(f"muse_bot exited with return code {bot_proc.returncode}")
        
        if bot_proc.returncode != 0:
            sys.exit(1) # Paksa keluar dengan kode error jika bot gagal
            
    finally:
        log("Cleaning up browser process...")
        try:
            browser_proc.terminate()
            browser_proc.wait(timeout=5)
        except Exception:
            try:
                browser_proc.kill()
            except Exception:
                pass

if __name__ == "__main__":
    headless_mode = "--headed" not in sys.argv
    run_one(headless=headless_mode)
