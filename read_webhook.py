import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# webhook_server.py の全内容確認
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

print(f"SIZE: {len(content)}chars")
# handle_message 周辺を中心に表示
idx = content.find("def handle_message")
if idx < 0:
    idx = content.find("handle")
print(content)
