import time
import urllib.error
import urllib.request

url = "https://line-webhook-74735301292.asia-northeast1.run.app/webhook"
print("Waiting for Cloud Run deploy...")

for i in range(12):
    time.sleep(15)
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"{(i + 1) * 15}s: status={resp.status}")
            if resp.status in (200, 405, 400):
                print("Cloud Run is up!")
                break
    except urllib.error.HTTPError as e:
        print(f"{(i + 1) * 15}s: HTTP {e.code} - service responding")
        break
    except Exception as e:
        print(f"{(i + 1) * 15}s: {type(e).__name__}: {e}")
