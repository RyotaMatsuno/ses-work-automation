"""ポート・接続方式の診断"""

import socket
import time

from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

host = "mail65.onamae.ne.jp"
tests = [
    (993, "SSL"),
    (143, "STARTTLS"),
]

for port, mode in tests:
    t0 = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=10)
        elapsed = time.time() - t0
        print(f"[OK] {host}:{port} ({mode}) connected in {elapsed:.1f}s")
        sock.close()
    except Exception as e:
        elapsed = time.time() - t0
        print(f"[NG] {host}:{port} ({mode}) failed in {elapsed:.1f}s: {e}")
