import subprocess
import time

CF = r"C:\Users\ma_py\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"
LOG = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cf_login2.log"

proc = subprocess.Popen(
    [CF, "tunnel", "login"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",
    errors="replace",
)

url_found = None
with open(LOG, "w", encoding="utf-8") as f:
    for i in range(40):
        line = proc.stdout.readline()
        if line:
            f.write(line)
            f.flush()
            print(line, end="", flush=True)
            if "https://auth" in line or "https://dash" in line or "please open" in line.lower():
                url_found = line.strip()
                break
        time.sleep(0.5)

print(f"\n=== URL: {url_found} ===")
