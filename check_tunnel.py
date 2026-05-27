import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# tunnel.log確認
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\cloudflare\tunnel.log", "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

print("=== tunnel.log (last 50 lines) ===")
lines = content.splitlines()
print("\n".join(lines[-50:]))
