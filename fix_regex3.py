# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LQ = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
lines = open(LQ, encoding="utf-8").read().splitlines()

# 351行目付近の_k_norm行を探して差し替え
for i, line in enumerate(lines):
    if "_k_norm = " in line and "_re_dedup" in line:
        # 句読点を除去する正規表現（安全な書き方）
        lines[i] = '        _k_norm = _re_dedup.sub("[^\\w]", "", _k)[:30] if _k else ""'
        print(f"L{i + 1} 差し替え完了: {lines[i]}")
        break

with open(LQ, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

# 確認
import subprocess

r = subprocess.run(
    [
        sys.executable,
        "-c",
        "import sys; sys.path.insert(0, r'C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\line_webhook'); from line_query import handle_line_query; print('import OK')",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook",
    timeout=10,
)
print(r.stdout.strip() or "ERR: " + r.stderr[:200])
