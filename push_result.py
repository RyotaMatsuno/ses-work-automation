import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

MATSUNO_TOKEN = config.get("LINE_CHANNEL_ACCESS_TOKEN", "")
MATSUNO_USER_ID = config.get("MATSUNO_LINE_USER_ID") or "Ue3508b43b84991f5a68281da5bf4cf39"


def push(text):
    if len(text) > 4900:
        text = text[:4900] + "\n...(省略)"
    r = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {MATSUNO_TOKEN}", "Content-Type": "application/json"},
        json={"to": MATSUNO_USER_ID, "messages": [{"type": "text", "text": text}]},
        timeout=15,
    )
    return r.status_code, r.text[:100]


# ローカルでline_queryを実行して結果をpush
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
for m in list(sys.modules):
    if "line_query" in m:
        del sys.modules[m]

from line_query import handle_line_query

print("line_query 実行中...")
result = handle_line_query("HS 北小金")
print(f"結果: {len(result) if result else 0}文字")

if result:
    # 上位10件のみにトリム（LINEに見やすく送る）
    lines = result.split("\n")
    # ⑥以降を切り取り
    cut_idx = len(lines)
    for i, ln in enumerate(lines):
        if ln.startswith("⑥") or ln.startswith("6."):
            cut_idx = i
            break
    trimmed = "\n".join(lines[:cut_idx])
    if len(lines) > cut_idx:
        trimmed += f"\n...他{result.count('①②③④⑤⑥⑦⑧⑨⑩')}件"

    status, resp = push(trimmed)
    print(f"Push status: {status}")
    if status == 200:
        print("✅ LINEに「HS 北小金」の照会結果を送信しました")
    else:
        print(f"❌ Push失敗: {resp}")
        # 429の場合はメッセージリミット
        if "429" in str(status):
            print("→ LINE月次メッセージ上限に達している可能性")
else:
    print("result=None (一致なし or エラー)")
